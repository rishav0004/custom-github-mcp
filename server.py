"""
Custom GitHub MCP Server
=========================

A Model Context Protocol (MCP) server exposing full CRUD access to GitHub:
repos, issues, pull requests, branches, comments, reviews, and merges.

Auth:
    Set the GITHUB_TOKEN environment variable.

Run locally:
    python server.py

For Render:
    uvicorn server:app --host 0.0.0.0 --port $PORT

MCP endpoint:
    /mcp
"""

import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise RuntimeError(
        "GITHUB_TOKEN environment variable is not set. "
        "Set GITHUB_TOKEN in your environment before starting the server."
    )


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("github-mcp")


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def _client() -> httpx.Client:
    return httpx.Client(
        base_url=GITHUB_API,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=30.0,
    )


def _request(method: str, path: str, **kwargs) -> Any:
    """Make a GitHub API request and return parsed JSON."""

    with _client() as client:
        resp = client.request(method, path, **kwargs)

    if resp.status_code >= 400:
        detail = resp.text[:500]
        raise RuntimeError(
            f"GitHub API error {resp.status_code} "
            f"for {method} {path}: {detail}"
        )

    if resp.status_code == 204 or not resp.content:
        return {
            "status": "ok",
            "code": resp.status_code,
        }

    return resp.json()


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

@mcp.tool()
def list_repos(
    owner: str | None = None,
    per_page: int = 30,
) -> Any:
    """List repositories for the authenticated user or owner/org."""
    if owner:
        return _request(
            "GET",
            f"/users/{owner}/repos",
            params={"per_page": per_page},
        )

    return _request(
        "GET",
        "/user/repos",
        params={"per_page": per_page},
    )


@mcp.tool()
def get_repo(owner: str, repo: str) -> Any:
    """Get details about a repository."""
    return _request(
        "GET",
        f"/repos/{owner}/{repo}",
    )


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------

@mcp.tool()
def list_issues(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 30,
) -> Any:
    """List issues in a repo."""
    return _request(
        "GET",
        f"/repos/{owner}/{repo}/issues",
        params={
            "state": state,
            "per_page": per_page,
        },
    )


@mcp.tool()
def get_issue(
    owner: str,
    repo: str,
    issue_number: int,
) -> Any:
    """Get a single issue."""
    return _request(
        "GET",
        f"/repos/{owner}/{repo}/issues/{issue_number}",
    )


@mcp.tool()
def create_issue(
    owner: str,
    repo: str,
    title: str,
    body: str = "",
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
) -> Any:
    """Create a new issue."""

    payload: dict[str, Any] = {
        "title": title,
        "body": body,
    }

    if labels:
        payload["labels"] = labels

    if assignees:
        payload["assignees"] = assignees

    return _request(
        "POST",
        f"/repos/{owner}/{repo}/issues",
        json=payload,
    )


@mcp.tool()
def update_issue(
    owner: str,
    repo: str,
    issue_number: int,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
    labels: list[str] | None = None,
) -> Any:
    """Update an issue."""

    payload: dict[str, Any] = {}

    if title is not None:
        payload["title"] = title

    if body is not None:
        payload["body"] = body

    if state is not None:
        payload["state"] = state

    if labels is not None:
        payload["labels"] = labels

    return _request(
        "PATCH",
        f"/repos/{owner}/{repo}/issues/{issue_number}",
        json=payload,
    )


@mcp.tool()
def close_issue(
    owner: str,
    repo: str,
    issue_number: int,
) -> Any:
    """Close an issue."""

    return _request(
        "PATCH",
        f"/repos/{owner}/{repo}/issues/{issue_number}",
        json={"state": "closed"},
    )


@mcp.tool()
def add_issue_comment(
    owner: str,
    repo: str,
    issue_number: int,
    body: str,
) -> Any:
    """Add a comment to an issue or pull request."""

    return _request(
        "POST",
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
        json={"body": body},
    )


@mcp.tool()
def list_issue_comments(
    owner: str,
    repo: str,
    issue_number: int,
) -> Any:
    """List comments on an issue or pull request."""

    return _request(
        "GET",
        f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
    )


# ---------------------------------------------------------------------------
# Branches
# ---------------------------------------------------------------------------

@mcp.tool()
def list_branches(
    owner: str,
    repo: str,
    per_page: int = 30,
) -> Any:
    """List branches in a repo."""

    return _request(
        "GET",
        f"/repos/{owner}/{repo}/branches",
        params={"per_page": per_page},
    )


@mcp.tool()
def get_branch(
    owner: str,
    repo: str,
    branch: str,
) -> Any:
    """Get details about a branch."""

    return _request(
        "GET",
        f"/repos/{owner}/{repo}/branches/{branch}",
    )


