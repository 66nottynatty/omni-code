from .state import AgentState
import logging

logger = logging.getLogger(__name__)


def analyze_repo(state: AgentState) -> AgentState:
    """Analyze a repository and update state with results."""
    current_repo = state.get("current_repo", "unknown")
    logger.info(f"Analyzing repository: {current_repo}")
    return {
        "analysis_result": f"Analysis complete for {current_repo}",
        "messages": [{"role": "assistant", "content": f"Reviewed repository: {current_repo}"}]
    }


def fetch_repo_info(state: AgentState) -> AgentState:
    """Fetch information about a repository."""
    current_repo = state.get("current_repo", "unknown")
    logger.info(f"Fetching info for repository: {current_repo}")
    return {
        "messages": [{"role": "assistant", "content": f"Fetched info for {current_repo}"}]
    }


def should_continue(state: AgentState) -> str:
    """Determine if workflow should continue."""
    return "analyze"
