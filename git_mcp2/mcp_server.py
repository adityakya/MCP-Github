import os
import httpx
import json
import asyncio

from typing import Dict, Any, List, Optional
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server
#----------------------------------------------------------------------------#

server = Server("github-mcp")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Expose all GitHub tools provided by this server."""
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
            description="Get detailed information for a repository (owner/repo)",
            inputSchema={
                "type": "object",
                "properties": {"repo": {"type": "string"}},
                "required": ["repo"],
            },
        ),
        types.Tool(
            name="list_issues",
            description="List issues for a repository with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository in format owner/repo"},
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
                    "labels": {"type": "string", "description": "Comma-separated list of labels"},
                    "per_page": {"type": "integer", "default": 30, "maximum": 100}
                },
                "required": ["repo"],
            },
        ),
        types.Tool(
            name="create_issue",
            description="Create a new issue in a repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "labels": {"type": "array", "items": {"type": "string"}},
                    "assignees": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["repo", "title"],
            },
        ),
        types.Tool(
            name="update_issue",
            description="Update an existing issue",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string"},
                    "issue_number": {"type": "integer"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "state": {"type": "string", "enum": ["open", "closed"]},
                    "labels": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["repo", "issue_number"],
            },
        ),
        types.Tool(
            name="list_pull_requests",
            description="List pull requests for a repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string"},
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
                    "per_page": {"type": "integer", "default": 30, "maximum": 100}
                },
                "required": ["repo"],
            },
        ),
        types.Tool(
            name="create_pull_request",
            description="Create a new pull request",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string"},
                    "title": {"type": "string"},
                    "head": {"type": "string", "description": "Branch containing changes"},
                    "base": {"type": "string", "description": "Branch to merge into"},
                    "body": {"type": "string"},
                    "draft": {"type": "boolean", "default": False}
                },
                "required": ["repo", "title", "head", "base"],
            },
        ),
        types.Tool(
            name="get_file_contents",
            description="Get contents of a file from a repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string"},
                    "path": {"type": "string", "description": "Path to file in repository"},
                    "branch": {"type": "string", "description": "Branch name (default: main)"}
                },
                "required": ["repo", "path"],
            },
        ),
        types.Tool(
            name="create_or_update_file",
            description="Create or update a file in a repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string"},
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "message": {"type": "string", "description": "Commit message"},
                    "branch": {"type": "string"},
                    "sha": {"type": "string", "description": "SHA of file to update (for updates only)"}
                },
                "required": ["repo", "path", "content", "message", "branch"],
            },
        ),
        types.Tool(
            name="list_branches",
            description="List all branches in a repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string"},
                    "per_page": {"type": "integer", "default": 30, "maximum": 100}
                },
                "required": ["repo"],
            },
        ),
        types.Tool(
            name="create_branch",
            description="Create a new branch in a repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string"},
                    "branch": {"type": "string", "description": "Name of new branch"},
                    "from_branch": {"type": "string", "description": "Source branch (default: main)"}
                },
                "required": ["repo", "branch"],
            },
        ),
        types.Tool(
            name="list_commits",
            description="List commits in a repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string"},
                    "branch": {"type": "string", "description": "Branch name"},
                    "per_page": {"type": "integer", "default": 30, "maximum": 100}
                },
                "required": ["repo"],
            },
        ),
        types.Tool(
            name="search_repositories",
            description="Search for repositories on GitHub",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "sort": {"type": "string", "enum": ["stars", "forks", "updated"]},
                    "order": {"type": "string", "enum": ["asc", "desc"], "default": "desc"},
                    "per_page": {"type": "integer", "default": 30, "maximum": 100}
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="search_code",
            description="Search for code in repositories",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "per_page": {"type": "integer", "default": 30, "maximum": 100}
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="create_repository",
            description="Create a new repository for authenticated user",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "private": {"type": "boolean", "default": False},
                    "auto_init": {"type": "boolean", "default": True}
                },
                "required": ["name"],
            },
        ),
        types.Tool(
            name="fork_repository",
            description="Fork a repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string"}
                },
                "required": ["repo"],
            },
        ),
        types.Tool(
            name="list_releases",
            description="List releases for a repository",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo": {"type": "string"},
                    "per_page": {"type": "integer", "default": 30, "maximum": 100}
                },
                "required": ["repo"],
            },
        ),
        types.Tool(
            name="get_user_info",
            description="Get information about a GitHub user",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string"}
                },
                "required": ["username"],
            },
        ),
    ]


def _parse_repo_string(repo_str: str) -> tuple[Optional[str], Optional[str]]:
    """Return (owner, repo) from a string like 'owner/repo'"""
    if not repo_str:
        return None, None
    parts = repo_str.split("/")
    if len(parts) == 2:
        return parts[0], parts[1]
    return None, repo_str


def _get_headers() -> Dict[str, str]:
    """Get standard headers for GitHub API requests"""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def _extract_arguments(arguments: dict | None) -> dict:
    """Extract arguments from potentially nested structure"""
    if not arguments:
        return {}
    if "arguments" in arguments:
        return arguments["arguments"]
    return arguments


@server.call_tool()
async def handle_tool_call(name: str, arguments: dict | None):
    """Route tool calls to appropriate handlers"""
    args = _extract_arguments(arguments)
    
    handlers = {
        "list_repositories": list_repositories,
        "get_repo_details": get_repo_details,
        "list_issues": list_issues,
        "create_issue": create_issue,
        "update_issue": update_issue,
        "list_pull_requests": list_pull_requests,
        "create_pull_request": create_pull_request,
        "get_file_contents": get_file_contents,
        "create_or_update_file": create_or_update_file,
        "list_branches": list_branches,
        "create_branch": create_branch,
        "list_commits": list_commits,
        "search_repositories": search_repositories,
        "search_code": search_code,
        "create_repository": create_repository,
        "fork_repository": fork_repository,
        "list_releases": list_releases,
        "get_user_info": get_user_info,
    }
    
    handler = handlers.get(name)
    if handler:
        return await handler(name, args)
    
   
    return [types.TextContent(type="text", text=f"❌ Unknown tool: {name}")]


# ============================================================================
# REPOSITORY TOOLS
# ============================================================================

async def list_repositories(name: str, arguments: dict):
    """List all public repositories for a given GitHub username."""
    username = arguments.get("username")
    if not username:
        return [types.TextContent(type="text", text="❌ Missing username parameter")]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/users/{username}/repos",
                headers=_get_headers(),
                params={"per_page": 100}
            )
            
            if response.status_code != 200:
                error = response.json().get('message', f'Error: {response.status_code}')
                return [types.TextContent(type="text", text=f"❌ {error}")]

            data = response.json()
            if not data:
                return [types.TextContent(type="text", text="No repositories found")]
            
            repo_results = []
            for repo in data:
                repo_str = (
                    f"{repo['full_name']} ({repo.get('visibility', 'public')}) - "
                    f"⭐ {repo.get('stargazers_count', 0)} - "
                    f"{repo.get('description') or 'No description'}"
                )
                repo_results.append(repo_str)
            
            return [types.TextContent(type="text", text="\n\n".join(repo_results))]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


async def get_repo_details(name: str, arguments: dict):
    """Get detailed information for a repository"""
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid repo format. Use 'owner/repo'")]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}",
                headers=_get_headers()
            )
            
            if response.status_code != 200:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            data = response.json()
            details = f"""Repository: {data.get('full_name')}
