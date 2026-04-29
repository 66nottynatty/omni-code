from langgraph.graph import StateGraph, START, END
from .state import AgentState
from .nodes import analyze_repo, fetch_repo_info, should_continue


def create_workflow():
    """Create and compile the LangGraph workflow."""
    graph = StateGraph(AgentState)
    
    graph.add_node("analyze", analyze_repo)
    graph.add_node("fetch", fetch_repo_info)
    
    graph.add_edge(START, "fetch")
    graph.add_conditional_edges(
        "fetch",
        should_continue,
        {
            "analyze": "analyze",
            END: END
        }
    )
    graph.add_edge("analyze", END)
    
    return graph.compile()


workflow = create_workflow()
