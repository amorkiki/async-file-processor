import asyncio
from typing import TypeVar, Generic
from ..schemas.base_task import BaseTask

T = TypeVar("T", bound=BaseTask)


class QueueManager(Generic[T]):
    def __init__(self):
        self._queue: asyncio.Queue[T] = asyncio.Queue()

    async def put(self, task: T) -> None:
        await self._queue.put(task)

    async def get(self) -> T:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

    def qsize(self) -> int:
        return self._queue.qsize()

    def empty(self) -> bool:
        return self._queue.empty()
