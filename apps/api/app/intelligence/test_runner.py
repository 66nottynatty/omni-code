"""
TestRunner — Executes project tests and returns structured results.
Used by agents to verify their code changes work before concluding.
"""
import asyncio
import os
import re
from typing import Dict, Any
from pathlib import Path


class TestRunner:

    async def run(self, workspace_path: str, command: str = "auto") -> Dict[str, Any]:
        if command == "auto":
            command = self._detect_command(workspace_path)

        if not command:
            return {"passed": True, "output": "No test framework detected", "skipped": True}

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=workspace_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

            out = stdout.decode(errors="replace")
            err = stderr.decode(errors="replace")

            return {
                "passed": proc.returncode == 0,
                "returncode": proc.returncode,
                "output": out,
                "errors": err,
                "summary": self._parse_summary(out + err),
                "command": command
            }
        except asyncio.TimeoutError:
            return {
                "passed": False,
                "output": "",
                "errors": "Tests timed out after 120 seconds",
                "summary": "TIMEOUT"
            }
        except Exception as e:
            return {"passed": False, "output": "", "errors": str(e), "summary": "ERROR"}

    def _detect_command(self, path: str) -> str:
        p = Path(path)
        if (p / "pytest.ini").exists() or (p / "pyproject.toml").exists():
            return "pytest --tb=short -q 2>&1"
        if (p / "package.json").exists():
            pkg = (p / "package.json").read_text()
            if '"jest"' in pkg or '"vitest"' in pkg:
                return "npm test -- --watchAll=false --passWithNoTests 2>&1"
        if (p / "go.mod").exists():
            return "go test ./... 2>&1"
        if (p / "Cargo.toml").exists():
            return "cargo test 2>&1"
        return ""

    def _parse_summary(self, output: str) -> str:
        patterns = [
            r"\d+ passed",
            r"Tests:\s+\d+ passed",
            r"ok\s+\S+",
            r"\d+ tests? failed",
            r"FAILED \S+",
            r"error\[",
        ]
        for pattern in patterns:
            m = re.search(pattern, output)
            if m:
                return m.group(0)
        lines = [l for l in output.strip().splitlines() if l.strip()]
        return lines[-1][:150] if lines else "No output"
