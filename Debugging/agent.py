from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.tools import tool
from langchain_core.messages import BaseMessage
from langchain_core.prompts import BasePromptTemplate
from langchain_core.callbacks.manager import CallbackManagerForChainRun
from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
import os
from dotenv import load_dotenv
load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGCHAIN_TRACING_API_KEY")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"]="https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"]="pr-ample-length-96"

llm = init_chat_model("groq:gemma2-9b-it", temperature=0) 

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def make_tool_graph():
    ## Graph with tool call

    @tool
    def add_numbers(a: int, b: int) -> int:
        """Add two numbers together."""
        return a + b
    
    tools = [add_numbers]
    tool_node = ToolNode(tools)

    llm_with_tools = llm.bind_tools(tools)

    def call_llm_model(state:State):
        return {"messages": llm_with_tools.invoke(state["messages"])}
    
    graph = StateGraph(State)
    graph.add_node("tool_calling_llm",call_llm_model)
    graph.add_node("tools",tool_node)

    graph.add_edge(START, "tool_calling_llm")
    graph.add_conditional_edges("tool_calling_llm", 
                                # If the model decided to call a tool, go to the tool node
                                # If the model decided to not call a tool, go back to the model node
                                tools_condition
                                )
    graph.add_edge("tools", END)

    builder = graph.compile()  # Compile the graph to check for errors

    return builder

tool_agent = make_tool_graph()
