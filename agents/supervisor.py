from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import create_react_agent
from utils.config import settings
from langchain_core.messages import HumanMessage, SystemMessage

from core.tools import all_jarvis_tools
from agents.learning import learning_tools
from agents.productivity import productivity_tools
from agents.automation import automation_tools

class SupervisorAgent:
    def __init__(self):
        if settings.LLM_BACKEND.lower() == "nvidia":
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            self.llm = ChatNVIDIA(
                model=settings.NVIDIA_MODEL,
                api_key=settings.NVIDIA_API_KEY
            )
        else:
            from langchain_ollama import ChatOllama
            self.llm = ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL
            )
        
        # Combine all tools
        self.tools = all_jarvis_tools + learning_tools + productivity_tools + automation_tools
        
        # System prompt
        self.system_prompt = (
            "You are JARVIS, a highly advanced AI assistant running locally. "
            "You have access to a variety of tools to help the user with productivity, learning, and automation. "
            "If you need to perform an action, use the appropriate tool. "
            "For automation tasks that simulate clicks or type, ALWAYS use the 'ask_human_permission' tool first unless explicitly told otherwise. "
            "Keep your verbal responses concise and natural for voice interaction."
        )
        
        # We initialize the graph lazily because AsyncSqliteSaver needs an async context
        self.graph = None
        self.memory = None

    async def _ensure_graph(self):
        """Lazily initialize the graph and memory in an async context."""
        if self.graph is None:
            # AsyncSqliteSaver.from_conn_string returns an async context manager
            self.memory_manager = AsyncSqliteSaver.from_conn_string("jarvis_memory.db")
            self.memory = await self.memory_manager.__aenter__()
            
            self.graph = create_react_agent(
                self.llm, 
                tools=self.tools, 
                checkpointer=self.memory,
                prompt=self.system_prompt
            )

    async def heal_memory(self, thread_id: str = "default"):
        """Detects and fixes dangling tool calls in the chat history."""
        await self._ensure_graph()
        config = {"configurable": {"thread_id": thread_id}}
        try:
            state = await self.graph.aget_state(config)
            if state and state.values and "messages" in state.values:
                messages = state.values["messages"]
                if messages:
                    last_msg = messages[-1]
                    tool_calls = getattr(last_msg, "tool_calls", [])
                    if tool_calls:
                        from langchain_core.messages import ToolMessage
                        print(f"[BRAIN] Healing history for thread '{thread_id}'...")
                        tool_results = [
                            ToolMessage(
                                tool_call_id=tc["id"], 
                                content="Error: Session ended before tool could complete."
                            ) for tc in tool_calls
                        ]
                        await self.graph.aupdate_state(config, {"messages": tool_results})
                        return True
        except Exception as e:
            print(f"[BRAIN WARNING] Memory healing skipped: {e}")
        return False

    async def process_query(self, query: str, thread_id: str = "default", narration_callback=None):
        await self._ensure_graph()
        config = {"configurable": {"thread_id": thread_id}}
        
        # 1. Fix dangling tool calls if they exist
        await self.heal_memory(thread_id)

        # 2. Process the actual query
        input_state = {"messages": [HumanMessage(content=query)]}
        
        try:
            # Try astream_events to get real-time tool narration
            async for event in self.graph.astream_events(input_state, config, version="v2"):
                kind = event["event"]
                if kind == "on_tool_start" and narration_callback:
                    tool_name = event["name"]
                    # Generate a simple narration
                    msg = f"Alright, let me use the {tool_name.replace('_', ' ')} tool to figure this out."
                    await narration_callback(msg)
            
            # Get final state after stream completes
            state = await self.graph.aget_state(config)
            return state.values["messages"][-1].content
            
        except Exception as e:
            print(f"[BRAIN ERROR] Processing failed: {e}")
            # Fallback to a simple invoke if streaming fails
            result = await self.graph.ainvoke(input_state, config)
            return result["messages"][-1].content

if __name__ == "__main__":
    import asyncio
    agent = SupervisorAgent()
    async def test():
        resp = await agent.process_query("What tools do you have access to?")
        print(f"Response: {resp}")
    # asyncio.run(test())
