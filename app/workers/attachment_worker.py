"""Worker entry point for deployments that process attachments asynchronously."""

import asyncio


async def run() -> None:
    while True:
        await asyncio.sleep(30)


if __name__ == "__main__":
    asyncio.run(run())
