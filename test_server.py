# asyncio lets us run the async calls that the FastMCP client uses
import asyncio

from fastmcp import Client

# Import the server we built in server.py
from server import mcp


async def main():
    # Connect to the server in memory, no Claude Desktop needed
    async with Client(mcp) as client:
        # Call get_brain_state once for each simulated state
        for state in ["relaxed", "focused"]:
            result = await client.call_tool("get_brain_state", {"state": state})
            print(state, result)


asyncio.run(main())