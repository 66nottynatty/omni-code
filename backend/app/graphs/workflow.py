from langgraph.graph import StateGraph, START, END
from .state import AgentState
from .nodes import call_model, execute_tools, should_continue, inject_skills_node

def create_workflow():
    """Create and compile the LangGraph workflow."""
    graph = StateGraph(AgentState)
    
    graph.add_node("inject_skills", inject_skills_node)
    graph.add_node("agent", call_model)
    graph.add_node("tools", execute_tools)
    
    graph.add_edge(START, "inject_skills")
    graph.add_edge("inject_skills", "agent")
    graph.add_conditional_edges(
        "agent",
        should_continue,
    )
    graph.add_edge("tools", "agent")
    
    return graph.compile()

workflow = create_workflow()
