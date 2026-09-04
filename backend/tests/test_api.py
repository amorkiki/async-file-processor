import uuid
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel, select
from app.main import app
from app.core.db import engine, SessionLocal
from app.core.engine import start_engine, stop_engine
from app.models import Task, TaskStatus


@pytest.fixture(autouse=True)
async def clean_database():
    SQLModel.metadata.create_all(engine)

    # 清空 Task 表
    with SessionLocal() as db:
        tasks = db.execute(select(Task)).scalars().all()
        for task in tasks:
            db.delete(task)
        db.commit()

    # 启动引擎（让 Worker 在测试期间运行）
    await start_engine(worker_count=2)

    yield

    await stop_engine()

    # 测试结束后再次清空
    with SessionLocal() as db:
        tasks = db.execute(select(Task)).scalars().all()
        for task in tasks:
            db.delete(task)
        db.commit()


@pytest.mark.asyncio
async def test_full_task_lifespan():
    """测试：上传 -> 提交 -> Worker 执行 -> 状态变为 done"""
    test_content = b"this is a test file for testing processing"
    # `httpx` 格式，模拟 `multipart/form-data` 文件上传
    test_file = {"file": ("test.txt", test_content, "text/plain")}

    # 创建 HTTP 客户端
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        upload_resp = await client.post("/tasks/upload", files=test_file)
        assert upload_resp.status_code == 200
        file_path = upload_resp.json()["file_path"]

        # 提交任务
        submit_payload = {
            "type": "process",
            "params": {"file_path": file_path, "source_name": "test.txt"},
        }
        submit_resp = await client.post("/tasks/", json=submit_payload)
        assert submit_resp.status_code == 202
        task_id = submit_resp.json()["task_id"]

        # 轮询等待完成
        final_status = None
        for _ in range(20):  # 最多尝试 20 次
            await asyncio.sleep(0.1)
            get_resp = await client.get(f"/tasks/{task_id}")
            assert get_resp.status_code == 200
            data = get_resp.json()
            if data["status"] in ("done", "failed", "cancelled"):
                final_status = "done"
                break

        # 最终断言：正常文本文件应该成功处理为 done
        assert final_status == "done", f"期望 done，实际得到 {final_status}"


@pytest.mark.asyncio
async def test_cancel_pending_task():
    """测试：任务还在队列中，处于pending状态时的取消"""
    with SessionLocal() as db:
        task = Task(
            type="process",
            params={"file_path": "/dummy"},
            source_name="test.txt",
            status=TaskStatus.pending,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        cancel_resp = await client.delete(f"/tasks/{task_id}")
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "cancelled"

        get_resp = await client.get(f"/tasks/{task_id}")
        assert get_resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_cancel_done_task():
    """测试：任务已完成，取消应返回 409 冲突"""
    with SessionLocal() as db:
        task = Task(
            type="process",
            params={"file_path": "/dummy"},
            source_name="test.txt",
            status=TaskStatus.done,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        task_id = task.id

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        cancel_resp = await client.delete(f"/tasks/{task_id}")
        assert cancel_resp.status_code == 409

        get_resp = await client.get(f"/tasks/{task_id}")
        assert get_resp.json()["status"] == "done"


@pytest.mark.asyncio
async def test_cancel_not_found():
    """测试：任务不存在，取消应返回 404"""
    fake_id = uuid.uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        cancel_resp = await client.delete(f"/tasks/{fake_id}")
        assert cancel_resp.status_code == 404