Description: {data.get('description') or 'No description'}
Private: {data.get('private')}
URL: {data.get('html_url')}
Stars: ⭐ {data.get('stargazers_count')}
Forks: 🔱 {data.get('forks_count')}
Open Issues: {data.get('open_issues_count')}
Language: {data.get('language') or 'N/A'}
Created: {data.get('created_at')}
Updated: {data.get('updated_at')}
Default Branch: {data.get('default_branch')}"""
            
            return [types.TextContent(type="text", text=details)]

    except Exception as e:
      
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


async def search_repositories(name: str, arguments: dict):
    """Search for repositories on GitHub"""
    query = arguments.get("query")
    if not query:
        return [types.TextContent(type="text", text="❌ Missing query parameter")]
    
    params = {
        "q": query,
        "per_page": arguments.get("per_page", 30)
    }
    if arguments.get("sort"):
        params["sort"] = arguments["sort"]
    if arguments.get("order"):
        params["order"] = arguments["order"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/search/repositories",
                headers=_get_headers(),
                params=params
            )
            
            if response.status_code != 200:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            data = response.json()
            results = []
            for repo in data.get("items", []):
                results.append(
                    f"{repo['full_name']} - ⭐ {repo['stargazers_count']} - "
                    f"{repo.get('description') or 'No description'}"
                )
            
            total = data.get("total_count", 0)
            header = f"Found {total} repositories (showing {len(results)}):\n\n"
            return [types.TextContent(type="text", text=header + "\n".join(results))]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


async def create_repository(name: str, arguments: dict):
    """Create a new repository"""
    if not GITHUB_TOKEN:
        return [types.TextContent(type="text", text="❌ GitHub token required for this operation")]
    
    repo_name = arguments.get("name")
    if not repo_name:
        return [types.TextContent(type="text", text="❌ Missing repository name")]

    data = {
        "name": repo_name,
        "description": arguments.get("description", ""),
        "private": arguments.get("private", False),
        "auto_init": arguments.get("auto_init", True)
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.github.com/user/repos",
                headers=_get_headers(),
                json=data
            )
            
            if response.status_code not in [200, 201]:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            repo = response.json()
            return [types.TextContent(
                type="text",
                text=f"✅ Repository created: {repo['html_url']}"
            )]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


async def fork_repository(name: str, arguments: dict):
    """Fork a repository"""
    if not GITHUB_TOKEN:
        return [types.TextContent(type="text", text="❌ GitHub token required for this operation")]
    
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid repo format. Use 'owner/repo'")]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/repos/{owner}/{repo_name}/forks",
                headers=_get_headers()
            )
            
            if response.status_code not in [200, 202]:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            fork = response.json()
            return [types.TextContent(
                type="text",
                text=f"✅ Repository forked: {fork['html_url']}"
            )]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


# ============================================================================
# ISSUE TOOLS
# ============================================================================

async def list_issues(name: str, arguments: dict):
    """List issues for a repository"""
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid repo format. Use 'owner/repo'")]

    params = {
        "state": arguments.get("state", "open"),
        "per_page": arguments.get("per_page", 30)
    }
    if arguments.get("labels"):
        params["labels"] = arguments["labels"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/issues",
                headers=_get_headers(),
                params=params
            )
            
            if response.status_code != 200:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            issues = response.json()
            if not issues:
                return [types.TextContent(type="text", text="No issues found")]
            
            results = []
            for issue in issues:
                if "pull_request" not in issue:  # Skip PRs
                    labels = ", ".join([l["name"] for l in issue.get("labels", [])])
                    results.append(
                        f"#{issue['number']} - {issue['title']}\n"
                        f"  State: {issue['state']} | Labels: {labels or 'None'}\n"
                        f"  URL: {issue['html_url']}"
                    )
            
            return [types.TextContent(type="text", text="\n\n".join(results))]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


async def create_issue(name: str, arguments: dict):
    """Create a new issue"""
    if not GITHUB_TOKEN:
        return [types.TextContent(type="text", text="❌ GitHub token required for this operation")]
    
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid repo format. Use 'owner/repo'")]
    
    title = arguments.get("title")
    if not title:
        return [types.TextContent(type="text", text="❌ Missing title parameter")]

    data = {
        "title": title,
        "body": arguments.get("body", ""),
    }
    if arguments.get("labels"):
        data["labels"] = arguments["labels"]
    if arguments.get("assignees"):
        data["assignees"] = arguments["assignees"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/repos/{owner}/{repo_name}/issues",
                headers=_get_headers(),
                json=data
            )
            
            if response.status_code not in [200, 201]:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            issue = response.json()
            return [types.TextContent(
                type="text",
                text=f"✅ Issue created: #{issue['number']} - {issue['html_url']}"
            )]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


async def update_issue(name: str, arguments: dict):
    """Update an existing issue"""
    if not GITHUB_TOKEN:
        return [types.TextContent(type="text", text="❌ GitHub token required for this operation")]
    
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    issue_number = arguments.get("issue_number")
    
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid repo format. Use 'owner/repo'")]
    if not issue_number:
        return [types.TextContent(type="text", text="❌ Missing issue_number parameter")]

    data = {}
    if arguments.get("title"):
        data["title"] = arguments["title"]
    if arguments.get("body"):
        data["body"] = arguments["body"]
    if arguments.get("state"):
        data["state"] = arguments["state"]
    if arguments.get("labels"):
        data["labels"] = arguments["labels"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://api.github.com/repos/{owner}/{repo_name}/issues/{issue_number}",
                headers=_get_headers(),
                json=data
            )
            
            if response.status_code != 200:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            issue = response.json()
            return [types.TextContent(
                type="text",
                text=f"✅ Issue updated: #{issue['number']} - {issue['html_url']}"
            )]

    except Exception as e:
      
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


# ============================================================================
# PULL REQUEST TOOLS
# ============================================================================

async def list_pull_requests(name: str, arguments: dict):
    """List pull requests for a repository"""
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid repo format. Use 'owner/repo'")]

    params = {
        "state": arguments.get("state", "open"),
        "per_page": arguments.get("per_page", 30)
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/pulls",
                headers=_get_headers(),
                params=params
            )
            
            if response.status_code != 200:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            prs = response.json()
            if not prs:
                return [types.TextContent(type="text", text="No pull requests found")]
            
            results = []
            for pr in prs:
                results.append(
                    f"#{pr['number']} - {pr['title']}\n"
                    f"  {pr['head']['ref']} → {pr['base']['ref']}\n"
                    f"  State: {pr['state']} | Draft: {pr.get('draft', False)}\n"
                    f"  URL: {pr['html_url']}"
                )
            
            return [types.TextContent(type="text", text="\n\n".join(results))]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


async def create_pull_request(name: str, arguments: dict):
    """Create a new pull request"""
    if not GITHUB_TOKEN:
        return [types.TextContent(type="text", text="❌ GitHub token required for this operation")]
    
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid repo format. Use 'owner/repo'")]

    required = ["title", "head", "base"]
    for field in required:
        if not arguments.get(field):
            return [types.TextContent(type="text", text=f"❌ Missing {field} parameter")]

    data = {
        "title": arguments["title"],
        "head": arguments["head"],
        "base": arguments["base"],
        "body": arguments.get("body", ""),
        "draft": arguments.get("draft", False)
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/repos/{owner}/{repo_name}/pulls",
                headers=_get_headers(),
                json=data
            )
            
            if response.status_code not in [200, 201]:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            pr = response.json()
            return [types.TextContent(
                type="text",
                text=f"✅ Pull request created: #{pr['number']} - {pr['html_url']}"
            )]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


# ============================================================================
# FILE & CONTENT TOOLS
# ============================================================================

async def get_file_contents(name: str, arguments: dict):
    """Get contents of a file from a repository"""
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    path = arguments.get("path")
    
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid repo format. Use 'owner/repo'")]
    if not path:
        return [types.TextContent(type="text", text="❌ Missing path parameter")]

    params = {}
    if arguments.get("branch"):
        params["ref"] = arguments["branch"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/contents/{path}",
                headers=_get_headers(),
                params=params
            )
            
            if response.status_code != 200:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            data = response.json()
            
            # Decode content
            import base64
            content = base64.b64decode(data["content"]).decode("utf-8")
            
            result = f"File: {path}\nSize: {data['size']} bytes\nSHA: {data['sha']}\n\n{content}"
            return [types.TextContent(type="text", text=result)]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


async def create_or_update_file(name: str, arguments: dict):
    """Create or update a file in a repository"""
    if not GITHUB_TOKEN:
        return [types.TextContent(type="text", text="❌ GitHub token required for this operation")]
    
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    path = arguments.get("path")
    content = arguments.get("content")
    message = arguments.get("message")
    branch = arguments.get("branch")
    
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid repo format. Use 'owner/repo'")]
    if not all([path, content, message, branch]):
        return [types.TextContent(type="text", text="❌ Missing required parameters")]

    import base64
    encoded_content = base64.b64encode(content.encode()).decode()
    
    data = {
        "message": message,
        "content": encoded_content,
        "branch": branch
    }
    if arguments.get("sha"):
        data["sha"] = arguments["sha"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"https://api.github.com/repos/{owner}/{repo_name}/contents/{path}",
                headers=_get_headers(),
                json=data
            )
            
            if response.status_code not in [200, 201]:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            result = response.json()
            return [types.TextContent(
                type="text",
                text=f"✅ File {'updated' if arguments.get('sha') else 'created'}: {result['content']['html_url']}"
            )]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


# ============================================================================
# BRANCH TOOLS
# ============================================================================

async def list_branches(name: str, arguments: dict):
    """List all branches in a repository"""
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid repo format. Use 'owner/repo'")]

    params = {"per_page": arguments.get("per_page", 30)}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/branches",
                headers=_get_headers(),
                params=params
            )
            
            if response.status_code != 200:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            branches = response.json()
            if not branches:
                return [types.TextContent(type="text", text="No branches found")]
            
            results = []
            for branch in branches:
                protected = "🔒" if branch.get("protected") else ""
                results.append(f"{protected} {branch['name']} (SHA: {branch['commit']['sha'][:7]})")
            
            return [types.TextContent(type="text", text="\n".join(results))]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


async def create_branch(name: str, arguments: dict):
    """Create a new branch in a repository"""
    if not GITHUB_TOKEN:
        return [types.TextContent(type="text", text="❌ GitHub token required for this operation")]
    
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    branch = arguments.get("branch")
    
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid repo format. Use 'owner/repo'")]
    if not branch:
        return [types.TextContent(type="text", text="❌ Missing branch parameter")]

    try:
        async with httpx.AsyncClient() as client:
            # Get SHA of from_branch (default: main)
            from_branch = arguments.get("from_branch", "main")
            ref_response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/git/ref/heads/{from_branch}",
                headers=_get_headers()
            )
            
            if ref_response.status_code != 200:
                error = ref_response.json().get("message", str(ref_response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            sha = ref_response.json()["object"]["sha"]
            
            # Create new branch
            data = {
                "ref": f"refs/heads/{branch}",
                "sha": sha
            }
            
            response = await client.post(
                f"https://api.github.com/repos/{owner}/{repo_name}/git/refs",
                headers=_get_headers(),
                json=data
            )
            
            if response.status_code not in [200, 201]:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            return [types.TextContent(
                type="text",
                text=f"✅ Branch '{branch}' created from '{from_branch}'"
            )]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


# ============================================================================
# COMMIT TOOLS
# ============================================================================

async def list_commits(name: str, arguments: dict):
    """List commits in a repository"""
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid repo format. Use 'owner/repo'")]

    params = {"per_page": arguments.get("per_page", 30)}
    if arguments.get("branch"):
        params["sha"] = arguments["branch"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/commits",
                headers=_get_headers(),
                params=params
            )
            
            if response.status_code != 200:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            commits = response.json()
            if not commits:
                return [types.TextContent(type="text", text="No commits found")]
            
            results = []
            for commit in commits:
                sha = commit['sha'][:7]
                message = commit['commit']['message'].split('\n')[0]  # First line only
                author = commit['commit']['author']['name']
                date = commit['commit']['author']['date']
                results.append(f"{sha} - {message}\n  by {author} on {date}")
            
            return [types.TextContent(type="text", text="\n\n".join(results))]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


# ============================================================================
# SEARCH TOOLS
# ============================================================================

async def search_code(name: str, arguments: dict):
    """Search for code in repositories"""
    query = arguments.get("query")
    if not query:
        return [types.TextContent(type="text", text="❌ Missing query parameter")]

    params = {
        "q": query,
        "per_page": arguments.get("per_page", 30)
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/search/code",
                headers=_get_headers(),
                params=params
            )
            
            if response.status_code != 200:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                return [types.TextContent(type="text", text="No code results found")]
            
            results = []
            for item in items:
                results.append(
                    f"{item['repository']['full_name']}/{item['path']}\n"
                    f"  URL: {item['html_url']}"
                )
            
            total = data.get("total_count", 0)
            header = f"Found {total} code results (showing {len(results)}):\n\n"
            return [types.TextContent(type="text", text=header + "\n\n".join(results))]

    except Exception as e:
      
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


# ============================================================================
# RELEASE TOOLS
# ============================================================================

async def list_releases(name: str, arguments: dict):
    """List releases for a repository"""
    repo = arguments.get("repo")
    owner, repo_name = _parse_repo_string(repo)
    
    if not owner or not repo_name:
        return [types.TextContent(type="text", text="❌ Invalid repo format. Use 'owner/repo'")]

    params = {"per_page": arguments.get("per_page", 30)}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/releases",
                headers=_get_headers(),
                params=params
            )
            
            if response.status_code != 200:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            releases = response.json()
            if not releases:
                return [types.TextContent(type="text", text="No releases found")]
            
            results = []
            for release in releases:
                prerelease = "🚧 " if release.get("prerelease") else ""
                draft = "📝 " if release.get("draft") else ""
                results.append(
                    f"{prerelease}{draft}{release['tag_name']} - {release['name']}\n"
                    f"  Published: {release.get('published_at', 'N/A')}\n"
                    f"  URL: {release['html_url']}"
                )
            
            return [types.TextContent(type="text", text="\n\n".join(results))]

    except Exception as e:
       
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


# ============================================================================
# USER TOOLS
# ============================================================================

async def get_user_info(name: str, arguments: dict):
    """Get information about a GitHub user"""
    username = arguments.get("username")
    if not username:
        return [types.TextContent(type="text", text="❌ Missing username parameter")]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/users/{username}",
                headers=_get_headers()
            )
            
            if response.status_code != 200:
                error = response.json().get("message", str(response.status_code))
                return [types.TextContent(type="text", text=f"❌ {error}")]
            
            user = response.json()
            info = f"""Username: {user['login']}
Name: {user.get('name') or 'N/A'}
Bio: {user.get('bio') or 'N/A'}
Company: {user.get('company') or 'N/A'}
Location: {user.get('location') or 'N/A'}
Email: {user.get('email') or 'N/A'}
Blog: {user.get('blog') or 'N/A'}
Public Repos: {user['public_repos']}
Followers: {user['followers']}
Following: {user['following']}
Created: {user['created_at']}
Profile: {user['html_url']}"""
            
            return [types.TextContent(type="text", text=info)]

    except Exception as e:
      
        return [types.TextContent(type="text", text=f"❌ {str(e)}")]


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run MCP server using stdio transport."""
    tools = await list_tools()
  
    
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())