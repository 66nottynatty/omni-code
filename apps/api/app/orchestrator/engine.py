import asyncio
from typing import Dict, List, Any, Optional
from .decomposer import TaskDecomposer
from .model_router import ModelRouter, ModelCapability
from .mcp_manager import MCPManager
from .agents.base import BaseAgent
from .agents.backend_agent import BackendAgent
from .agents.frontend_agent import FrontendAgent
from .agents.security_agent import SecurityAgent
from .agents.devops_agent import DevOpsAgent
from ..schemas.orchestrator import TaskGraph, SubTask, TaskStatus
from ..database.models import TaskGraphModel, SubTaskModel, TaskCheckpointModel, AgentSessionModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
import structlog
import json
from datetime import datetime, timedelta
from enum import Enum

logger = structlog.get_logger()


class RecoveryLevel(Enum):
    """Recovery escalation levels."""
    RETRY = 1
    REPLAN = 2
    ESCALATE = 3


class TokenBudget:
    """Token budget tracking for cost control."""
    
    def __init__(self, max_tokens: int = 100000):
        self.max_tokens = max_tokens
        self.used_tokens = 0
        self.budget_warned = False
    
    def check(self, tokens_needed: int) -> bool:
        """Check if token allocation is within budget."""
        return (self.used_tokens + tokens_needed) <= self.max_tokens
    
    def allocate(self, tokens: int):
        """Allocate tokens to usage."""
        self.used_tokens += tokens
        if not self.budget_warned and self.used_tokens > self.max_tokens * 0.8:
            logger.warning("token_budget_warning", used=self.used_tokens, max=self.max_tokens)
            self.budget_warned = True
    
    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens - self.used_tokens)


