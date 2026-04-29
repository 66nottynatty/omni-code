from typing import TypedDict, Annotated
from langgraph.graph import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    current_repo: str | None
    analysis_result: str | None
    github_token: str | None
