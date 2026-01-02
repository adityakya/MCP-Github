"""
LangGraph Chatbot with MCP Server Integration
Uses Streamlit for UI and LangGraph for agent orchestration
"""

import streamlit as st
import asyncio
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_core.tools import tool
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os
import json

# Page configuration
st.set_page_config(
    page_title="GitHub Assistant",
    page_icon="🐙",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "default_thread"
if "mcp_session" not in st.session_state:
    st.session_state.mcp_session = None


# MCP Client Manager
class MCPClientManager:
    def __init__(self):
        self.session = None
        self.read = None
        self.write = None
        self.client_context = None
        self.session_context = None
        
    async def connect(self):
        """Connect to MCP server"""
        if self.session is not None:
            return self.session
            
        server_params = StdioServerParameters(
            command="python",
            args=["server.py"],
            env=None
        )
        
        self.client_context = stdio_client(server_params)
        self.read, self.write = await self.client_context.__aenter__()
        
        self.session_context = ClientSession(self.read, self.write)
        self.session = await self.session_context.__aenter__()
        
        await self.session.initialize()
        return self.session
    
    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.session_context:
            await self.session_context.__aexit__(None, None, None)
        if self.client_context:
            await self.client_context.__aexit__(None, None, None)
        self.session = None


# Initialize MCP client manager
@st.cache_resource
def get_mcp_manager():
    return MCPClientManager()

mcp_manager = get_mcp_manager()


# Define LangChain tools that wrap MCP tools
@tool
async def list_github_repositories(username: str = "adityakya", org: str = None, limit: int = 10) -> str:
    """
    List GitHub repositories for a user or organization.
    
    Args:
        username: GitHub username (optional)
        org: Organization name (optional)
        limit: Maximum number of repositories to return
    """
    try:
        session = await mcp_manager.connect()
        
        arguments = {"limit": limit}
        if username:
            arguments["username"] = username
        if org:
            arguments["org"] = org
            
        result = await session.call_tool("list_repositories", arguments=arguments)
        return result.content[0].text
    except Exception as e:
        return f"Error listing repositories: {str(e)}"


@tool
async def delete_github_repository(repo_name: str, confirm: bool = False) -> str:
    """
    Delete a GitHub repository. Requires confirmation for safety.
    
    Args:
        repo_name: Full repository name (format: 'owner/repo' or just 'repo')
        confirm: Must be True to actually delete the repository
    """
    try:
        session = await mcp_manager.connect()
        
        result = await session.call_tool(
            "delete_repository",
            arguments={"repo_name": repo_name, "confirm": confirm}
        )
        return result.content[0].text
    except Exception as e:
        return f"Error deleting repository: {str(e)}"


# Define the agent state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]


# Initialize LLM with tools
def get_llm():
    # Gemini api
    from dotenv import load_dotenv
    load_dotenv()
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

    # # Huggingface api
    # from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
    # api_key = os.getenv("HUGGINGFACE_API_KEY")
    # model = HuggingFaceEndpoint(
    #     repo_id="openai/gpt-oss-20b",
    #     task="conversational",          # important for Groq models
    #     huggingfacehub_api_token=api_key
    # )
    # llm = ChatHuggingFace(llm=model)
    
    tools = [list_github_repositories, delete_github_repository]
    return llm.bind_tools(tools), tools

# Create the agent graph
def create_graph():
    llm, tools = get_llm()
    
    # Define the function that determines whether to continue or end
    def should_continue(state: AgentState):
        messages = state["messages"]
        last_message = messages[-1]
        
        # If there are no tool calls, then we finish
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return "end"
        else:
            return "continue"
    
    # Define the function that calls the model
    async def call_model(state: AgentState):
        messages = state["messages"]
        response = await llm.ainvoke(messages)
        return {"messages": [response]}
    
    # Define the tool node
    tool_node = ToolNode(tools)
    
    # Define the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    
    # Set the entry point
    workflow.set_entry_point("agent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "continue": "tools",
            "end": END,
        },
    )
    
    # Add edge from tools back to agent
    workflow.add_edge("tools", "agent")
    
    # Compile with memory
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)
    
    return graph


# Streamlit UI
st.title("🐙 GitHub Assistant")
st.caption("Chat with your GitHub repositories using natural language")

# Sidebar with information
with st.sidebar:
    st.header("About")
    st.write("""
    This chatbot can help you:
    - List your GitHub repositories
    - Search repositories by user or organization
    - Delete repositories (with confirmation)
    
    Just ask in natural language!
    """)
    
    st.header("Example Prompts")
    st.code("""
• List my repositories
• Show me repos for user 'torvalds'
• What are my top 5 repos?
• Delete the repo 'test-repo'
    """)
    
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.thread_id = f"thread_{len(st.session_state.messages)}"
        st.rerun()
    
    st.divider()
    st.caption("Powered by LangGraph + MCP + Claude")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me about your GitHub repositories..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Run the agent
        async def run_agent():
            graph = create_graph()
            
            # Prepare input
            inputs = {
                "messages": [HumanMessage(content=prompt)]
            }
            
            config = {
                "configurable": {"thread_id": st.session_state.thread_id}
            }
            
            # Stream the response
            response_text = ""
            tool_calls_made = []
            
            async for event in graph.astream(inputs, config, stream_mode="values"):
                if "messages" in event:
                    last_message = event["messages"][-1]
                    
                    # Handle AI messages
                    if isinstance(last_message, AIMessage):
                        if hasattr(last_message, "content") and last_message.content:
                            response_text = last_message.content
                        
                        # Track tool calls
                        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                            for tool_call in last_message.tool_calls:
                                tool_calls_made.append({
                                    "name": tool_call["name"],
                                    "args": tool_call["args"]
                                })
                    
                    # Handle tool messages
                    elif isinstance(last_message, ToolMessage):
                        # Tool result will be processed in next iteration
                        pass
            
            # Show tool calls if any
            if tool_calls_made:
                with st.expander("🔧 Tool Calls Made", expanded=False):
                    for i, tool_call in enumerate(tool_calls_made, 1):
                        st.write(f"**Call {i}:** `{tool_call['name']}`")
                        st.json(tool_call['args'])
            
            return response_text
        
        # Run the async function
        try:
            full_response = asyncio.run(run_agent())
            message_placeholder.markdown(full_response)
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            message_placeholder.markdown(error_msg)
            full_response = error_msg
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Footer
st.divider()
st.caption("💡 Tip: Try asking about repositories, or request specific GitHub operations!")