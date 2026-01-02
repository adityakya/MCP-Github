"""
GitHub MCP Client
Connects to the GitHub MCP server and demonstrates tool usage
"""

import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json


async def run_client():
    """Run the MCP client to interact with GitHub server"""
    
    # Server parameters - points to our server.py
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"],
        env=None  # Will inherit environment variables including GITHUB_TOKEN
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            
            print("🚀 Connected to GitHub MCP Server\n")
            
            # List available tools
            tools = await session.list_tools()
            print("📋 Available Tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            print()
            
            # Example 1: List repositories
            print("=" * 60)
            print("Example 1: Listing repositories")
            print("=" * 60)
            
            result = await session.call_tool(
                "list_repositories",
                arguments={"limit": 5}
            )
            print(result.content[0].text)
            print()
            
            # Example 2: List repositories for a specific user
            print("=" * 60)
            print("Example 2: Listing repositories for a specific user")
            print("=" * 60)
            
            # You can change this to any GitHub username
            result = await session.call_tool(
                "list_repositories",
                arguments={
                    "username": "torvalds",  # Example: Linus Torvalds
                    "limit": 3
                }
            )
            print(result.content[0].text)
            print()
            
            # Example 3: Attempt to delete without confirmation (safety check)
            print("=" * 60)
            print("Example 3: Delete repository (without confirmation)")
            print("=" * 60)
            
            result = await session.call_tool(
                "delete_repository",
                arguments={
                    "repo_name": "test-repo",
                    "confirm": False
                }
            )
            print(result.content[0].text)
            print()
            
            # Example 4: Delete with confirmation (commented out for safety)
            print("=" * 60)
            print("Example 4: Delete repository (with confirmation)")
            print("=" * 60)
            print("⚠️  This example is commented out for safety.")
            print("Uncomment the code below to actually delete a repository.\n")
            
            # UNCOMMENT BELOW TO ACTUALLY DELETE A REPOSITORY
            # WARNING: THIS IS PERMANENT!
            # result = await session.call_tool(
            #     "delete_repository",
            #     arguments={
            #         "repo_name": "your-username/test-repo",
            #         "confirm": True
            #     }
            # )
            # print(result.content[0].text)
            
            print("\n✅ Client demonstration complete!")


if __name__ == "__main__":
    asyncio.run(run_client())