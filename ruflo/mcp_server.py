"""
Ruflo MCP Server — exposes Ruflo capabilities over the Model Context Protocol.

Tries to use the official `mcp` Python SDK first. If not installed, falls back
to a hand-rolled JSON-RPC 2.0 stdio implementation.
"""
import asyncio
import json
import sys
from typing import Any


# ------------------------------------------------------------------ #
# Shared tool definitions (used by both implementations)
# ------------------------------------------------------------------ #

_TOOLS = [
    {
        "name": "ruflo_run",
        "description": "Run a task through the Ruflo multi-agent system. Automatically routes to the best agent.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task or question to process",
                },
                "mode": {
                    "type": "string",
                    "enum": ["sequential", "parallel", "best_of"],
                    "description": "Execution mode (default: sequential)",
                    "default": "sequential",
                },
                "session_id": {
                    "type": "string",
                    "description": "Optional session ID for memory continuity",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "ruflo_stats",
        "description": "Get aggregate performance statistics for all Ruflo agents.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "ruflo_memory",
        "description": "Retrieve the recent conversation memory for a session.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "The session ID to retrieve memory for",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of messages to return (default: 20)",
                    "default": 20,
                },
            },
            "required": ["session_id"],
        },
    },
]


# ------------------------------------------------------------------ #
# Tool execution (shared)
# ------------------------------------------------------------------ #

async def _execute_tool(tool_name: str, tool_args: dict) -> str:
    from ruflo.core import Ruflo

    if tool_name == "ruflo_run":
        task = tool_args.get("task", "")
        mode = tool_args.get("mode", "sequential")
        session_id = tool_args.get("session_id", None)

        if not task:
            return json.dumps({"error": "task parameter is required"})

        ruflo = Ruflo()
        try:
            result = await ruflo.run(task, session_id=session_id, mode=mode)
            return json.dumps(
                {
                    "output": result.output,
                    "agent_used": result.agent_used,
                    "success": result.success,
                    "score": result.score,
                    "tokens_used": result.tokens_used,
                    "latency_ms": result.latency_ms,
                },
                ensure_ascii=False,
            )
        finally:
            await ruflo.close()

    elif tool_name == "ruflo_stats":
        ruflo = Ruflo()
        try:
            await ruflo._ensure_initialized()
            stats = await ruflo.get_stats()
            return json.dumps({"stats": stats}, ensure_ascii=False)
        finally:
            await ruflo.close()

    elif tool_name == "ruflo_memory":
        session_id = tool_args.get("session_id", "")
        limit = int(tool_args.get("limit", 20))

        if not session_id:
            return json.dumps({"error": "session_id parameter is required"})

        ruflo = Ruflo()
        try:
            await ruflo._ensure_initialized()
            messages = await ruflo.get_memory(session_id, limit=limit)
            return json.dumps({"messages": messages}, ensure_ascii=False)
        finally:
            await ruflo.close()

    else:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ------------------------------------------------------------------ #
# Official MCP SDK implementation
# ------------------------------------------------------------------ #

def _run_with_mcp_sdk():
    import mcp
    import mcp.server.stdio
    from mcp.server import Server
    from mcp.types import Tool, TextContent, CallToolResult

    server = Server("ruflo")

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["inputSchema"],
            )
            for t in _TOOLS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict):
        result_str = await _execute_tool(name, arguments or {})
        return [TextContent(type="text", text=result_str)]

    async def _main():
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(_main())


# ------------------------------------------------------------------ #
# Manual JSON-RPC 2.0 stdio implementation
# ------------------------------------------------------------------ #

def _make_response(id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": id, "result": result}


def _make_error(id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


async def handle_request(request: dict) -> dict | None:
    method = request.get("method", "")
    params = request.get("params", {}) or {}
    req_id = request.get("id")

    # Notifications (no id) — no response needed
    if req_id is None and method.startswith("notifications/"):
        return None

    if method == "initialize":
        return _make_response(
            req_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ruflo", "version": "0.1.0"},
            },
        )

    elif method == "initialized":
        return None  # notification, no response

    elif method == "tools/list":
        return _make_response(req_id, {"tools": _TOOLS})

    elif method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {}) or {}
        try:
            result_str = await _execute_tool(tool_name, tool_args)
            return _make_response(
                req_id,
                {"content": [{"type": "text", "text": result_str}]},
            )
        except Exception as e:
            return _make_error(req_id, -32603, f"Tool execution failed: {str(e)}")

    elif method == "ping":
        return _make_response(req_id, {})

    else:
        return _make_error(req_id, -32601, f"Method not found: {method}")


async def _stdio_server():
    """Hand-rolled JSON-RPC 2.0 stdio server."""
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    loop = asyncio.get_event_loop()

    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    write_transport, _ = await loop.connect_write_pipe(
        asyncio.BaseProtocol, sys.stdout
    )

    def _send(obj: dict):
        data = json.dumps(obj, ensure_ascii=False) + "\n"
        sys.stdout.buffer.write(data.encode("utf-8"))
        sys.stdout.buffer.flush()

    while True:
        try:
            line = await reader.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                _send(_make_error(None, -32700, f"Parse error: {str(e)}"))
                continue

            try:
                response = await handle_request(request)
                if response is not None:
                    _send(response)
            except Exception as e:
                req_id = request.get("id")
                _send(_make_error(req_id, -32603, f"Internal error: {str(e)}"))

        except asyncio.CancelledError:
            break
        except Exception:
            break


def _run_manual_stdio():
    """Run the manual JSON-RPC stdio server using line-buffered stdin/stdout."""
    import sys

    async def _main():
        loop = asyncio.get_event_loop()

        def _send(obj: dict):
            data = json.dumps(obj, ensure_ascii=False) + "\n"
            sys.stdout.buffer.write(data.encode("utf-8"))
            sys.stdout.buffer.flush()

        stdin_reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(stdin_reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            try:
                line_bytes = await stdin_reader.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8").strip()
                if not line:
                    continue

                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    _send(_make_error(None, -32700, f"Parse error: {str(e)}"))
                    continue

                try:
                    response = await handle_request(request)
                    if response is not None:
                        _send(response)
                except Exception as e:
                    req_id = request.get("id")
                    _send(_make_error(req_id, -32603, f"Internal error: {str(e)}"))

            except (asyncio.CancelledError, KeyboardInterrupt):
                break
            except Exception:
                break

    asyncio.run(_main())


# ------------------------------------------------------------------ #
# Entry point
# ------------------------------------------------------------------ #

def main():
    try:
        import mcp  # noqa: F401
        _run_with_mcp_sdk()
    except ImportError:
        _run_manual_stdio()


if __name__ == "__main__":
    main()
