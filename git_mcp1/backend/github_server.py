# backend/github_server.py
import os
import httpx
import json
import asyncio
import logging
from typing import Dict, Any, List
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

# Configure logging to write to a file instead of stdout
logging.basicConfig(
    filename='github_server.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

server = Server("github-mcp")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")



@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Expose tools provided by this server."""
    # Advertise the supported tools and their expected input schema
    return [
        types.Tool(
            name="list_repositories",
            description="List all public repositories for a given GitHub username",
            inputSchema={
                "type": "object",
                "properties": {"username": {"type": "string"}},
                "required": ["username"],
            },
        ),
        types.Tool(
            name="get_repo_details",
            description="Get details for a repository (owner/repo)",
            inputSchema={
                "type": "object",
                "properties": {"repo": {"type": "string"}},
                "required": ["repo"],
            },
        ),
    ]

# TOOL 1
@server.call_tool()
async def handle_tool_call(name: str, arguments: dict | None):
    if name == "list_repositories":
        return await list_repositories(name, arguments)
    elif name == "get_repo_details":
        return await get_repo_details(name, arguments)
    else:
        logging.error("Unknown tool called: %s", name)
        return [types.TextContent(type="text", text=f"❌ Unknown tool: {name}")]


async def list_repositories(name: str, arguments: dict | None):
    """List all public repositories for a given GitHub username."""
    # Log detailed argument structure
    logging.info("🔍 list_repositories received arguments: %s", json.dumps(arguments, indent=2))

    # Extract arguments from the correct structure
    if not arguments:
        return [types.TextContent(type="text", text="❌ Missing arguments")]

    # Handle nested arguments structure
    if "arguments" in arguments:
        arguments = arguments["arguments"]
    
    # Log raw request details
    logging.info(f"💡 Tool execution - Name: {name}, Tool: list_repositories, Arguments: {arguments}")

    # Extract username from arguments
    if not arguments or not isinstance(arguments, dict):
        logging.error("Invalid arguments type: %r", type(arguments))
        return [types.TextContent(type="text", text="❌ Invalid arguments: expected dictionary with username")]

    username = arguments.get("username")
    if not username:
        error_msg = "❌ Missing username parameter"
        logging.error("Missing username in arguments: %r", arguments)
        return [types.TextContent(type="text", text=error_msg)]

    # Set up API headers
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
        logging.debug("Using authenticated GitHub API request")

    try:
        # Make GitHub API request
        logging.info("Making GitHub API request for user: %r", username)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/users/{username}/repos",
                headers=headers
            )
            
            # Handle non-200 responses
            if response.status_code != 200:
                error_data = response.json()
                error_message = error_data.get('message', f'GitHub API Error: {response.status_code}')
                logging.error("GitHub API Error: %s", error_message)
                return [types.TextContent(type="text", text=f"❌ {error_message}")]

            # Process successful response
            data = response.json()
            logging.info("GitHub API returned %d repositories for user %r", len(data), username)
            
            if not data:
                msg = "No repositories found. Note: Only public repositories are visible."
                logging.info(msg)
                return [types.TextContent(type="text", text=msg)]
            
            # Format repository information
            repo_results = []
            for repo in data:
                repo_str = (
                    f"{repo['full_name']} "
                    f"({repo.get('visibility', 'public')}) - "
                    f"{repo.get('description') or 'No description'}"
                )
                repo_results.append(repo_str)
                logging.debug("Processing repository: %s", repo['full_name'])
            
            # Return formatted results as a single text block
            formatted_results = "\n\n".join(repo_results)
            return [types.TextContent(type="text", text=formatted_results)]
            

    except httpx.RequestError as e:
        error_msg = f"Failed to connect to GitHub API: {str(e)}"
        logging.error(error_msg)
        return [types.TextContent(type="text", text=f"❌ {error_msg}")]
    except Exception as e:
        error_msg = f"Unexpected error processing GitHub response: {str(e)}"
        logging.exception(error_msg)
        return [types.TextContent(type="text", text=f"❌ {error_msg}")]


# TOOL 2
def _parse_repo_string(repo_str: str):
    """Return (owner, repo) from a string like 'owner/repo'"""
    if not repo_str:
        return None, None
    parts = repo_str.split("/")
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, repo_str

# @server.call_tool()
async def get_repo_details(name: str, arguments: dict | None):
    # Log detailed argument structure
    logging.info("🔍 get_repo_details received arguments: %s", json.dumps(arguments, indent=2))

    # Handle nested arguments structure
    if arguments and "arguments" in arguments:
        arguments = arguments["arguments"]

    if not arguments:
        return [types.TextContent(type="text", text="❌ Missing 'repo' argument (owner/repo).")]
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid 'repo' format. Use 'owner/repo'.")]

    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://api.github.com/repos/{owner}/{repo_name}", headers=headers)
        if response.status_code != 200:
            try:
                error_data = response.json()
                error_message = error_data.get("message", str(response.status_code))
            except Exception:
                error_message = str(response.status_code)
            return [types.TextContent(type="text", text=f"❌ {error_message}")]
        data = response.json()
        # Pick useful fields
        details = [
            f"full_name: {data.get('full_name')}",
            f"description: {data.get('description')}",
            f"private: {data.get('private')}",
            f"html_url: {data.get('html_url')}",
            f"stars: {data.get('stargazers_count')}",
            f"forks: {data.get('forks_count')}",
            f"open_issues: {data.get('open_issues_count')}",
        ]
        return [types.TextContent(type="text", text=line) for line in details]



async def main():
    """Run MCP server using stdio transport."""
    # Log available tools at startup
    tools = await list_tools()
    logging.info("🔧 Registered tools: %s", [tool.name for tool in tools])
    
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
