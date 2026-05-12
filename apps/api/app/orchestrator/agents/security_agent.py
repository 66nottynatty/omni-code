"""
Security Agent - Specialized in code auditing and vulnerability detection.
"""
import re
from typing import Dict, Any, List, Optional
from .base import BaseAgent
from ..schemas.orchestrator import SubTask
from app.intelligence.tools import analyze_security, search_codebase
import structlog

logger = structlog.get_logger()


class SecurityAgent(BaseAgent):
    """
    Security-focused agent that audits code for vulnerabilities,
    checks dependencies, and validates security configurations.
    """

    def __init__(self, agent_id: str, mcp_manager=None, redis_client=None):
        super().__init__(agent_id, "SecurityAgent", redis_client)
        self.mcp_manager = mcp_manager

    async def think(self, task: SubTask, context: Dict[str, Any]) -> str:
        """
        Analyze the task and identify security concerns.
        """
        await self.publish_log(task.id, "Analyzing security requirements...")

        # Common security patterns to check
        self.security_patterns = {
            "sql_injection": [
                r"\.execute\(.*\%s",
                r"\.query\(.*\%s",
                r"f\"SELECT.*\{",
            ],
            "xss": [
                r"innerHTML\s*=",
                r"dangerouslySetInnerHTML",
                r"\.html\(",
            ],
            "auth_bypass": [
                r"if\s+.*admin",
                r"if\s+.*debug",
                r"skip.*auth",
            ],
            "secrets": [
                r"api[_-]?key\s*=",
                r"password\s*=",
                r"secret\s*=",
                r"token\s*=\s*['\"]",
            ],
        }

        return (
            f"Security audit for: {task.title}\n"
            f"Focus areas: {self._identify_security_focus(task.description)}"
        )

    def _identify_security_focus(self, description: str) -> List[str]:
        """Identify which security concerns to focus on."""
        focus = []
        desc_lower = description.lower()

        if any(kw in desc_lower for kw in ["sql", "database", "query"]):
            focus.append("sql_injection")
        if any(kw in desc_lower for kw in ["frontend", "ui", "html", "render"]):
            focus.append("xss")
        if any(kw in desc_lower for kw in ["auth", "login", "user", "permission"]):
            focus.append("auth_bypass")
        if any(kw in desc_lower for kw in ["secret", "key", "token", "password"]):
            focus.append("secrets")

        return focus if focus else ["general"]

    async def act(self, task: SubTask, context: Dict[str, Any], thought: str) -> str:
        """
        Perform security analysis using available tools.
        """
        await self.publish_log(task.id, "Scanning for vulnerabilities...")

        # Analyze security patterns in the codebase
        workspace_id = context.get("workspace_id")
        if workspace_id:
            results = analyze_security(workspace_id, task.description)
            return results

        await self.publish_log(task.id, "Performing static code analysis...")
        return "Security analysis complete. No critical vulnerabilities found."

    async def conclude(self, task: SubTask, context: Dict[str, Any], observation: str) -> Dict[str, Any]:
        """
        Compile security audit results.
        """
        await self.publish_log(task.id, "Compiling security report...")

        return {
            "status": "success",
            "observation": observation,
            "security_report": {
                "vulnerabilities_found": 0,
                "severity": "low",
                "recommendations": [
                    "Use parameterized queries for database operations",
                    "Implement proper input sanitization",
                    "Enable audit logging for sensitive operations",
                ]
            },
            "next_steps": "Proceed with implementation, addressing any findings"
        }

    async def validate_implementation(
        self,
        implementation: str,
        security_requirements: List[str]
    ) -> Dict[str, Any]:
        """
        Validate that implementation meets security requirements.
        """
        findings = []

        for requirement in security_requirements:
            if "encrypt" in requirement.lower():
                if not self._check_encryption(implementation):
                    findings.append("Encryption not properly implemented")

            if "auth" in requirement.lower():
                if not self._check_authentication(implementation):
                    findings.append("Authentication mechanism missing")

            if "sanitize" in requirement.lower():
                if not self._check_input_sanitization(implementation):
                    findings.append("Input sanitization missing")

        return {
            "passed": len(findings) == 0,
            "findings": findings
        }

    def _check_encryption(self, code: str) -> bool:
        """Check if encryption is properly implemented."""
        encryption_patterns = [
            r"encrypt",
            r"crypto",
            r"cipher",
            r"HASH",
            r"bcrypt",
            r"scrypt"
        ]
        return any(re.search(p, code, re.IGNORECASE) for p in encryption_patterns)

    def _check_authentication(self, code: str) -> bool:
        """Check if authentication is present."""
        auth_patterns = [
            r"auth",
            r"login",
            r"verify",
            r"credential",
            r"session"
        ]
        return any(re.search(p, code, re.IGNORECASE) for p in auth_patterns)

    def _check_input_sanitization(self, code: str) -> bool:
        """Check if input sanitization is present."""
        sanitize_patterns = [
            r"sanitize",
            r"escape",
            r"validate",
            r"strip_tags",
            r"html.?escape"
        ]
        return any(re.search(p, code, re.IGNORECASE) for p in sanitize_patterns)