# core/async_worker.py
import asyncio
from typing import List, Callable, Any

async def run_parallel(tasks: List[Callable]) -> List[Any]:
    """
    Run async functions concurrently.
    Each task is a callable that returns a coroutine.
    """
    coroutines = [task() for task in tasks]
    results = await asyncio.gather(*coroutines, return_exceptions=True)
    # Handle exceptions gracefully
    processed = []
    for r in results:
        if isinstance(r, Exception):
            print(f"Task failed: {r}")
            processed.append(None)
        else:
            processed.append(r)
    return processed

def run_sync_parallel(tasks: List[Callable]) -> List[Any]:
    """Convenience wrapper for synchronous callers."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop.run_until_complete(run_parallel(tasks))