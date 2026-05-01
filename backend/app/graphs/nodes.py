from typing import Literal
from .state import AgentState
from app.intelligence.tools import read_file, write_file, search_codebase, run_terminal, report_blocker
from app.core.model_provider import ModelProvider
from langchain_core.messages import ToolMessage
from app.database.session import SessionLocal
from app.database.models import TaskLog
import redis
import logging
import json

logger = logging.getLogger(__name__)
from app.core.config import get_settings
settings = get_settings()
redis_client = redis.from_url(settings.redis_url)

tools = [read_file, write_file, search_codebase, run_terminal, report_blocker]
tools_by_name = {t.name: t for t in tools}

def _log_to_db_and_redis(task_id: int | None, content: str, level: str = "info"):
    if not task_id:
        return
    
    # DB Log
    db = SessionLocal()
    try:
        log = TaskLog(task_id=task_id, content=content, level=level)
        db.add(log)
        db.commit()
    finally:
        db.close()
    
    # Redis Pub/Sub for real-time
    redis_client.publish(f"task_logs_{task_id}", json.dumps({
        "content": content,
        "level": level,
        "task_id": task_id
    }))

def call_model(state: AgentState):
    task_id = state.get("task_id")
    _log_to_db_and_redis(task_id, "Calling model for next steps...")
    
    messages = state["messages"]
    provider, model_name = ModelProvider.route_model("coding")
    llm = ModelProvider.get_model(provider, model_name)
    llm_with_tools = llm.bind_tools(tools)
    
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def execute_tools(state: AgentState):
    task_id = state.get("task_id")
    messages = state["messages"]
    last_message = messages[-1]
    
    tool_messages = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        _log_to_db_and_redis(task_id, f"Executing tool: {tool_name}")
        
        # Inject thread_id/workspace_id/task_id if needed
        if tool_name in ["write_file", "run_terminal"]:
            tool_args["thread_id"] = state.get("thread_id")
        if tool_name == "search_codebase":
            tool_args["workspace_id"] = state.get("workspace_id")
        if tool_name == "report_blocker":
            tool_args["task_id"] = state.get("task_id")
            
        tool = tools_by_name[tool_name]
        try:
            result = tool.invoke(tool_args)
            _log_to_db_and_redis(task_id, f"Tool {tool_name} completed.")
        except Exception as e:
            result = str(e)
            _log_to_db_and_redis(task_id, f"Tool {tool_name} failed: {result}", level="error")
        
        tool_messages.append(ToolMessage(
            tool_call_id=tool_call["id"],
            content=str(result)
        ))
        
    return {"messages": tool_messages}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "__end__"
