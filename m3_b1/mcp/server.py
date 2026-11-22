from mcp.server.fastmcp import FastMCP
from tickets import get_ticket_status

server = FastMCP("demo-ticket-status")
server.tool()(get_ticket_status)

if __name__ == "__main__":
    server.run(transport="stdio")
