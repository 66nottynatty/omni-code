import abc
from typing import Dict, Any, List, Optional
from ..schemas.orchestrator import SubTask, TaskStatus
import asyncio
import structlog
import json
import time

logger = structlog.get_logger()


class BaseAgent(abc.ABC):
    """
    Base class for all specialized agents.
    
    Provides the core execution loop (Think → Act → Conclude),
    logging infrastructure, and tool integration via MCP.
    """

    def __init__(self, agent_id: str, name: str, redis_client=None):
        self.agent_id = agent_id
        self.name = name
        self.redis_client = redis_client
        self._token_budget = 100000  # Token budget for the agent
        self._tokens_used = 0

    async def run(self, task: SubTask, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution loop for the agent.
        
        Implements the Think → Act → Conclude pattern:
        1. Think: Analyze the task and plan approach
        2. Act: Execute the plan using available tools
        3. Conclude: Compile results and prepare output
        """
        logger.info("agent_run_start", agent=self.name, task_id=task.id)

        start_time = time.time()

        try:
            # 1. Thought phase
            thought = await self.think(task, context)
            await self.publish_log(
                task.id,
                f"🧠 Thinking: {thought}",
                log_type="thought"
            )

            # 2. Action phase
            observation = await self.act(task, context, thought)
            await self.publish_log(
                task.id,
                f"🎬 Acting: {observation}",
                log_type="action"
            )

            # 3. Self-correction phase (optional validation)
            corrected_observation = await self.validate_and_correct(
                task, context, observation
            )

            # 4. Conclusion phase
            result = await self.conclude(task, context, corrected_observation)

            # Calculate execution time
            execution_time = time.time() - start_time
            result["execution_time_seconds"] = round(execution_time, 2)
            result["agent"] = self.name

            logger.info(
                "agent_run_complete",
                agent=self.name,
                task_id=task.id,
                execution_time=execution_time
            )

            return result

        except Exception as e:
            logger.error(
                "agent_run_failed",
                agent=self.name,
                task_id=task.id,
                error=str(e)
            )
            await self.publish_log(
                task.id,
                f"❌ Error: {str(e)}",
                log_type="error"
            )
            raise

    @abc.abstractmethod
    async def think(self, task: SubTask, context: Dict[str, Any]) -> str:
        """
        Analyze the task and formulate an approach.
        
        This is where the agent should:
        - Understand the requirements
        - Identify necessary tools/resources
        - Plan the implementation approach
        - Load relevant skills/prompts
        
        Returns:
            A string describing the agent's thought process
        """
        pass

    @abc.abstractmethod
    async def act(self, task: SubTask, context: Dict[str, Any], thought: str) -> str:
        """
        Execute the planned approach using tools.
        
        This is where the agent should:
        - Use MCP tools to perform actions
        - Read/write files, run commands
        - Call external APIs
        - Modify the codebase
        
        Returns:
            A string describing the outcome of the actions
        """
        pass

    async def conclude(
        self,
        task: SubTask,
        context: Dict[str, Any],
        observation: str
    ) -> Dict[str, Any]:
        """
        Compile the results of the execution.
        
        This is where the agent should:
        - Summarize what was done
        - Identify next steps
        - Prepare output data for dependent tasks
        
        Returns:
            A dictionary with the task result and metadata
        """
        return {
            "status": "success",
            "observation": observation,
            "task_id": task.id,
            "next_steps": [
                "Review output",
                "Test the implementation",
                "Proceed to dependent tasks"
            ]
        }

    async def validate_and_correct(
        self,
        task: SubTask,
        context: Dict[str, Any],
        observation: str
    ) -> str:
        """
        Optional validation step for self-correction.
        
        This allows the agent to verify its work before
        concluding. Override in subclasses for custom validation.
        
        Returns:
            The (possibly corrected) observation
        """
        return observation

    async def publish_log(
        self,
        task_id: str,
        message: str,
        log_type: str = "info"
    ):
        """
        Publish a log message for streaming via SSE.
        
        Args:
            task_id: The ID of the current task
            message: The log message
            log_type: Type of log (info, thought, action, error, warning)
        """
        log_data = {
            "task_id": task_id,
            "agent": self.name,
            "agent_id": self.agent_id,
            "message": message,
            "type": log_type,
            "timestamp": time.time(),
            "tokens_used": self._tokens_used,
            "token_budget_remaining": self._token_budget - self._tokens_used
        }

        # Print to console for development
        print(f"[{self.name}] {message}")

        # Publish to Redis for SSE streaming if available
        if self.redis_client:
            try:
                channel = f"agent_logs_{task_id}"
                self.redis_client.publish(
                    channel,
                    json.dumps(log_data)
                )
            except Exception as e:
                logger.warning(
                    "failed_to_publish_log",
                    task_id=task_id,
                    error=str(e)
                )

    async def heartbeat(self):
        """
        Updates the agent's last seen timestamp.
        
        This can be used by the orchestrator to detect
        hung or stalled agents.
        """
        if self.redis_client:
            try:
                key = f"agent:heartbeat:{self.agent_id}"
                self.redis_client.setex(key, 60, time.time())
            except Exception as e:
                logger.warning(
                    "failed_to_update_heartbeat",
                    agent_id=self.agent_id,
                    error=str(e)
                )

    def check_token_budget(self, tokens_needed: int) -> bool:
        """
        Check if there are enough tokens remaining in the budget.
        
        Args:
            tokens_needed: Number of tokens needed for the next operation
            
        Returns:
            True if the operation is within budget
        """
        return (self._tokens_used + tokens_needed) <= self._token_budget

    def add_token_usage(self, tokens: int):
        """
        Track token usage for cost monitoring.
        
        Args:
            tokens: Number of tokens used
        """
        self._tokens_used += tokens

    async def read_skill(self, skill_name: str, workspace_id: Optional[int] = None) -> str:
        """
        Read a skill from the skill registry.
        
        This helper method allows agents to load relevant
        skills for their tasks.
        
        Args:
            skill_name: Name of the skill to read
            workspace_id: Optional workspace ID for workspace-specific skills
            
        Returns:
            The content of the skill, or an empty string if not found
        """
        try:
            from app.intelligence.tools import read_skill as tools_read_skill
            return tools_read_skill(skill_name, workspace_id)
        except Exception as e:
            logger.warning(
                "failed_to_read_skill",
                skill_name=skill_name,
                error=str(e)
            )
            return ""

    async def get_workspace_context(self, workspace_id: int) -> Dict[str, Any]:
        """
        Get context about the workspace for better task execution.
        
        Args:
            workspace_id: The workspace ID
            
        Returns:
            Dictionary with workspace context
        """
        context = {
            "workspace_id": workspace_id,
            "tech_stack": [],
            "file_structure": {},
            "recent_changes": []
        }

        try:
            from app.database.models import Workspace
            from app.database.session import SessionLocal

            db = SessionLocal()
            workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()

            if workspace:
                context["owner"] = workspace.owner
                context["repo"] = workspace.repo
                context["branch"] = workspace.branch

            db.close()
        except Exception as e:
            logger.warning(
                "failed_to_get_workspace_context",
                workspace_id=workspace_id,
                error=str(e)
            )

        return context


class AgentResponse:
    """Structured response from agent execution."""

    def __init__(
        self,
        status: str,
        observation: str,
        artifacts: Optional[Dict[str, Any]] = None,
        errors: Optional[List[str]] = None
    ):
        self.status = status
        self.observation = observation
        self.artifacts = artifacts or {}
        self.errors = errors or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "observation": self.observation,
            "artifacts": self.artifacts,
            "errors": self.errors
        }


class AgentValidator:
    """
    Validator for checking agent output quality.
    
    Can be used in the validate_and_correct phase to ensure
    output meets quality standards.
    """

    @staticmethod
    def validate_code_output(code: str, requirements: List[str]) -> Dict[str, Any]:
        """
        Validate that code meets requirements.
        
        Args:
            code: The code to validate
            requirements: List of requirement strings to check
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        for req in requirements:
            req_lower = req.lower()
            if req_lower not in code.lower():
                issues.append(f"Missing requirement: {req}")

        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

    @staticmethod
    def validate_file_exists(file_path: str) -> bool:
        """Check if a file exists."""
        import os
        return os.path.exists(file_path)