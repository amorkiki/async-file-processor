import asyncio
from typing import List, Callable, Optional
from sqlalchemy.orm import Session
from .worker import Worker, TaskRunner
from .queue_manager import QueueManager


class WorkerPool:
    """
    Worker 池管理器

    职责：
    - 启动/停止多个 Worker
    - 管理 Worker 生命周期
    """

    def __init__(
        self,
        queue_manager: QueueManager,
        session_factory: Callable[[], Session],
        task_runner: TaskRunner,
        worker_count: int = 3,
        model_class: Optional[type] = None,
        adapter_factory: Optional[Callable] = None,
    ):
        self.queue_manager = queue_manager
        self.session_factory = session_factory
        self.task_runner = task_runner
        self.worker_count = worker_count
        self.model_class = model_class
        self.adapter_factory = adapter_factory
        self._workers: List[asyncio.Task] = []
        self._worker_instances: List[Worker] = []

    async def start(self) -> None:
        """启动所有 Worker"""
        for i in range(self.worker_count):
            worker = Worker(
                queue_manager=self.queue_manager,
                session_factory=self.session_factory,
                task_runner=self.task_runner,
                worker_id=i,
                model_class=self.model_class,
                adapter_factory=self.adapter_factory,
            )
            self._worker_instances.append(worker)
            self._workers.append(asyncio.create_task(worker.run()))
        print(f"✅ {self.worker_count} 个 Worker 已启动")

    async def stop(self) -> None:
        """停止所有 Worker，带超时和强制取消"""
        # 1. 发送停止信号
        for worker in self._worker_instances:
            worker.stop()

        if not self._workers:
            print("🛑 没有 Worker 在运行")
            return

        # 2. 等待所有 Worker 自然退出，最多等待 5 秒
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._workers, return_exceptions=True), timeout=5.0
            )
            print("✅ 所有 Worker 已正常退出")
        except asyncio.TimeoutError:
            print("⚠️ Worker 停止超时，强制取消...")
            # 3. 强制取消所有 Worker 任务
            for task in self._workers:
                task.cancel()
            # 等待取消完成（忽略异常）
            await asyncio.gather(*self._workers, return_exceptions=True)
            print("✅ 所有 Worker 已强制取消")

        # 4. 清空列表
        self._workers.clear()
        self._worker_instances.clear()