class OrchestratorEngine:
    """
    Master orchestrator engine for task-graph execution.
    """

    def __init__(self, db_session: AsyncSession = None, redis_client=None):
        self.model_router = ModelRouter()
        self.decomposer = TaskDecomposer(self.model_router)
        self.mcp_manager = MCPManager()
        self.db = db_session
        self.redis_client = redis_client
        self.token_budget = TokenBudget()
        self.active_graphs: Dict[str, TaskGraph] = {}
        
    async def execute_workflow(
        self,
        prompt: str,
        workspace_id: int,
        prefer_local: bool = False
    ) -> TaskGraph:
        """
        Main entry point to start a workflow.
        """
        context = {
            "workspace_id": workspace_id,
            "prefer_local": prefer_local,
            "graph_context": {}
        }
        
        # Decompose goal into task graph
        graph = await self.decomposer.decompose(prompt, context)
        
        # Save graph to DB
        await self.save_graph_to_db(graph, workspace_id)
        
        logger.info(
            "workflow_started",
            graph_id=graph.id,
            subtasks_count=len(graph.subtasks),
            workspace_id=workspace_id
        )
        
        # Store reference for SSE streaming
        self.active_graphs[graph.id] = graph
        
        # Start execution in background
        asyncio.create_task(self.run_graph(graph))
        
        return graph

    async def save_graph_to_db(self, graph: TaskGraph, workspace_id: int):
        """Save task graph to database."""
        if not self.db:
            return
            
        db_graph = TaskGraphModel(
            id=graph.id,
            goal=graph.goal,
            status=graph.status,
            workspace_id=workspace_id
        )
        self.db.add(db_graph)
        
        for st in graph.subtasks:
            db_subtask = SubTaskModel(
                id=st.id,
                graph_id=graph.id,
                title=st.title,
                description=st.description,
                agent_type=st.agent_type,
                model_id=st.model_id,
                status=st.status.value,
                dependencies=st.dependencies,
                input_data=st.input_data,
                retry_count=st.retry_count,
                max_retries=st.max_retries
            )
            self.db.add(db_subtask)
        
        await self.db.commit()

    async def run_graph(self, graph: TaskGraph):
        """
        Executes the subtasks in the graph according to their dependencies.
        """
        await self.update_graph_status(graph.id, TaskStatus.RUNNING)
        graph.status = TaskStatus.RUNNING
        
        logger.info("graph_execution_started", graph_id=graph.id)
        
        while not self._is_graph_complete(graph):
            # Check for control signals
            if self.redis_client:
                signal = self.redis_client.get(f"graph_signal_{graph.id}")
                if signal == b"pause":
                    await self._publish_graph_update(graph.id, "paused", {})
                    while True:
                        await asyncio.sleep(1)
                        sig = self.redis_client.get(f"graph_signal_{graph.id}")
                        if sig != b"pause":
                            break
                    await self._publish_graph_update(graph.id, "resumed", {})
                elif signal == b"cancel":
                    await self.update_graph_status(graph.id, TaskStatus.CANCELLED)
                    graph.status = TaskStatus.CANCELLED
                    self.redis_client.delete(f"graph_signal_{graph.id}")
                    return

            # Find tasks that are ready to run
            ready_tasks = self._get_ready_tasks(graph)
            
            if not ready_tasks:
                if self._has_blocked_or_failed_tasks(graph):
                    # For simplicity in this mock, we break on failure
                    break
                await asyncio.sleep(1)
                continue

            for task in ready_tasks:
                if not self.token_budget.check(5000):
                    logger.warning("token_budget_exceeded", graph_id=graph.id)
                    break
                asyncio.create_task(self.run_subtask(graph, task))

            await asyncio.sleep(0.5)

        # Update final status
        if graph.status != TaskStatus.CANCELLED:
            final_status = TaskStatus.COMPLETED if self._is_graph_complete(graph) else TaskStatus.FAILED
            await self.update_graph_status(graph.id, final_status)
            graph.status = final_status
        
        logger.info(
            "graph_execution_completed",
            graph_id=graph.id,
            status=graph.status.value
        )

    def _is_graph_complete(self, graph: TaskGraph) -> bool:
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            for t in graph.subtasks
        )

    def _has_blocked_or_failed_tasks(self, graph: TaskGraph) -> bool:
        return any(
            t.status in (TaskStatus.BLOCKED, TaskStatus.FAILED)
            for t in graph.subtasks
        )

    def _get_ready_tasks(self, graph: TaskGraph) -> List[SubTask]:
        return [
            t for t in graph.subtasks 
            if t.status == TaskStatus.PENDING and 
            all(self.get_task_status_local(graph, dep_id) == TaskStatus.COMPLETED 
                for dep_id in t.dependencies)
        ]

    async def run_subtask(
        self,
        graph: TaskGraph,
        task: SubTask,
        context_overrides: Optional[Dict[str, Any]] = None
    ):
        await self.update_subtask_status(task.id, TaskStatus.RUNNING)
        task.status = TaskStatus.RUNNING
        
        context = self._build_agent_context(graph, task)
        if context_overrides:
            context.update(context_overrides)
        
        agent = self.get_agent(task.agent_type, task.id, self.mcp_manager, self.redis_client)
        
        try:
            result = await agent.run(task, context)
            task.output_data = result
            task.status = TaskStatus.COMPLETED
            
            estimated_tokens = result.get("tokens_used", 1000)
            self.token_budget.allocate(estimated_tokens)
            
            await self.update_subtask_status(
                task.id,
                TaskStatus.COMPLETED,
                output_data=result,
                completed_at=datetime.utcnow()
            )
            await self._publish_task_update(graph.id, task, "completed")
            
        except Exception as e:
            task.retry_count += 1
            logger.error("subtask_failed", task_id=task.id, error=str(e))
            
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING
                await self.update_subtask_status(task.id, TaskStatus.PENDING, retry_count=task.retry_count)
            else:
                task.status = TaskStatus.FAILED
                await self.update_subtask_status(task.id, TaskStatus.FAILED)
                await self._publish_graph_update(graph.id, "failed", {"error": str(e)})

    def _build_agent_context(self, graph: TaskGraph, task: SubTask) -> Dict[str, Any]:
        dependency_outputs = {}
        for dep_id in task.dependencies:
            for t in graph.subtasks:
                if t.id == dep_id and t.output_data:
                    dependency_outputs[dep_id] = t.output_data
        
        context = {
            "workspace_id": getattr(graph, 'workspace_id', None),
            "graph_id": graph.id,
            "graph_goal": graph.goal,
            "dependency_outputs": dependency_outputs,
            "token_budget_remaining": self.token_budget.remaining
        }
        return context

    async def update_graph_status(self, graph_id: str, status: TaskStatus):
        if self.db:
            try:
                await self.db.execute(
                    update(TaskGraphModel)
                    .where(TaskGraphModel.id == graph_id)
                    .values(status=status.value, updated_at=datetime.utcnow())
                )
                await self.db.commit()
            except Exception as e:
                logger.error("db_update_failed", error=str(e))

    async def update_subtask_status(
        self,
        task_id: str,
        status: TaskStatus,
        output_data: Optional[Dict] = None,
        retry_count: Optional[int] = None,
        completed_at: Optional[datetime] = None
    ):
        if not self.db:
            return
        try:
            values = {"status": status.value}
            if output_data: values["output_data"] = output_data
            if retry_count is not None: values["retry_count"] = retry_count
            if completed_at: values["completed_at"] = completed_at
            
            await self.db.execute(
                update(SubTaskModel).where(SubTaskModel.id == task_id).values(**values)
            )
            await self.db.commit()
        except Exception as e:
            logger.error("subtask_update_failed", task_id=task_id, error=str(e))

    def get_task_status_local(self, graph: TaskGraph, task_id: str) -> TaskStatus:
        for t in graph.subtasks:
            if t.id == task_id: return t.status
        return TaskStatus.FAILED

    async def _publish_task_update(self, graph_id: str, task: SubTask, status: str):
        if not self.redis_client: return
        try:
            update_data = {
                "type": "task_update",
                "graph_id": graph_id,
                "task": {"id": task.id, "title": task.title, "status": task.status.value},
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.redis_client.publish(f"graph_updates_{graph_id}", json.dumps(update_data))
        except Exception as e:
            logger.warning("redis_publish_failed", error=str(e))

    async def _publish_graph_update(self, graph_id: str, status: str, context: Dict[str, Any]):
        if not self.redis_client: return
        try:
            update_data = {
                "type": "graph_update",
                "graph_id": graph_id,
                "status": status,
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.redis_client.publish(f"graph_updates_{graph_id}", json.dumps(update_data))
        except Exception as e:
            logger.warning("redis_publish_failed", error=str(e))

    def get_agent(self, agent_type: str, task_id: str, mcp_manager=None, redis_client=None) -> BaseAgent:
        agent_map = {"backend": BackendAgent, "frontend": FrontendAgent, "security": SecurityAgent, "devops": DevOpsAgent}
        agent_class = agent_map.get(agent_type, BackendAgent)
        return agent_class(agent_id=task_id, mcp_manager=mcp_manager, redis_client=redis_client)

    async def recover_running_graphs(self):
        if not self.db: return
        try:
            result = await self.db.execute(select(TaskGraphModel).where(TaskGraphModel.status == TaskStatus.RUNNING.value))
            for db_graph in result.scalars().all():
                logger.info("recovering_graph", graph_id=db_graph.id)
                res = await self.db.execute(select(SubTaskModel).where(SubTaskModel.graph_id == db_graph.id))
                subtasks = [SubTask(id=st.id, title=st.title, description=st.description, agent_type=st.agent_type, status=TaskStatus(st.status), dependencies=st.dependencies or []) for st in res.scalars().all()]
                graph = TaskGraph(id=db_graph.id, goal=db_graph.goal, subtasks=subtasks, status=TaskStatus.RUNNING)
                asyncio.create_task(self.run_graph(graph))
        except Exception as e:
            logger.error("recovery_failed", error=str(e))
