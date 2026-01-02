# backend/github_agent.py
import os
import sys
import json
import asyncio
# import logging
import shlex
from typing import Dict, Any, Optional, List
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp import types


# Path to MCP server
SERVER_PATH = os.path.join(os.path.dirname(__file__), "mcp_server.py")
def parse_command(query: str) -> tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Parse a command string into tool name and arguments.
    
    Supported commands:
    - list_repositories <username>
    - get_repo_details <owner/repo>
    - list_issues <owner/repo> [state] [labels]
    - create_issue <owner/repo> <title> [body]
    - update_issue <owner/repo> <issue_number> [title] [body] [state]
    - list_pull_requests <owner/repo> [state]
    - create_pull_request <owner/repo> <title> <head> <base> [body]
    - get_file_contents <owner/repo> <path> [branch]
    - create_or_update_file <owner/repo> <path> <content> <message> <branch> [sha]
    - list_branches <owner/repo>
    - create_branch <owner/repo> <branch> [from_branch]
    - list_commits <owner/repo> [branch]
    - search_repositories <query> [sort] [order]
    - search_code <query>
    - create_repository <name> [description] [private]
    - fork_repository <owner/repo>
    - list_releases <owner/repo>
    - get_user_info <username>
    
    Args:
        query: Raw command string
        
    Returns:
        Tuple of (tool_name, arguments dict) or (None, None) if invalid
    """
    try:
        parts = shlex.split(query)
    except Exception:
       
        parts = query.split()
        
    if not parts:
        return None, None
        
    cmd = parts[0].lower()
    
    # Repository tools
    if cmd == "list_repositories":
        if len(parts) < 2:
            return None, None
        return "list_repositories", {"username": parts[1]}
        
    elif cmd == "get_repo_details":
        if len(parts) < 2:
            return None, None
        return "get_repo_details", {"repo": parts[1]}
    
    elif cmd == "search_repositories":
        if len(parts) < 2:
            return None, None
        args = {"query": parts[1]}
        if len(parts) > 2:
            args["sort"] = parts[2]
        if len(parts) > 3:
            args["order"] = parts[3]
        return "search_repositories", args
    
    elif cmd == "create_repository":
        if len(parts) < 2:
            return None, None
        args = {"name": parts[1]}
        if len(parts) > 2:
            args["description"] = parts[2]
        if len(parts) > 3:
            args["private"] = parts[3].lower() in ["true", "1", "yes"]
        return "create_repository", args
    
    elif cmd == "fork_repository":
        if len(parts) < 2:
            return None, None
        return "fork_repository", {"repo": parts[1]}
    
    # Issue tools
    elif cmd == "list_issues":
        if len(parts) < 2:
            return None, None
        args = {"repo": parts[1]}
        if len(parts) > 2:
            args["state"] = parts[2]
        if len(parts) > 3:
            args["labels"] = parts[3]
        return "list_issues", args
    
    elif cmd == "create_issue":
        if len(parts) < 3:
            return None, None
        args = {
            "repo": parts[1],
            "title": parts[2]
        }
        if len(parts) > 3:
            args["body"] = parts[3]
        return "create_issue", args
    
    elif cmd == "update_issue":
        if len(parts) < 3:
            return None, None
        args = {
            "repo": parts[1],
            "issue_number": int(parts[2])
        }
        if len(parts) > 3:
            args["title"] = parts[3]
        if len(parts) > 4:
            args["body"] = parts[4]
        if len(parts) > 5:
            args["state"] = parts[5]
        return "update_issue", args
    
    # Pull request tools
    elif cmd == "list_pull_requests":
        if len(parts) < 2:
            return None, None
        args = {"repo": parts[1]}
        if len(parts) > 2:
            args["state"] = parts[2]
        return "list_pull_requests", args
    
    elif cmd == "create_pull_request":
        if len(parts) < 5:
            return None, None
        args = {
            "repo": parts[1],
            "title": parts[2],
            "head": parts[3],
            "base": parts[4]
        }
        if len(parts) > 5:
            args["body"] = parts[5]
        return "create_pull_request", args
    
    # File tools
    elif cmd == "get_file_contents":
        if len(parts) < 3:
            return None, None
        args = {
            "repo": parts[1],
            "path": parts[2]
        }
        if len(parts) > 3:
            args["branch"] = parts[3]
        return "get_file_contents", args
    
    elif cmd == "create_or_update_file":
        if len(parts) < 6:
            return None, None
        args = {
            "repo": parts[1],
            "path": parts[2],
            "content": parts[3],
            "message": parts[4],
            "branch": parts[5]
        }
        if len(parts) > 6:
            args["sha"] = parts[6]
        return "create_or_update_file", args
    
    # Branch tools
    elif cmd == "list_branches":
        if len(parts) < 2:
            return None, None
        return "list_branches", {"repo": parts[1]}
    
    elif cmd == "create_branch":
        if len(parts) < 3:
            return None, None
        args = {
            "repo": parts[1],
            "branch": parts[2]
        }
        if len(parts) > 3:
            args["from_branch"] = parts[3]
        return "create_branch", args
    
    # Commit tools
    elif cmd == "list_commits":
        if len(parts) < 2:
            return None, None
        args = {"repo": parts[1]}
        if len(parts) > 2:
            args["branch"] = parts[2]
        return "list_commits", args
    
    # Search tools
    elif cmd == "search_code":
        if len(parts) < 2:
            return None, None
        return "search_code", {"query": parts[1]}
    
    # Release tools
    elif cmd == "list_releases":
        if len(parts) < 2:
            return None, None
        return "list_releases", {"repo": parts[1]}
    
    # User tools
    elif cmd == "get_user_info":
        if len(parts) < 2:
            return None, None
        return "get_user_info", {"username": parts[1]}
            
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
        query: The command string to process

    Returns:
        Dict with either success data or {"error": "error message"}
    """
    # Validate input
    if not query or not query.strip():
        return {"error": "Empty query"}

   
    
    # Parse command
    tool_name, arguments = parse_command(query)
    if not tool_name or not arguments:
        return {
            "error": f"Invalid command format: {query}",
            "help": "Use format: <command> <args>. Example: list_repositories octocat"
        }
    
   
    
    try:
        # Create and validate session
        params = await create_github_session()
        
        # Connect to server and process request
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                try:
                    # Initialize session
                    await session.initialize()
                   
                
                    # Prepare and send request
                    call_request = types.CallToolRequest(
                        params={
                            "name": tool_name,
                            "arguments": arguments
                        }
                    )
                    request = types.ClientRequest(call_request)
                   
                    
                    result = await session.send_request(request, types.ClientResult)
                    
                    
                    # Process response
                    if not hasattr(result, "root"):
                        return {"error": "Invalid response format: missing root"}

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
                        return {"error": "No data returned"}
                    
                    # Return appropriate response based on tool
                  
                    
                    # For single result tools
                    if len(results) == 1:
                        return {"success": True, "data": results[0]}
                    
                    # For list tools
                    return {"success": True, "data": results, "count": len(results)}
                    
                except Exception as e:
                  
                    return {"error": f"Tool execution failed: {str(e)}"}
                    
    except Exception as e:
       
        return {"error": f"Server communication failed: {str(e)}"}


