import os
import sys
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# Add the parent directory to sys.path to allow imports if running as script
# Adjust this depending on how you run the script. 
# Since this is tools/agents-research/chain-v0, adding root to path might be needed or just relative imports if run as module.
# For now, we'll assume we run from the root or handle imports carefully.
# But since we are inside tools/agents-research/chain-v0, we can import from local modules directly.

try:
    from tools import ALL_TOOLS
    from states import AgentState
except ImportError:
    # If running from root, these imports might fail if not treated as a package.
    # We will assume this script is run as `python tools/agents-research/chain-v0/main.py` 
    # and sys.path hack might be needed if tools.py is in the same dir.
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from tools import ALL_TOOLS
    from states import AgentState

# Load .env file
try:
    from dotenv import load_dotenv
    # Load from project root
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ".env")
    load_dotenv(dotenv_path)
except ImportError:
    print("python-dotenv not installed, skipping .env loading")

# 1. Setup Model
# Ensure OPENAI_API_KEY is set in environment
if "OPENAI_API_KEY" not in os.environ:
    print("WARNING: OPENAI_API_KEY not found in environment variables.")

model = ChatOpenAI(model=os.environ.get("OPENAI_MODEL", "gpt-4o"))
tools = ALL_TOOLS
model_with_tools = model.bind_tools(tools)

# 2. Define Nodes

SYSTEM_PROMPT = """You are a helpful Text-to-SQL assistant. 
Your goal is to help users find information in the database using the available Discovery tools.
Always start by checking 'search_datasources' if you don't know the datasource.
Use 'search_tables' and 'search_columns' to explore the schema.
You can find example queries with 'search_golden_sql'.
When you have enough info create a SQL query (but you cannot run SQL directly yet).
Generate the SQL query and return it."""

def call_model(state: AgentState):
    messages = state["messages"]
    # Add system prompt if not present? 
    # Actually, we can just prepend it or assume the agent knows. 
    # Better: Prepend system prompt to the messages sent to the model (not necessarily state if we want to save space, but state is fine)
    # For simplicity, we ensure the first message is always system prompt in the flow or we just pass it here.
    
    # Check if system message exists, if not, we could prepend it. 
    # But effectively, we can just pass [SystemMessage, ...messages] to the model.
    # However, to keep it simple with state, we will initialize the graph with a system message.
    
    response = model_with_tools.invoke([SystemMessage(content=SYSTEM_PROMPT)] + messages)
    return {"messages": [response]}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "__end__"

# 3. Define Graph
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
tool_node = ToolNode(tools)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
)

workflow.add_edge("tools", "agent")

# Add memory for persistence
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

# 4. Main Entrypoint
if __name__ == "__main__":
    print("Text-to-SQL Agent Research Tool (Chat Mode)")
    print("-------------------------------------------")
    print("Type 'exit', 'quit', or 'q' to stop.")
    
    # Create a unique thread ID for this session
    import uuid
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["exit", "quit", "q"]:
                print("Bye!")
                break
            
            # We send the new user message. LangGraph with MemorySaver handles the history.
            input_message = HumanMessage(content=user_input)
            
            # Stream events
            # We pass ONLY the new message here, the graph state will be updated via the checkpointer.
            # Note: For StateGraph with Annotated[list, add], passing new keys updates/appends.
            
            for event in app.stream({"messages": [input_message]}, config=config):
                for key, value in event.items():
                    if key == "agent":
                        msg = value["messages"][-1]
                        print(f"\nAgent: {msg.content}")
                        if msg.tool_calls:
                            for tc in msg.tool_calls:
                                print(f"  [Tool Call]: {tc['name']}({tc['args']})")
                    elif key == "tools":
                        # Optional: Print tool outputs for debugging
                        # for msg in value["messages"]:
                        #     print(f"  [Tool Output]: {msg.content[:200]}...")
                        pass
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")
