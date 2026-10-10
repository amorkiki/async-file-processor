import asyncio
import traceback
from typing import Callable, Awaitable, Generic, TypeVar, Optional
from sqlalchemy.orm import Session
from ..schemas.base_task import BaseTask, BaseTaskStatus
from .queue_manager import QueueManager
from .state_machine import create_task_state_machine, TransitionError

T = TypeVar("T", bound=BaseTask)

# ---------- 业务执行器类型 ----------
# 引擎层不关心具体业务，只接收一个异步函数
# 该函数接收任务对象和数据库 Session，执行业务逻辑并更新任务状态
TaskRunner = Callable[[T, Session], Awaitable[None]]


class Worker(Generic[T]):
    def __init__(
        self,
        queue_manager: QueueManager,
        session_factory: Callable[[], Session],
        task_runner: TaskRunner[T],
        worker_id: int = 0,
        model_class: Optional[type] = None,
        adapter_factory: Optional[Callable[[T, Session], T]] = None,
    ):
        self.queue_manager = queue_manager
        self.session_factory = session_factory
        self.task_runner = task_runner
        self.worker_id = worker_id
        self.model_class = model_class
        self.adapter_factory = adapter_factory
        self._running = False

    async def run(self) -> None:
        """启动 Worker 循环"""
        self._running = True
        print(f"🟢 Worker {self.worker_id} 已启动")

        while self._running:
            # ---------- 1. 从队列获取任务（带超时，每秒醒来一次） ----------
            try:
                memory_task = await asyncio.wait_for(
                    self.queue_manager.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                # Worker 任务被外部取消
                print(f"⏹️ Worker {self.worker_id}: 任务被取消")
                break

            # 成功取出任务，并确保无论任务处理成功与否，都调用 task_done()
            try:
                # ---------- 2. 创建独立的数据库会话 ----------
                db = self.session_factory()
                try:
                    # ---------- 3. 从数据库获取最新任务 ----------
                    db_task = self._get_task_from_db(db, memory_task.id)
                    if db_task is None:
                        print(
                            f"⏭️ Worker {self.worker_id}: 任务 {memory_task.id} 不存在，跳过"
                        )
                        continue

                    # ---------- 4. 状态机：尝试转为 running ----------
                    sm = create_task_state_machine()
                    sm.reset(db_task.status.value)
                    try:
                        sm.transition_to(BaseTaskStatus.running.value)
                    except TransitionError as e:
                        current_status = db_task.status.value
                        print(
                            f"⚠️ Worker {self.worker_id}: 任务 {memory_task.id} "
                            f"无法从 {current_status} 转为 running（原因: {e}），跳过执行"
                        )
                        if current_status == BaseTaskStatus.pending.value:
                            db_task.update_status(
                                BaseTaskStatus.failed, f"启动时状态异常: {e}"
                            )
                            db.commit()
                        else:
                            # 任务已处于终态，无需修改，直接跳过
                            pass
                        continue
                    # 转换成功，更新数据库状态为 running
                    db_task.update_status(BaseTaskStatus.running, "任务开始执行")
                    db.commit()
                    print(
                        f"▶️ Worker {self.worker_id}: 任务 {memory_task.id} 已锁定为 running"
                    )

                    # ---------- 5. 执行业务逻辑 ----------
                    try:
                        await self.task_runner(db_task, db)
                    except asyncio.CancelledError:
                        # 可能在执行过程中被取消
                        print(f"⏹️ Worker {self.worker_id}: 执行中被取消")
                        sm.reset(db_task.status.value)
                        try:
                            sm.transition_to(BaseTaskStatus.cancelled.value)
                            db_task.update_status(
                                BaseTaskStatus.cancelled, "Worker 被取消"
                            )
                            db.commit()
                        except TransitionError:
                            # 如果任务已经处于终态，则无需处理
                            pass
                        raise  # 重新抛出，让外层捕获并退出循环
                    except Exception as e:
                        # 业务异常 → failed
                        print(
                            f"❌ Worker {self.worker_id}: 任务 {memory_task.id} 执行异常: {e}"
                        )
                        # 把当前正在处理的异常的完整堆栈跟踪（traceback）打印出来
                        traceback.print_exc()
                        db.rollback()
                        sm.reset(db_task.status.value)
                        try:
                            sm.transition_to(BaseTaskStatus.failed.value)
                            db_task.update_status(
                                BaseTaskStatus.failed, f"执行失败: {e}"
                            )
                            db.commit()
                        except TransitionError:
                            pass
                    else:
                        # ---------- 6. 业务执行成功，尝试转为 done ----------
                        sm.reset(db_task.status.value)
                        try:
                            sm.transition_to(BaseTaskStatus.done.value)
                            db_task.update_status(BaseTaskStatus.done, "任务完成")
                            db.commit()
                            print(
                                f"✅ Worker {self.worker_id}: 任务 {memory_task.id} 已完成"
                            )
                        except TransitionError:
                            pass

                finally:
                    db.close()
            finally:
                self.queue_manager.task_done()

        print(f"🟥 Worker {self.worker_id} 已退出")

    def _get_task_from_db(self, db: Session, task_id: str) -> Optional[T]:
        if self.model_class is None:
            raise RuntimeError("Worker 未注入 model_class")
        db_task = db.get(self.model_class, task_id)
        if db_task is None:
            return None
        if self.adapter_factory:
            return self.adapter_factory(db_task, db)
        return db_task

    def stop(self) -> None:
        self._running = False
