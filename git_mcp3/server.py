"""
GitHub MCP Server using FastMCP 2.0
Provides tools to list and delete GitHub repositories
"""

from mcp.server.fastmcp import FastMCP
from github import Github
from typing import Optional
import os
from dotenv import load_dotenv
load_dotenv()  

# Initialize FastMCP server
mcp = FastMCP("GitHub Manager")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable not set")

github_client = Github(GITHUB_TOKEN)

@mcp.tool()
def list_repositories(
    username: Optional[str] = None,
    org: Optional[str] = None,
    limit: int = 10
) -> str:
    """
    List GitHub repositories for a user or organization.
    
    Args:
        username: GitHub username (if not provided, uses authenticated user)
        org: Organization name (takes precedence over username)
        limit: Maximum number of repositories to return (default: 10)
    
    Returns:
        A formatted string with repository information
    """
    try:
        repos = []
        
        if org:
            # List organization repositories
            organization = github_client.get_organization(org)
            repos = list(organization.get_repos()[:limit])
        elif username:
            # List user repositories
            user = github_client.get_user(username)
            repos = list(user.get_repos()[:limit])
        else:
            # List authenticated user's repositories
            user = github_client.get_user()
            repos = list(user.get_repos()[:limit])
        
        if not repos:
            return "No repositories found."
        
        # Format repository information
        result = []
        result.append(f"Found {len(repos)} repositories:\n")
        
        for repo in repos:
            result.append(f"\n📦 {repo.full_name}")
            result.append(f"   Description: {repo.description or 'No description'}")
            result.append(f"   URL: {repo.html_url}")
            result.append(f"   Stars: ⭐ {repo.stargazers_count}")
            result.append(f"   Forks: 🍴 {repo.forks_count}")
            result.append(f"   Private: {'🔒 Yes' if repo.private else '🌍 No'}")
            result.append(f"   Language: {repo.language or 'N/A'}")
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Error listing repositories: {str(e)}"


@mcp.tool()
def delete_repository(repo_name: str, confirm: bool = False) -> str:
    """
    Delete a GitHub repository. Requires confirmation for safety.
    
    Args:
        repo_name: Full repository name (format: 'owner/repo' or just 'repo' for authenticated user)
        confirm: Must be set to True to actually delete the repository
    
    Returns:
        Success or error message
    """
    try:
        if not confirm:
            return (
                f"⚠️  SAFETY CHECK: Deletion not confirmed!\n\n"
                f"To delete repository '{repo_name}', you must set confirm=True.\n"
                f"This action is IRREVERSIBLE and will permanently delete:\n"
                f"  - All code and commits\n"
                f"  - All issues and pull requests\n"
                f"  - All releases and assets\n"
                f"  - All wiki pages\n\n"
                f"Please confirm you want to proceed."
            )
        
        # Get the repository
        if "/" in repo_name:
            # Full repo name provided
            repo = github_client.get_repo(repo_name)
        else:
            # Just repo name, use authenticated user
            user = github_client.get_user()
            repo = github_client.get_repo(f"{user.login}/{repo_name}")
        
        # Store info before deletion
        full_name = repo.full_name
        
        # Delete the repository
        repo.delete()
        
        return f"✅ Successfully deleted repository: {full_name}"
        
    except Exception as e:
        return f"❌ Error deleting repository: {str(e)}"


# Run the server
if __name__ == "__main__":
    mcp.run()