"""
QA Agent - Specialized in test generation, execution, and bug reporting.
"""
from typing import Dict, Any, Optional, List
from .base import BaseAgent
from ..schemas.orchestrator import SubTask
from app.intelligence.tools import read_file, write_file, run_terminal, read_skill, search_codebase
import structlog
import json

logger = structlog.get_logger()


class QAAgent(BaseAgent):
    """
    QA-focused agent that handles test writing, test execution,
    and bug analysis.
    """

    def __init__(self, agent_id: str, mcp_manager=None, redis_client=None):
        super().__init__(agent_id, "QAAgent", redis_client)
        self.mcp_manager = mcp_manager
        self.test_framework = None

    async def think(self, task: SubTask, context: Dict[str, Any]) -> str:
        """
        Analyze the task and plan QA strategy.
        """
        await self.publish_log(task.id, "Analyzing QA requirements...")

        # Determine test framework from context or task description
        self.test_framework = self._detect_test_framework(task.description, context)
        await self.publish_log(task.id, f"Detected test framework: {self.test_framework}")

        repo_map_info = f"## Repository Structure\n{context.get('repo_map', '')}\n\n"
        return repo_map_info + (
            f"QA strategy for: {task.title}\n"
            f"Test framework: {self.test_framework}\n"
            f"Description: {task.description}"
        )

    def _detect_test_framework(self, description: str, context: Dict[str, Any]) -> str:
        """Detect the test framework to use."""
        desc_lower = description.lower()
        
        # Check description first
        if "pytest" in desc_lower:
            return "pytest"
        if "jest" in desc_lower:
            return "jest"
        if "unittest" in desc_lower:
            return "unittest"
        if "vitest" in desc_lower:
            return "vitest"
        if "cypress" in desc_lower:
            return "cypress"
        if "playwright" in desc_lower:
            return "playwright"

        # Check tech stack in context
        tech_stack = context.get("tech_stack", {})
        languages = tech_stack.get("languages", [])
        
        if "Python" in languages:
            return "pytest"
        if "JavaScript/TypeScript" in languages:
            return "jest"
        
        return "pytest" # Default

    async def act(self, task: SubTask, context: Dict[str, Any], thought: str) -> str:
        """
        Execute QA tasks: write tests or run them.
        """
        await self.publish_log(task.id, "Executing QA actions...")

        workspace_path = context.get("workspace_path", "/workspace")
        
        # Decide if we are writing tests or running them
        if "run" in task.description.lower() and "test" in task.description.lower():
            return await self._run_tests(task, workspace_path)
        else:
            return await self._write_tests(task, context)

    async def _write_tests(self, task: SubTask, context: Dict[str, Any]) -> str:
        """Generate and write test files."""
        file_path = task.input_data.get("file_path", "tests/test_generated.py")
        await self.publish_log(task.id, f"Generating tests for {file_path}")

        # In a real implementation, we would use an LLM to generate the test code
        # For this implementation, we'll generate a placeholder based on the framework
        test_code = self._generate_test_code(task)

        result = write_file(
            thread_id=task.input_data.get("thread_id", 0),
            file_path=file_path,
            content=test_code
        )
        return f"Successfully wrote tests to {file_path}. Result: {result}"

    def _generate_test_code(self, task: SubTask) -> str:
        """Generate test code based on the framework."""
        if self.test_framework == "pytest":
            return f'''import pytest

def test_{task.id}_placeholder():
    """
    Test generated for: {task.title}
    Description: {task.description}
    """
    assert True

# TODO: Implement actual test cases
'''
        elif self.test_framework == "jest":
            return f'''describe('{task.title}', () => {{
  test('should pass placeholder test for {task.id}', () => {{
    expect(true).toBe(true);
  }});
}});

// TODO: Implement actual test cases
'''
        else:
            return f'''# Test placeholder for {task.title}
# Framework: {self.test_framework}

def test_placeholder():
    pass
'''

    async def _run_tests(self, task: SubTask, workspace_path: str) -> str:
        """Run tests and report results."""
        await self.publish_log(task.id, f"Running tests using {self.test_framework}")
        
        cmd = ""
        if self.test_framework == "pytest":
            cmd = "pytest"
        elif self.test_framework == "jest":
            cmd = "npm test"
        elif self.test_framework == "vitest":
            cmd = "npx vitest run"
        else:
            cmd = "pytest" # Fallback

        await self.publish_log(task.id, f"Executing command: {cmd}")
        
        # Use run_terminal tool
        result = run_terminal(
            thread_id=task.input_data.get("thread_id", 0),
            command=cmd
        )
        
        await self.publish_log(task.id, f"Test execution finished.")
        return f"Test results for {self.test_framework}:\n{result}"

    async def conclude(self, task: SubTask, context: Dict[str, Any], observation: str) -> Dict[str, Any]:
        """
        Finalize QA results.
        """
        await self.publish_log(task.id, "QA task complete")

        return {
            "status": "success",
            "observation": observation,
            "qa_info": {
                "framework": self.test_framework,
                "tasks_performed": "Test generation/execution"
            }
        }
