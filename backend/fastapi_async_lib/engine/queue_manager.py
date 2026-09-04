import asyncio
from typing import TypeVar, Generic, Optional
from ..schemas.base_task import BaseTask

T = TypeVar("T", bound=BaseTask)


class QueueManager(Generic[T]):
    """
    通用任务队列管理器

    职责：
    - 管理任务队列（入队/出队）
    - 支持未来切换 Redis 实现（只需替换内部的 _queue 实现）
    """

    def __init__(self):
        self._queue: asyncio.Queue[T] = asyncio.Queue()

    async def put(self, task: T) -> None:
        """将任务放入队列"""
        await self._queue.put(task)

    async def get(self) -> T:
        """从队列取出任务（阻塞直到有任务）"""
        return await self._queue.get()

    def task_done(self) -> None:
        """标记当前任务已完成"""
        self._queue.task_done()

    def qsize(self) -> int:
        """获取队列大小"""
        return self._queue.qsize()

    def empty(self) -> bool:
        """判断队列是否为空"""
        return self._queue.empty()