async def list_available_tools() -> List[str]:
    """Get list of all available tools from the server.
    
    Returns:
        List of tool names
    """
    try:
        params = await create_github_session()
        
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                # List tools request
                list_request = types.ListToolsRequest()
                request = types.ClientRequest(list_request)
                result = await session.send_request(request, types.ClientResult)
                
                if hasattr(result, "root") and hasattr(result.root, "tools"):
                    return [tool.name for tool in result.root.tools]
                
                return []
                
    except Exception as e:
       
        return []


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    async def main():
        if len(sys.argv) < 2:
            print("Available commands:")
            print("  list_repositories <username>")
            print("  get_repo_details <owner/repo>")
            print("  list_issues <owner/repo> [state]")
            print("  create_issue <owner/repo> <title> [body]")
            print("  list_pull_requests <owner/repo>")
            print("  get_file_contents <owner/repo> <path>")
            print("  list_branches <owner/repo>")
            print("  list_commits <owner/repo>")
            print("  search_repositories <query>")
            print("  search_code <query>")
            print("  list_releases <owner/repo>")
            print("  get_user_info <username>")
            print("\nOr run 'list_tools' to see all available tools")
            sys.exit(1)
        
        query = " ".join(sys.argv[1:])
        
        if query == "list_tools":
            tools = await list_available_tools()
            print(f"Available tools ({len(tools)}):")
            for tool in tools:
                print(f"  - {tool}")
            return
        
        result = await run_github_agent(query)
        print(json.dumps(result, indent=2))
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)