"""
test.py — standalone smoke test for the GitHub MCP server.

Spawns server.py as a real MCP subprocess (same way Claude Desktop does),
connects to it as an MCP client, and:
  1. Lists all registered tools (confirms the server starts and speaks MCP).
  2. Calls a read-only tool (confirms your GITHUB_TOKEN actually works).

Usage:
    export GITHUB_TOKEN=ghp_your_token_here
    python test.py                      # uses your own repos
    python test.py octocat Hello-World  # test against a specific owner/repo

Exit code 0 = everything passed. Non-zero = something's broken; read the
printed error.
"""

import asyncio
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")


async def main() -> int:
    if not os.environ.get("GITHUB_TOKEN"):
        print("FAIL: GITHUB_TOKEN is not set in this shell.")
        print("      export GITHUB_TOKEN=ghp_your_token_here   (then re-run)")
        return 1

    owner = sys.argv[1] if len(sys.argv) > 1 else None
    repo = sys.argv[2] if len(sys.argv) > 2 else None

    params = StdioServerParameters(
        command=sys.executable,  # use the same python running this script
        args=[SERVER_SCRIPT],
        env=dict(os.environ),  # pass GITHUB_TOKEN through to the subprocess
    )

    print(f"Launching server: {sys.executable} {SERVER_SCRIPT}")
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("PASS: connected and initialized MCP session.\n")

                # --- Step 1: list tools ---
                tools_result = await session.list_tools()
                tool_names = [t.name for t in tools_result.tools]
                print(f"PASS: server exposes {len(tool_names)} tools:")
                for name in tool_names:
                    print(f"   - {name}")
                print()

                if "list_repos" not in tool_names or "get_repo" not in tool_names:
                    print("FAIL: expected tools missing — server code may be out of sync with test.py.")
                    return 1

                # --- Step 2: call a real, read-only tool ---
                if owner and repo:
                    print(f"Calling get_repo(owner={owner!r}, repo={repo!r}) ...")
                    result = await session.call_tool("get_repo", {"owner": owner, "repo": repo})
                else:
                    print("Calling list_repos() for the authenticated user ...")
                    result = await session.call_tool("list_repos", {})

                if result.isError:
                    text = result.content[0].text if result.content else "(no error detail)"
                    print(f"FAIL: GitHub API call returned an error:\n{text}")
                    print("\nMost likely cause: invalid/expired GITHUB_TOKEN, or missing scopes.")
                    return 1

                print("PASS: GitHub API call succeeded. Sample of the response:\n")
                text = result.content[0].text if result.content else "(empty response)"
                print(text[:800] + ("..." if len(text) > 800 else ""))

        print("\nAll checks passed — the MCP server and your GitHub token are working.")
        return 0

    except FileNotFoundError:
        print(f"FAIL: could not find or launch server.py at {SERVER_SCRIPT}")
        return 1
    except Exception as exc:  # noqa: BLE001 - this is a diagnostic script
        print(f"FAIL: unexpected error: {exc!r}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))