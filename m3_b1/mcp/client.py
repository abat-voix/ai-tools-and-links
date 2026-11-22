import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).with_name("server.py"))],
    )
    async with (
        stdio_client(params) as (reader, writer),
        ClientSession(reader, writer) as session,
    ):
        await session.initialize()
        result = await session.call_tool(
            "get_ticket_status",
            {"ticket_id": "T-1042"},
        )
        print(json.dumps(result.structuredContent, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
