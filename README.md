# GitHub MCP Server (Custom)

A custom Model Context Protocol (MCP) server giving an AI agent full
CRUD access to GitHub: repositories, issues, pull requests, branches,
comments, reviews, and merges. Built with the official Python `mcp` SDK
(`FastMCP`) and GitHub's REST API via `httpx`.

23 tools total — see `server.py` for the full list. Highlights:

| Area | Tools |
|---|---|
| Repos | `list_repos`, `get_repo` |
| Issues | `list_issues`, `get_issue`, `create_issue`, `update_issue`, `close_issue`, `add_issue_comment`, `list_issue_comments` |
| Branches | `list_branches`, `get_branch`, `create_branch`, `delete_branch` |
| Pull Requests | `list_pull_requests`, `get_pull_request`, `create_pull_request`, `update_pull_request`, `merge_pull_request`, `list_pr_files` |
| Reviews | `list_pr_reviews`, `create_pr_review` |
| Commits | `list_commits`, `get_commit` |

## Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Create a GitHub token**

   Go to <https://github.com/settings/tokens> and create either:
   - a **classic PAT** with the `repo` scope, or
   - a **fine-grained PAT** with `Contents`, `Issues`, `Pull requests`,
     and `Metadata` set to Read & write, scoped to the repos you want
     the agent to touch.

3. **Set the token as an environment variable**

   ```bash
   export GITHUB_TOKEN=ghp_your_token_here
   ```

4. **Run it standalone (optional sanity check)**

   ```bash
   python server.py
   ```

   It will sit and wait for an MCP client to connect over stdio — that's expected, it's not a web server.

## Connecting it to Claude Desktop

Add this to your `claude_desktop_config.json`
(`%APPDATA%\Claude\claude_desktop_config.json` on Windows,
`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "github": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"],
      "env": {
        "GITHUB_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

Restart Claude Desktop and the GitHub tools will show up in the tool picker.

## Connecting it to your own agent pipeline (e.g. the Jira → GitHub → Teams project)

Since this is a standard MCP stdio server, any MCP-compatible client or SDK
can spawn it as a subprocess and talk to it over stdin/stdout — including a
.NET host if you're using the MCP C# SDK, or the Python/TypeScript SDKs if
your orchestrator is polyglot. Point the client at:

```
command: python
args: ["/absolute/path/to/server.py"]
env: { "GITHUB_TOKEN": "<token>" }
```

## Extending it

To add a new tool, just add a new `@mcp.tool()`-decorated function to
`server.py` that calls `_request(method, path, ...)` against the
[GitHub REST API](https://docs.github.com/en/rest). The docstring becomes
the tool's description shown to the model, and type hints become the
input schema — so keep both accurate.

## Notes

- All write operations (`create_*`, `update_*`, `delete_*`, `merge_*`)
  make real changes on GitHub — there's no dry-run mode. Consider testing
  against a scratch repo first, especially `merge_pull_request` and
  `delete_branch`.
- Rate limits follow GitHub's standard REST API limits (5,000 requests/hour
  for authenticated requests as of this writing) — the server doesn't do
  its own throttling.
- Errors from GitHub (bad auth, 404s, merge conflicts, etc.) are raised as
  `RuntimeError` with the API's response body included, so the calling
  agent gets a readable message to react to.
