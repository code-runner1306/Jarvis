from typing import TypedDict, Annotated, List
import operator
from langchain_core.messages import BaseMessage

class JarvisState(TypedDict):
    # The list of messages in the conversation
    messages: Annotated[List[BaseMessage], operator.add]
    
    # Current intent or task being processed
    current_intent: str
    
    # Next step in the graph
    next: str
