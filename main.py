import os
import json
from starlette.responses import JSONResponse
from server import mcp

# Disable DNS rebinding protection to allow connections from Render domains
mcp.settings.transport_security.enable_dns_rebinding_protection = False

# Retrieve the Streamable HTTP Starlette app from FastMCP
base_app = mcp.streamable_http_app()

class TokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # We only authenticate HTTP requests
        if scope["type"] == "http":
            path = scope.get("path", "")
            
            # Allow health check endpoint to be accessed publicly
            if path == "/health":
                await self._send_json(send, {"status": "ok"}, status_code=200)
                return

            # Secure the /mcp endpoint and any sub-routes
            if path.startswith("/mcp"):
                headers = dict(scope.get("headers", []))
                auth_header = headers.get(b"authorization", b"").decode("utf-8")
                
                expected_token = os.environ.get("MCP_API_TOKEN")

                # If the security token is not set, block requests and alert logs
                if not expected_token:
                    await self._send_json(
                        send,
                        {"detail": "Server configuration error: MCP_API_TOKEN is not set."},
                        status_code=500
                    )
                    return

                if not auth_header.startswith("Bearer "):
                    await self._send_json(
                        send,
                        {"detail": "Unauthorized: Missing or invalid Authorization header format."},
                        status_code=401
                    )
                    return

                token = auth_header.split(" ", 1)[1]
                if token != expected_token:
                    await self._send_json(
                        send,
                        {"detail": "Unauthorized: Invalid API token."},
                        status_code=401
                    )
                    return

        # Forward authenticated or non-mcp requests to the Starlette app
        await self.app(scope, receive, send)

    async def _send_json(self, send, data, status_code):
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
            ]
        })
        body = json.dumps(data).encode("utf-8")
        await send({
            "type": "http.response.body",
            "body": body,
            "more_body": False
        })

# Wrap the Starlette application with our Token Auth Middleware
app = TokenAuthMiddleware(base_app)
