import asyncio
from server import list_tools

async def main():
    tools = await list_tools()
    print([t.name for t in tools])

asyncio.run(main())
