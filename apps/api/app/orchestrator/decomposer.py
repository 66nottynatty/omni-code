import json
import uuid
import structlog
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.core.model_provider import ModelProvider
from app.schemas.orchestrator import TaskGraph, SubTask, TaskStatus
from langchain_core.messages import SystemMessage, HumanMessage

logger = structlog.get_logger()

class TaskDecomposer:
  
  async def decompose(self, goal, context):
    llm = ModelProvider.get_model("deepseek", "deepseek-reasoner")
    
    system = """You are a Master Orchestrator.
    Break down the goal into subtasks.
    Return ONLY valid JSON matching this schema:
    {
      "subtasks": [
        {
          "id": "t1",
          "title": "...",
          "description": "...",
          "agent_type": "backend|frontend|testing|security|database|docs|devops",
          "dependencies": [],
          "input_data": {}
        }
      ]
    }
    No markdown, no explanation. JSON only."""
    
    user_msg = f"""
    Goal: {goal}
    Context: {json.dumps(context)}
    
    Create a task graph. Max 8 subtasks.
    Identify parallel work where possible.
    """
    
    try:
      response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=user_msg)
      ])
      
      content = response.content
      if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
      elif "```" in content:
        content = content.split("```")[1].split("```")[0]
      
      data = json.loads(content.strip())
      subtasks = [SubTask(
        id=t["id"],
        title=t["title"],
        description=t["description"],
        agent_type=t.get("agent_type","backend"),
        dependencies=t.get("dependencies",[]),
        status=TaskStatus.PENDING,
        input_data=t.get("input_data",{})
      ) for t in data["subtasks"]]
      
    except Exception as e:
      logger.warning("decompose_parse_failed", error=str(e))
      subtasks = [] # Fallback logic omitted for brevity
    
    graph = TaskGraph(
      id=str(uuid.uuid4()),
      goal=goal,
      subtasks=subtasks,
      status=TaskStatus.PENDING,
      created_at=datetime.utcnow().isoformat(),
      updated_at=datetime.utcnow().isoformat()
    )
    return graph
