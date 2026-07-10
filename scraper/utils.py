import asyncio
import random

async def sleep(ms: float):
    await asyncio.sleep(ms / 1000.0)

async def random_sleep(min_ms: float, max_ms: float):
    delay = random.randint(int(min_ms), int(max_ms))
    await sleep(delay)

def clean_str(s: str) -> str:
    if not s:
        return ""
    return " ".join(s.split()).strip()
