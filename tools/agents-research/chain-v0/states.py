from typing import TypedDict, Annotated, List, Union
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    """The state of the agent."""
    messages: Annotated[List[BaseMessage], operator.add]
