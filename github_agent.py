# backend/github_agent.py
import os
import sys
import json
import asyncio
import logging
import shlex
from typing import Dict, Any, Optional, List
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp import types

# Configure file logging
logging.basicConfig(
    filename='github_agent.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

# Path to MCP server
SERVER_PATH = os.path.join(os.path.dirname(__file__), "github_server.py")

def parse_command(query: str) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Parse a command string into tool name and arguments.
    
    Args:
        query: Raw command string
        
    Returns:
        Tuple of (tool_name, arguments dict) or (None, None) if invalid
    """
    try:
        parts = shlex.split(query)
    except Exception:
        logging.warning("Failed to parse query with shlex, falling back to split")
        parts = query.split()
        
    if not parts:
        return None, None
        
    cmd = parts[0].lower()
    
    # if cmd in ("list_repos", "list_repositories"):
    if cmd == "list_repositories":
        if len(parts) < 2:
            return None, None
        return "list_repositories", {"username": parts[1].strip()}
        
    elif cmd == "get_repo_details":
        if len(parts) < 2:
            return None, None
        return "get_repo_details", {"repo": parts[1]}
            
    return None, None

async def create_github_session() -> StdioServerParameters:
    """Start the MCP GitHub server and initialize the session using stdio_client.
    
    Returns:
        StdioServerParameters: Configuration for stdio_client
    
    Raises:
        OSError: If server path is invalid
        Exception: For other initialization errors
    """
    if not os.path.exists(SERVER_PATH):
        raise OSError(f"Server not found at: {SERVER_PATH}")
        
    params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_PATH],
        env=os.environ.copy(),
    )
    
    return params

async def run_github_agent(query: str) -> Dict[str, Any]:
    """Send a query to the MCP GitHub server and return the result.

    Args:
        query: The command string to process (e.g., "list_repositories octocat")

    Returns:
        Dict with either {"repositories": [...]} or {"error": "error message"}
    """
    logging.basicConfig(
        filename='github_agent.log',
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        force=True
    )
    # Validate input
    if not query or not query.strip():
        return {"error": "Empty query"}

    logging.info("Starting github agent with query: %r", query)
    
    ## Parse command
    tool_name, arguments = parse_command(query)
    if not tool_name or not arguments:
        return {"error": f"Invalid command format: {query}"}
    
    logging.info("Parsed command - tool: %r, arguments: %r", tool_name, arguments)
    
    try:
        # Create and validate session
        params = await create_github_session()
        
        # Connect to server and process request
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize session
                try:
                    await session.initialize()
                    logging.info("🔄 Session initialized successfully")
                
                                    # Prepare and send request
                    call_request = types.CallToolRequest(
                        params={
                            "name": tool_name,
                            "arguments": arguments
                        }
                    )
                    request = types.ClientRequest(call_request)
                    logging.info(f"📤 Sending request - Tool: {tool_name}, Arguments structure: {json.dumps(arguments, indent=2)}")
                    logging.debug("📦 Full request object: %r", request)
                    result = await session.send_request(request, types.ClientResult)
                    logging.info("Received response from server: %r", result)
                    
                    # Process response
                    if not hasattr(result, "root"):
                        return {"error": "Invalid response format: missing root"}

                    # Handle EmptyResult type
                    root = result.root
                    if not hasattr(root, "content"):
                        if hasattr(root, "error"):
                            return {"error": root.error}
                        return {"error": "Invalid response format: missing content"}

                    content = root.content
                    if not content:
                        return {"error": "No results received from server"}
                    
                    # Extract results
                    results = []
                    for item in content:
                        text = None
                        if isinstance(item, dict) and "text" in item:
                            text = item["text"]
                        elif hasattr(item, "text"):
                            text = item.text
                        else:
                            text = str(item)
                        
                        if text and isinstance(text, str):
                            if "❌" in text:  # Error indicator
                                return {"error": text.replace("❌ ", "")}
                            results.append(text)
                    
                    if not results:
                        return {"error": "No repositories found"}
                        
                    logging.info("Successfully found %d repositories", len(results))
                    return {"repositories": results}
                    
                except Exception as e:
                    logging.exception("Error during tool execution")
                    return {"error": f"Tool execution failed: {str(e)}"}
                    
    except Exception as e:
        logging.exception("Failed to communicate with server")
        return {"error": f"Server communication failed: {str(e)}"}



# if __name__ == "__main__":
#     # Example usage
#     query = "list_repositories adityakya"
#     try:
#         result = asyncio.run(run_github_agent(query))
#         print(json.dumps(result, indent=2))
#     except KeyboardInterrupt:
#         print("\nOperation cancelled by user")
#     except Exception as e:
#         print(f"Error: {e}", file=sys.stderr)
