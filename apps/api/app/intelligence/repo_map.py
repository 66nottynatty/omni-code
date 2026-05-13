"""
RepoMap — Builds a compact structural map of a repository.
Injected into agent context so agents understand file relationships,
not just content fragments from embedding search.
"""
import os
import ast
import re
from pathlib import Path
from typing import List, Optional

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".next", "dist",
    "build", ".venv", "venv", ".mypy_cache", "coverage"
}
IGNORE_EXTS = {".lock", ".png", ".jpg", ".svg", ".ico", ".woff", ".ttf"}


class RepoMap:

    def __init__(self, workspace_path: str, max_chars: int = 6000):
        self.root = Path(workspace_path)
        self.max_chars = max_chars

    def build(self, focus_files: Optional[List[str]] = None) -> str:
        parts = [f"# Repo Map: {self.root.name}\n"]
        parts.append("## File Tree")
        parts.append(self._tree(max_depth=3))

        if focus_files:
            parts.append("\n## Symbol Index")
            for fp in focus_files[:8]:
                symbols = self._symbols(fp)
                if symbols:
                    parts.append(f"\n`{fp}`")
                    parts.extend(f"  {s}" for s in symbols[:15])

            parts.append("\n## Local Imports")
            parts.append(self._import_graph(focus_files[:6]))

        result = "\n".join(parts)
        return result[:self.max_chars]

    def _tree(self, max_depth: int = 3) -> str:
        lines = []
        for root, dirs, files in os.walk(self.root):
            dirs[:] = sorted(d for d in dirs if d not in IGNORE_DIRS)
            depth = str(root).replace(str(self.root), "").count(os.sep)
            if depth >= max_depth:
                dirs.clear()
                continue
            indent = "  " * depth
            folder = os.path.basename(root)
            lines.append(f"{indent}{folder}/")
            sub = "  " * (depth + 1)
            shown = [f for f in sorted(files) if Path(f).suffix not in IGNORE_EXTS]
            for f in shown[:12]:
                lines.append(f"{sub}{f}")
            if len(shown) > 12:
                lines.append(f"{sub}... ({len(shown) - 12} more)")
        return "\n".join(lines)

    def _symbols(self, filepath: str) -> List[str]:
        full = self.root / filepath
        if not full.exists():
            return []
        try:
            src = full.read_text(errors="ignore")
            if filepath.endswith(".py"):
                return self._py_symbols(src)
            if filepath.endswith((".ts", ".tsx", ".js", ".jsx")):
                return self._ts_symbols(src)
        except Exception:
            pass
        return []

    def _py_symbols(self, src: str) -> List[str]:
        syms = []
        try:
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    syms.append(f"class {node.name}")
                elif isinstance(node, ast.FunctionDef):
                    args = [a.arg for a in node.args.args]
                    syms.append(f"def {node.name}({', '.join(args[:4])}{'...' if len(args) > 4 else ''})")
        except Exception:
            pass
        return syms

    def _ts_symbols(self, src: str) -> List[str]:
        syms = []
        for m in re.finditer(r"export\s+(default\s+)?(async\s+)?function\s+(\w+)", src):
            syms.append(f"export function {m.group(3)}()")
        for m in re.finditer(r"export\s+(type|interface|const|class|enum)\s+(\w+)", src):
            syms.append(f"export {m.group(1)} {m.group(2)}")
        return syms

    def _import_graph(self, files: List[str]) -> str:
        lines = []
        for fp in files:
            full = self.root / fp
            if not full.exists():
                continue
            try:
                src = full.read_text(errors="ignore")
                local = re.findall(r"(?:import|from)\s+['\"](\.[^'\"]+)['\"]", src)
                if local:
                    lines.append(f"  {fp} → {', '.join(local[:4])}")
            except Exception:
                pass
        return "\n".join(lines) or "  (none)"
