import asyncio
import json
import aiofiles

from modules import hypixel, asyncreqs


async def main():
    try:
        player = "ragingenby"
        file_path = f".{player}.json"
        # data = await hypixel.get_player(player)
        async with aiofiles.open(file_path, "r") as f:
            data = hypixel.PlayerData(json.loads(await f.read()))
        print(data.discord)

        async with aiofiles.open(file_path, "w") as f:
            await f.write(json.dumps(data.data, indent=2))
    finally:
        await asyncreqs.close()


if __name__ == "__main__":
    asyncio.run(main())