@mcp.tool()
def create_branch(
    owner: str,
    repo: str,
    new_branch: str,
    from_branch: str = "main",
) -> Any:
    """Create a new branch."""

    ref_data = _request(
        "GET",
        f"/repos/{owner}/{repo}/git/ref/heads/{from_branch}",
    )

    sha = ref_data["object"]["sha"]

    return _request(
        "POST",
        f"/repos/{owner}/{repo}/git/refs",
        json={
            "ref": f"refs/heads/{new_branch}",
            "sha": sha,
        },
    )


@mcp.tool()
def delete_branch(
    owner: str,
    repo: str,
    branch: str,
) -> Any:
    """Delete a branch."""

    return _request(
        "DELETE",
        f"/repos/{owner}/{repo}/git/refs/heads/{branch}",
    )


# ---------------------------------------------------------------------------
# Pull Requests
# ---------------------------------------------------------------------------

@mcp.tool()
def list_pull_requests(
    owner: str,
    repo: str,
    state: str = "open",
    per_page: int = 30,
) -> Any:
    """List pull requests."""

    return _request(
        "GET",
        f"/repos/{owner}/{repo}/pulls",
        params={
            "state": state,
            "per_page": per_page,
        },
    )


@mcp.tool()
def get_pull_request(
    owner: str,
    repo: str,
    pr_number: int,
) -> Any:
    """Get a pull request."""

    return _request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pr_number}",
    )


@mcp.tool()
def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    head: str,
    base: str = "main",
    body: str = "",
    draft: bool = False,
) -> Any:
    """Create a pull request."""

    return _request(
        "POST",
        f"/repos/{owner}/{repo}/pulls",
        json={
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "draft": draft,
        },
    )


@mcp.tool()
def update_pull_request(
    owner: str,
    repo: str,
    pr_number: int,
    title: str | None = None,
    body: str | None = None,
    state: str | None = None,
    base: str | None = None,
) -> Any:
    """Update a pull request."""

    payload: dict[str, Any] = {}

    if title is not None:
        payload["title"] = title

    if body is not None:
        payload["body"] = body

    if state is not None:
        payload["state"] = state

    if base is not None:
        payload["base"] = base

    return _request(
        "PATCH",
        f"/repos/{owner}/{repo}/pulls/{pr_number}",
        json=payload,
    )


@mcp.tool()
def merge_pull_request(
    owner: str,
    repo: str,
    pr_number: int,
    commit_title: str | None = None,
    commit_message: str | None = None,
    merge_method: str = "merge",
) -> Any:
    """Merge a pull request."""

    payload: dict[str, Any] = {
        "merge_method": merge_method,
    }

    if commit_title:
        payload["commit_title"] = commit_title

    if commit_message:
        payload["commit_message"] = commit_message

    return _request(
        "PUT",
        f"/repos/{owner}/{repo}/pulls/{pr_number}/merge",
        json=payload,
    )


@mcp.tool()
def list_pr_files(
    owner: str,
    repo: str,
    pr_number: int,
) -> Any:
    """List files changed in a pull request."""

    return _request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
    )


# ---------------------------------------------------------------------------
# Reviews
# ---------------------------------------------------------------------------

@mcp.tool()
def list_pr_reviews(
    owner: str,
    repo: str,
    pr_number: int,
) -> Any:
    """List reviews on a pull request."""

    return _request(
        "GET",
        f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
    )


@mcp.tool()
def create_pr_review(
    owner: str,
    repo: str,
    pr_number: int,
    body: str = "",
    event: str = "COMMENT",
) -> Any:
    """Create a review on a pull request."""

    return _request(
        "POST",
        f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
        json={
            "body": body,
            "event": event,
        },
    )


# ---------------------------------------------------------------------------
# Commits
# ---------------------------------------------------------------------------

@mcp.tool()
def list_commits(
    owner: str,
    repo: str,
    branch: str | None = None,
    per_page: int = 30,
) -> Any:
    """List commits on a repo."""

    params: dict[str, Any] = {
        "per_page": per_page,
    }

    if branch:
        params["sha"] = branch

    return _request(
        "GET",
        f"/repos/{owner}/{repo}/commits",
        params=params,
    )


@mcp.tool()
def get_commit(
    owner: str,
    repo: str,
    sha: str,
) -> Any:
    """Get details about a commit."""

    return _request(
        "GET",
        f"/repos/{owner}/{repo}/commits/{sha}",
    )


# ---------------------------------------------------------------------------
# Render / Streamable HTTP configuration
# ---------------------------------------------------------------------------

security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False
)

app = mcp.streamable_http_app(
    transport_security=security
)


# ---------------------------------------------------------------------------
# Local execution
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()