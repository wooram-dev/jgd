import aiohttp
import asyncio
import json

async def debug_api():
    url = "https://overfast-api.tekrop.fr/players/TeKrop-2217/summary"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            print(json.dumps(data, indent=2))

if __name__ == "__main__":
    asyncio.run(debug_api())
