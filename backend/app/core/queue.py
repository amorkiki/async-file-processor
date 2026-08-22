# queue.py
import asyncio
from app.models import Task, TaskStatus
from app.core.db import SessionLocal

# 模块级：queue,因为worker和submit_task必须用同一个queue
queue: asyncio.Queue[Task] = asyncio.Queue()


async def worker():
    from app.services.task_runner import execute  # 局部导入避免循环

    while True:
        task = await queue.get()
        db = SessionLocal()
        try:
            # 1. 获取数据库的最新状态
            db_task = db.get(Task, task.id)

            # 2. 如果 DB 里查不到/状态已经是终态，直接跳过
            if not db_task or db_task.status != TaskStatus.pending:
                print(f"⏭️ 任务 {task.id} 不存在或非pending状态，跳过执行")
                continue

            # 3. ⚠️原子性地将状态改为 running（乐观锁）-- 只有当前状态是 pending 时才更新，防止并发执行
            db_task.status = TaskStatus.running
            db.commit()
            print(f"▶️ 任务 {task.id} 状态已锁定为 running")

            # 4.把内存对象的状态同步到托管对象（避免后续混用）
            db_task.progress = task.progress
            db_task.message = task.message
            db_task.result_path = task.result_path

            # 5. 执行业务逻辑 (传入db，在excute中落库)
            # ⚠️传给 execute 的是 db_task（托管对象），而不是 task
            await execute(db_task, db)

            # 6. 之后所有对 task 的引用都改成 db_task
            final_db_task = db.get(Task, task.id)
            if final_db_task and final_db_task.status == TaskStatus.cancelled:
                print(f"⚠️ 任务 {task.id} 执行期间被取消")
            else:
                # 此时 db_task 已经被 execute 修改过了，直接 commit 即可
                db.commit()
                print(f"✅ 任务 {task.id} 终态 {db_task.status.value} 已落库")

        except asyncio.CancelledError:
            # 捕获外部取消信号（Worker 被关闭时的兜底）
            print(f"⏹️ Worker 被外部关闭，任务 {task.id} 标记为 cancelled")
            err_task = db.get(Task, task.id)
            if err_task and err_task.status not in (TaskStatus.done, TaskStatus.failed):
                err_task.status = TaskStatus.cancelled
                err_task.message = "Worker 关闭时取消"
                db.commit()

        except Exception as e:
            import traceback

            print(f"❌ execute 捕获异常: {e}")
            traceback.print_exc()  # ← 打印完整堆栈
            # 如果 execute 抛出异常，把失败状态落库（除非它已经被取消）
            print(f"❌ 任务 {task.id} 执行异常: {e}")
            db.rollback()  # 回滚未提交的改动

        finally:
            queue.task_done()  # 不会关闭队列。是告诉队列"我从 get() 拿走的那个任务，处理完了"。
            db.close()  # ⚠️关闭后台会话，释放连接
