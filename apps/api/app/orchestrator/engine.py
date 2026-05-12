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
    
    Features:
    - Dynamic graph modification and self-correction
    - Multi-level recovery with escalation
    - Token budget monitoring
    - Parallel task execution with dependency management
    - State persistence and recovery
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
        
        Args:
            prompt: User prompt describing the goal
            workspace_id: Workspace context ID
            prefer_local: Whether to prefer local models
            
        Returns:
            The created TaskGraph
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
        
        Uses a DAG-based execution model with parallel task scheduling.
        """
        await self.update_graph_status(graph.id, TaskStatus.RUNNING)
        graph.status = TaskStatus.RUNNING
        
        logger.info("graph_execution_started", graph_id=graph.id)
        
        while not self._is_graph_complete(graph):
            # Find tasks that are ready to run
            ready_tasks = self._get_ready_tasks(graph)
            
            if not ready_tasks:
                # Check if we have blocked or failed tasks
                if self._has_blocked_or_failed_tasks(graph):
                    await self._handle_blocked_tasks(graph)
                    break
                    
                await asyncio.sleep(1)
                continue

            # Start ready tasks in parallel (respecting token budget)
            for task in ready_tasks:
                if not self.token_budget.check(5000):  # Estimate 5000 tokens per task
                    logger.warning("token_budget_exceeded", graph_id=graph.id)
                    break
                    
                asyncio.create_task(self.run_subtask(graph, task))

            # Brief pause before checking for next batch
            await asyncio.sleep(0.5)

        # Update final status
        final_status = TaskStatus.COMPLETED if self._is_graph_complete(graph) else TaskStatus.FAILED
        await self.update_graph_status(graph.id, final_status)
        graph.status = final_status
        
        logger.info(
            "graph_execution_completed",
            graph_id=graph.id,
            status=final_status.value
        )

    def _is_graph_complete(self, graph: TaskGraph) -> bool:
        """Check if all tasks are completed or failed."""
        return all(
            t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
            for t in graph.subtasks
        )

    def _has_blocked_or_failed_tasks(self, graph: TaskGraph) -> bool:
        """Check if there are any blocked or failed tasks."""
        return any(
            t.status in (TaskStatus.BLOCKED, TaskStatus.FAILED)
            for t in graph.subtasks
        )

    def _get_ready_tasks(self, graph: TaskGraph) -> List[SubTask]:
        """Get tasks that are ready to execute."""
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
        """
        Execute a single subtask with full context.
        
        Args:
            graph: The parent task graph
            task: The task to execute
            context_overrides: Optional context modifications
        """
        await self.update_subtask_status(task.id, TaskStatus.RUNNING)
        task.status = TaskStatus.RUNNING
        
        # Build full context for the agent
        context = self._build_agent_context(graph, task)
        if context_overrides:
            context.update(context_overrides)
        
        # Create agent instance
        agent = self.get_agent(task.agent_type, task.id, self.mcp_manager, self.redis_client)
        
        # Create checkpoint before execution
        await self.create_checkpoint(graph.id)
        
        try:
            # Run agent with task and context
            result = await agent.run(task, context)
            
            # Update task with results
            task.output_data = result
            task.status = TaskStatus.COMPLETED
            
            # Log model feedback
            estimated_tokens = result.get("tokens_used", 1000)
            self.token_budget.allocate(estimated_tokens)
            
            self.model_router.log_feedback(
                model_id=task.model_id or "gpt-4o",
                success=True,
                latency=result.get("execution_time_seconds", 1.0),
                tokens_used=estimated_tokens
            )
            
            await self.update_subtask_status(
                task.id,
                TaskStatus.COMPLETED,
                output_data=result,
                tokens_used=estimated_tokens,
                completed_at=datetime.utcnow()
            )
            
            # Publish success to Redis for SSE
            await self._publish_task_update(graph.id, task, "completed")
            
        except Exception as e:
            task.retry_count += 1
            
            logger.error(
                "subtask_failed",
                task_id=task.id,
                error=str(e),
                retry_count=task.retry_count
            )
            
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.PENDING
                await self.update_subtask_status(
                    task.id,
                    TaskStatus.PENDING,
                    retry_count=task.retry_count
                )
            else:
                task.status = TaskStatus.FAILED
                await self.update_subtask_status(task.id, TaskStatus.FAILED)
                
                # Trigger recovery mechanism
                recovery_level = self._determine_recovery_level(task)
                await self.trigger_recovery(graph, task, e, recovery_level)
        
        # Create checkpoint after execution
        await self.create_checkpoint(graph.id)

    def _build_agent_context(
        self,
        graph: TaskGraph,
        task: SubTask
    ) -> Dict[str, Any]:
        """
        Build comprehensive context for the agent.
        
        Includes:
        - Graph goal and structure
        - Output from dependent tasks
        - Workspace information
        - Token budget status
        """
        # Gather outputs from completed dependencies
        dependency_outputs = {}
        for dep_id in task.dependencies:
            for t in graph.subtasks:
                if t.id == dep_id and t.output_data:
                    dependency_outputs[dep_id] = t.output_data
        
        # Build context
        context = {
            "workspace_id": getattr(graph, 'workspace_id', None),
            "graph_id": graph.id,
            "graph_goal": graph.goal,
            "task_dependencies": task.dependencies,
            "dependency_outputs": dependency_outputs,
            "token_budget_remaining": self.token_budget.remaining,
            "total_tasks": len(graph.subtasks),
            "completed_tasks": sum(
                1 for t in graph.subtasks 
                if t.status == TaskStatus.COMPLETED
            )
        }
        
        return context

    def _determine_recovery_level(self, task: SubTask) -> RecoveryLevel:
        """Determine appropriate recovery level based on task history."""
        if task.retry_count >= 3:
            return RecoveryLevel.ESCALATE
        elif task.retry_count >= 1:
            return RecoveryLevel.REPLAN
        return RecoveryLevel.RETRY

    async def trigger_recovery(
        self,
        graph: TaskGraph,
        task: SubTask,
        error: Exception,
        recovery_level: RecoveryLevel = RecoveryLevel.RETRY
    ):
        """
        Trigger recovery mechanism with escalation.
        
        Level 1 (RETRY): Simply retry with same context
        Level 2 (REPLAN): Replan the failed task with new approach
        Level 3 (ESCALATE): Invoke Master Agent to re-plan entire graph
        """
        logger.warning(
            "triggering_recovery",
            task_id=task.id,
            error=str(error),
            level=recovery_level.name
        )
        
        if recovery_level == RecoveryLevel.RETRY:
            # Just retry - already handled by run_subtask
            pass
            
        elif recovery_level == RecoveryLevel.REPLAN:
            # Replan the specific task
            await self._replan_task(graph, task, error)
            
        elif recovery_level == RecoveryLevel.ESCALATE:
            # Master Agent takes over - re-plan entire graph
            await self._master_agent_replan(graph, task, error)

    async def _replan_task(
        self,
        graph: TaskGraph,
        task: SubTask,
        error: Exception
    ):
        """Replan a failed task with modified approach."""
        logger.info("replanning_task", task_id=task.id)
        
        # Update task description with failure context
        task.description = (
            f"{task.description}\n\n"
            f"Previous attempt failed: {str(error)}\n"
            "Please try a different approach."
        )
        
        # Reset status to pending for retry
        task.status = TaskStatus.PENDING
        await self.update_subtask_status(task.id, TaskStatus.PENDING)

    async def _master_agent_replan(
        self,
        graph: TaskGraph,
        task: SubTask,
        error: Exception
    ):
        """
        Level 3 Recovery: Master Agent re-plans the entire graph.
        
        This is invoked when a task fails repeatedly and requires
        a higher-level strategic approach.
        """
        logger.info("master_agent_replan", graph_id=graph.id)
        
        # Build context about the failure
        failure_context = {
            "failed_task": task.id,
            "error": str(error),
            "completed_tasks": [
                {"id": t.id, "output": t.output_data}
                for t in graph.subtasks if t.status == TaskStatus.COMPLETED
            ],
            "failed_tasks": [
                t.id for t in graph.subtasks if t.status == TaskStatus.FAILED
            ],
            "pending_tasks": [
                t.id for t in graph.subtasks if t.status == TaskStatus.PENDING
            ]
        }
        
        # Mark graph as needing replan
        await self.update_graph_status(graph.id, TaskStatus.FAILED)
        
        # Log for monitoring/alerting
        logger.error(
            "graph_failed_requiring_replan",
            graph_id=graph.id,
            **failure_context
        )
        
        # Notify via Redis about the failure
        await self._publish_graph_update(graph.id, "failed", failure_context)

    async def update_graph_status(self, graph_id: str, status: TaskStatus):
        """Update graph status in database."""
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
        tokens_used: Optional[int] = None,
        completed_at: Optional[datetime] = None
    ):
        """Update subtask status in database."""
        if not self.db:
            return
            
        try:
            values = {"status": status.value}
            if output_data:
                values["output_data"] = output_data
            if retry_count is not None:
                values["retry_count"] = retry_count
            if tokens_used is not None:
                values["tokens_used"] = tokens_used
            if completed_at:
                values["completed_at"] = completed_at
            
            await self.db.execute(
                update(SubTaskModel).where(SubTaskModel.id == task_id).values(**values)
            )
            await self.db.commit()
        except Exception as e:
            logger.error("subtask_update_failed", task_id=task_id, error=str(e))

    def get_task_status_local(self, graph: TaskGraph, task_id: str) -> TaskStatus:
        """Get task status from local graph state."""
        for t in graph.subtasks:
            if t.id == task_id:
                return t.status
        return TaskStatus.FAILED

    async def create_checkpoint(self, graph_id: str):
        """Create a checkpoint of current graph state."""
        if not self.db:
            return
            
        try:
            # Get current state
            result = await self.db.execute(
                select(TaskGraphModel).where(TaskGraphModel.id == graph_id)
            )
            db_graph = result.scalar_one_or_none()
            if not db_graph:
                return
                
            result = await self.db.execute(
                select(SubTaskModel).where(SubTaskModel.graph_id == graph_id)
            )
            subtasks = result.scalars().all()
            
            state = {
                "graph_status": db_graph.status,
                "subtasks": {
                    st.id: {
                        "status": st.status,
                        "output_data": st.output_data,
                        "retry_count": st.retry_count
                    }
                    for st in subtasks
                }
            }
            
            # Count existing checkpoints
            result = await self.db.execute(
                select(TaskCheckpointModel).where(TaskCheckpointModel.graph_id == graph_id)
            )
            checkpoint_count = len(result.scalars().all())
            
            checkpoint = TaskCheckpointModel(
                graph_id=graph_id,
                checkpoint_number=checkpoint_count + 1,
                state_snapshot=state
            )
            self.db.add(checkpoint)
            await self.db.commit()
            
        except Exception as e:
            logger.error("checkpoint_failed", graph_id=graph_id, error=str(e))

    async def _publish_task_update(
        self,
        graph_id: str,
        task: SubTask,
        status: str
    ):
        """Publish task update to Redis for SSE streaming."""
        if not self.redis_client:
            return
            
        try:
            update_data = {
                "type": "task_update",
                "graph_id": graph_id,
                "task_id": task.id,
                "status": status,
                "task": {
                    "id": task.id,
                    "title": task.title,
                    "agent_type": task.agent_type,
                    "status": task.status.value,
                    "output_data": task.output_data
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.redis_client.publish(
                f"graph_updates_{graph_id}",
                json.dumps(update_data)
            )
        except Exception as e:
            logger.warning("redis_publish_failed", error=str(e))

    async def _publish_graph_update(
        self,
        graph_id: str,
        status: str,
        context: Dict[str, Any]
    ):
        """Publish graph-level update to Redis."""
        if not self.redis_client:
            return
            
        try:
            update_data = {
                "type": "graph_update",
                "graph_id": graph_id,
                "status": status,
                "context": context,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.redis_client.publish(
                f"graph_updates_{graph_id}",
                json.dumps(update_data)
            )
        except Exception as e:
            logger.warning("redis_publish_failed", error=str(e))

    async def recover_running_graphs(self):
        """Find and resume graphs that were running but interrupted."""
        if not self.db:
            return
            
        try:
            result = await self.db.execute(
                select(TaskGraphModel).where(TaskGraphModel.status == TaskStatus.RUNNING.value)
            )
            running_graphs = result.scalars().all()
            
            for db_graph in running_graphs:
                logger.info("recovering_graph", graph_id=db_graph.id)
                
                # Fetch subtasks
                result = await self.db.execute(
                    select(SubTaskModel).where(SubTaskModel.graph_id == db_graph.id)
                )
                db_subtasks = result.scalars().all()
                
                subtasks = [
                    SubTask(
                        id=st.id,
                        title=st.title,
                        description=st.description,
                        agent_type=st.agent_type,
                        status=TaskStatus(st.status),
                        dependencies=st.dependencies or [],
                        input_data=st.input_data or {},
                        output_data=st.output_data,
                        retry_count=st.retry_count or 0,
                        max_retries=st.max_retries or 3
                    )
                    for st in db_subtasks
                ]
                
                graph = TaskGraph(
                    id=db_graph.id,
                    goal=db_graph.goal,
                    subtasks=subtasks,
                    status=TaskStatus.RUNNING
                )
                
                # Resume execution
                asyncio.create_task(self.run_graph(graph))
                
        except Exception as e:
            logger.error("recovery_failed", error=str(e))

    async def cleanup_completed_tasks(self, ttl_days: int = 7):
        """Automatic cleanup for old completed/failed tasks."""
        if not self.db:
            return
            
        try:
            cutoff = datetime.utcnow() - timedelta(days=ttl_days)
            
            # Find old completed/failed graphs
            stmt = select(TaskGraphModel.id).where(
                TaskGraphModel.status.in_([TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]),
                TaskGraphModel.updated_at < cutoff
            )
            result = await self.db.execute(stmt)
            old_graph_ids = result.scalars().all()
            
            if old_graph_ids:
                logger.info("cleaning_up_old_graphs", count=len(old_graph_ids))
                
                # Cascade delete handles subtasks and checkpoints
                await self.db.execute(
                    delete(TaskGraphModel).where(TaskGraphModel.id.in_(old_graph_ids))
                )
                await self.db.commit()
                
        except Exception as e:
            logger.error("cleanup_failed", error=str(e))

    def get_agent(
        self,
        agent_type: str,
        task_id: str,
        mcp_manager: MCPManager = None,
        redis_client = None
    ) -> BaseAgent:
        """Get agent instance by type."""
        agent_map = {
            "backend": BackendAgent,
            "frontend": FrontendAgent,
            "security": SecurityAgent,
            "devops": DevOpsAgent,
        }
        
        agent_class = agent_map.get(agent_type, BackendAgent)
        return agent_class(
            agent_id=task_id,
            mcp_manager=mcp_manager or self.mcp_manager,
            redis_client=redis_client or self.redis_client
        )

    async def inject_task(self, graph_id: str, new_task: SubTask) -> bool:
        """
        Dynamically inject a new task into a running graph.
        
        Args:
            graph_id: Target graph ID
            new_task: Task to inject
            
        Returns:
            True if injection successful
        """
        if graph_id not in self.active_graphs:
            return False
            
        graph = self.active_graphs[graph_id]
        
        # Add to local graph
        graph.subtasks.append(new_task)
        
        # Persist to DB
        if self.db:
            db_subtask = SubTaskModel(
                id=new_task.id,
                graph_id=graph_id,
                title=new_task.title,
                description=new_task.description,
                agent_type=new_task.agent_type,
                model_id=new_task.model_id,
                status=new_task.status.value,
                dependencies=new_task.dependencies,
                input_data=new_task.input_data,
                max_retries=new_task.max_retries
            )
            self.db.add(db_subtask)
            await self.db.commit()
        
        return True

    async def modify_graph(self, graph_id: str, modifications: Dict[str, Any]) -> bool:
        """
        Modify an existing graph (add dependencies, change task order, etc.).
        
        Args:
            graph_id: Target graph ID
            modifications: Dictionary of modifications
            
        Returns:
            True if modification successful
        """
        if graph_id not in self.active_graphs:
            return False
            
        graph = self.active_graphs[graph_id]
        
        for task_id, changes in modifications.get("task_updates", {}).items():
            for task in graph.subtasks:
                if task.id == task_id:
                    if "dependencies" in changes:
                        task.dependencies = changes["dependencies"]
                    if "input_data" in changes:
                        task.input_data = changes["input_data"]
                    break
        
        return True