import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tickets import get_ticket_status


def test_allowed_ticket() -> None:
    assert get_ticket_status("T-1042") == {
        "ticket_id": "T-1042", "status": "in_progress",
    }


def test_unavailable_ticket_is_not_enumerable() -> None:
    assert get_ticket_status("T-2042") == get_ticket_status("T-9999")
    assert get_ticket_status("T-2042") == {"error": "ticket_unavailable"}


def test_invalid_ticket() -> None:
    assert get_ticket_status("../T-1042") == {"error": "invalid_ticket_id"}


def test_stdio_contract() -> None:
    async def check() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(Path(__file__).with_name("server.py"))],
        )
        async with (
            stdio_client(params) as (reader, writer),
            ClientSession(reader, writer) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            assert len(tools.tools) == 1
            schema = tools.tools[0].inputSchema
            assert schema["required"] == ["ticket_id"]
            assert set(schema["properties"]) == {"ticket_id"}
            allowed = await session.call_tool(
                "get_ticket_status", {"ticket_id": "T-1042"},
            )
            assert not allowed.isError
            assert allowed.structuredContent == {
                "ticket_id": "T-1042", "status": "in_progress",
            }
            blocked = await session.call_tool(
                "get_ticket_status", {"ticket_id": "T-2042"},
            )
            missing = await session.call_tool(
                "get_ticket_status", {"ticket_id": "T-9999"},
            )
            assert blocked.structuredContent == missing.structuredContent
    asyncio.run(check())
