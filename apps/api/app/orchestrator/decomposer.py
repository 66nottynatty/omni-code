import json
import uuid
import structlog
from datetime import datetime
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from ..schemas.orchestrator import TaskGraph, SubTask, TaskStatus
from app.core.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

class TaskDecomposer:
    def __init__(self, model_router=None):
        self.model_router = model_router
        self.model = ChatOpenAI(
            model="deepseek-reasoner",
            openai_api_key=settings.deepseek_api_key,
            openai_api_base="https://api.deepseek.com/v1"
        )

    async def decompose(self, goal: str, context: Dict[str, Any] = None, db=None) -> TaskGraph:
        logger.info("decomposing_task", goal=goal)
        
        system_msg = """You are the OmniCode Master Planner. 
Decompose the user's goal into a logical TaskGraph of subtasks.
Output valid JSON only with the following structure:
{
  "subtasks": [
    {
      "id": "string",
      "title": "string",
      "description": "string",
      "agent_type": "backend|frontend|security|devops|qa",
      "dependencies": ["id1", "id2"],
      "input_data": {}
    }
  ]
}"""

        user_msg = f"Goal: {goal}\nContext: {json.dumps(context or {})}"
        
        try:
            response = await self.model.ainvoke([
                SystemMessage(content=system_msg),
                HumanMessage(content=user_msg)
            ])
            
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content.strip())
            subtasks = []
            for t in data["subtasks"]:
                # Use model router to select best model for each subtask
                model_info = await self.model_router.route(
                    complexity=0.7, # Default complexity for decomposition
                    context_size=4000,
                    prefer_local=context.get("prefer_local", False) if context else False,
                    db=db
                )
                
                subtasks.append(SubTask(
                    id=t["id"],
                    title=t["title"],
                    description=t["description"],
                    agent_type=t.get("agent_type", "backend"),
                    model_id=model_info.id,
                    dependencies=t.get("dependencies", []),
                    status=TaskStatus.PENDING,
                    input_data=t.get("input_data", {})
                ))
        except Exception as e:
            logger.warning("decomposition_failed", error=str(e))
            subtasks = [SubTask(
                id="fallback-1",
                title="Manual Review",
                description=f"Decomposition failed: {str(e)}",
                agent_type="backend",
                status=TaskStatus.PENDING
            )]

        return TaskGraph(
            id=str(uuid.uuid4()),
            goal=goal,
            subtasks=subtasks,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

    async def replan(self, original_graph: TaskGraph, failure_context: Dict[str, Any], db=None) -> TaskGraph:
        """
        Replan a failed graph by generating new tasks to address the failure.
        """
        logger.info("replanning_graph", graph_id=original_graph.id)
        # For now, just redo the decomposition with the failure context
        new_goal = f"Original Goal: {original_graph.goal}\nFailure Context: {json.dumps(failure_context)}"
        return await self.decompose(new_goal, {}, db=db)
