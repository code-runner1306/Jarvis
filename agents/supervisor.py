from typing import Literal
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent
from utils.config import settings
from langchain_core.messages import HumanMessage, SystemMessage

from core.tools import all_jarvis_tools
from agents.learning import learning_tools
from agents.productivity import productivity_tools
from agents.automation import automation_tools

class SupervisorAgent:
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.LLM_MODEL,
            base_url=settings.OLLAMA_BASE_URL
        )
        
        # Combine all tools
        self.tools = all_jarvis_tools + learning_tools + productivity_tools + automation_tools
        
        # Persistence
        self.memory = SqliteSaver.from_conn_string("jarvis_memory.db")
        
        # System prompt
        system_prompt = (
            "You are JARVIS, a highly advanced AI assistant running locally. "
            "You have access to a variety of tools to help the user with productivity, learning, and automation. "
            "If you need to perform an action, use the appropriate tool. "
            "For automation tasks that simulate clicks or type, ALWAYS use the 'ask_human_permission' tool first unless explicitly told otherwise. "
            "Keep your verbal responses concise and natural for voice interaction."
        )
        
        # Create the ReAct agent graph
        self.graph = create_react_agent(
            self.llm, 
            tools=self.tools, 
            checkpointer=self.memory,
            state_modifier=system_prompt
        )

    async def process_query(self, query: str, thread_id: str = "default"):
        config = {"configurable": {"thread_id": thread_id}}
        input_state = {"messages": [HumanMessage(content=query)]}
        
        # The stream method allows us to see intermediate tool calls if needed, 
        # but ainvoke returns the final state.
        result = await self.graph.ainvoke(input_state, config)
        return result["messages"][-1].content

if __name__ == "__main__":
    import asyncio
    agent = SupervisorAgent()
    async def test():
        resp = await agent.process_query("What tools do you have access to?")
        print(f"Response: {resp}")
    # asyncio.run(test())
