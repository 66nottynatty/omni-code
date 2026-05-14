import abc
from typing import Dict, Any, List, Optional
from ..schemas.orchestrator import SubTask, TaskStatus
import asyncio
import structlog
import json
import time
from app.intelligence.test_runner import TestRunner
from app.intelligence.repo_map import RepoMap

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
        self._token_budget = 100000
        self._tokens_used = 0
        self.test_runner = TestRunner()
        self.max_correction_attempts = 3

    async def run(self, task: SubTask, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution loop for the agent.
        """
        logger.info("agent_run_start", agent=self.name, task_id=task.id)
        start_time = time.time()

        # Inject Repo Map into context
        repo_map = RepoMap(context.get("workspace_path", "/workspace"))
        focus_files = task.input_data.get("relevant_files", []) if task.input_data else []
        context["repo_map"] = repo_map.build(focus_files)

        try:
            # 1. Thought phase
            thought = await self.think(task, context)
            await self.publish_log(task.id, f"🧠 {thought}", log_type="thought")

            # 1b. Planning phase
            plan = await self.plan(task, context, thought)
            await self.publish_log(task.id, f"📋 Plan: {plan}", log_type="info")

            # 2. Action phase
            observation = await self.act(task, context, thought)
            await self.publish_log(task.id, f"⚙️ {observation}", log_type="action")

            # 3. Validation & Correction phase
            observation = await self.validate_and_correct(task, context, observation)

            # 4. Conclusion phase
            result = await self.conclude(task, context, observation)
            result["execution_time_seconds"] = round(time.time() - start_time, 2)
            result["agent"] = self.name
            
            logger.info("agent_run_complete", agent=self.name, task_id=task.id)
            return result
        except Exception as e:
            logger.error("agent_run_failed", agent=self.name, task_id=task.id, error=str(e))
            await self.publish_log(task.id, f"❌ Error: {str(e)}", log_type="error")
            raise

    async def validate_and_correct(self, task: SubTask, context: Dict[str, Any], observation: str) -> str:
        """
        Validate the action results and attempt corrections if needed.
        """
        workspace_path = context.get("workspace_path", "/workspace")
        for attempt in range(self.max_correction_attempts):
            test_result = await self.test_runner.run(workspace_path)

            if test_result.get("skipped") or test_result["passed"]:
                if not test_result.get("skipped"):
                    await self.publish_log(task.id, f"✅ Tests passed: {test_result['summary']}", log_type="info")
                break

            await self.publish_log(
                task.id,
                f"⚠️ Tests failed (attempt {attempt + 1}/{self.max_correction_attempts}): {test_result['summary']}",
                log_type="warning"
            )

            if attempt < self.max_correction_attempts - 1:
                correction_context = (
                    f"Your previous implementation caused test failures.\n"
                    f"Command: {test_result.get('command', '')}\n"
                    f"Errors:\n{test_result['errors'][:2000]}\n"
                    f"Output:\n{test_result['output'][:1000]}\n\n"
                    f"Identify the root cause and fix the issue."
                )
                observation = await self.act(task, context, correction_context)
                await self.publish_log(task.id, f"🔄 Corrective Action: {observation}", log_type="action")
        return observation

    @abc.abstractmethod
    async def think(self, task: SubTask, context: Dict[str, Any]) -> str:
        pass

    async def plan(self, task: SubTask, context: Dict[str, Any], thought: str) -> str:
        """
        Default planning implementation.
        """
        return f"Execute {task.title} based on reasoning."

    @abc.abstractmethod
    async def act(self, task: SubTask, context: Dict[str, Any], thought: str) -> str:
        pass

    async def conclude(
        self,
        task: SubTask,
        context: Dict[str, Any],
        observation: str
    ) -> Dict[str, Any]:
        return {
            "status": "success",
            "observation": observation,
            "task_id": task.id
        }

    async def publish_log(
        self,
        task_id: str,
        message: str,
        log_type: str = "info"
    ):
        log_data = {
            "task_id": task_id,
            "agent": self.name,
            "agent_id": self.agent_id,
            "message": message,
            "type": log_type,
            "timestamp": time.time(),
            "tokens_used": self._tokens_used
        }
        if self.redis_client:
            try:
                channel = f"agent_logs_{task_id}"
                await self.redis_client.publish(channel, json.dumps(log_data))
            except Exception as e:
                logger.warning("failed_to_publish_log", task_id=task_id, error=str(e))

    async def publish_token(self, task_id: str, token: str):
        """Publish a single token for real-time streaming."""
        if self.redis_client:
            try:
                channel = f"agent_tokens_{task_id}"
                await self.redis_client.publish(channel, json.dumps({
                    "task_id": task_id,
                    "token": token,
                    "type": "token",
                    "timestamp": time.time()
                }))
            except Exception:
                pass

    def add_token_usage(self, tokens: int):
        self._tokens_used += tokens
