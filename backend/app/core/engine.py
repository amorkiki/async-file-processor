import asyncio
import os
from typing import Optional
from sqlalchemy.orm import Session
from app.core.db import SessionLocal
from app.models import Task
from app.plugins.registry import get_runner
from app.adapters.task_adapter import TaskAdapter
from fastapi_async_lib.engine.queue_manager import QueueManager
from fastapi_async_lib.engine.worker_pool import WorkerPool
from fastapi_async_lib.schemas.base_task import BaseTask

# ---------- 全局引擎实例 ----------
_queue_manager: Optional[QueueManager] = None
_worker_pool: Optional[WorkerPool] = None
_worker_task: Optional[asyncio.Task] = None


def get_queue_manager() -> QueueManager:
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = QueueManager[Task]()
    return _queue_manager


def create_worker_pool(worker_count: int = 3) -> WorkerPool:
    queue_manager = get_queue_manager()

    # 数据库 Session 工厂
    def session_factory() -> Session:
        return SessionLocal()

    # 业务执行器适配器（将引擎调用转换为业务调用）
    async def task_runner_adapter(task: BaseTask, db: Session) -> None:
        if hasattr(task, "_task"):
            raw_task = task._task
        else:
            raw_task = task

        runner = get_runner(raw_task.type)
        if not runner:
            raise ValueError(f"未注册的执行器: {raw_task.type}")
        await runner(raw_task, db)

    def adapter_factory(db_task, db):
        return TaskAdapter(db_task, db)

    return WorkerPool(
        queue_manager=queue_manager,
        session_factory=session_factory,
        task_runner=task_runner_adapter,
        worker_count=worker_count,
        model_class=Task,
        adapter_factory=adapter_factory,
    )


async def start_engine(worker_count: Optional[int] = None) -> None:
    global _worker_pool, _worker_task

    if worker_count is None:
        worker_count = int(os.getenv("WORKER_COUNT", "3"))
    print(f"🚀 正在启动引擎...")

    if _worker_pool is not None:
        print("⚠️ 引擎已在运行中")
        return

    _worker_pool = create_worker_pool(worker_count)
    _worker_task = asyncio.create_task(_worker_pool.start())
    await asyncio.sleep(0.1)
    print(f"✅ 引擎已启动（{worker_count} 个 Worker）")


async def stop_engine() -> None:
    global _worker_pool, _worker_task
    print("🛑 正在停止引擎...")
    if _worker_pool is not None:
        await _worker_pool.stop()
        _worker_pool = None
    if _worker_task is not None:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None
    print("🛑 引擎已停止")


def submit_task_to_queue(task: Task) -> None:
    queue_manager = get_queue_manager()
    asyncio.create_task(queue_manager.put(task))
    print(f"📥 任务 {task.id} 已入队")
