# test_data_layer.py
import pytest
import os
from datetime import datetime
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.exc import IntegrityError
from app.models import Task
from app.main import app
from app.core.db import get_session, engine as prod_engine


# 1. 定义一个测试用的 Engine 和 Session
@pytest.fixture(scope="function")
def test_engine():
    # ① 使用独立的物理文件（放在 tests/ 目录下，不污染根目录）
    test_db_path = "tests/test_app.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

    test_engine = create_engine(
        f"sqlite:///{test_db_path}",
        echo=True,
        connect_args={"check_same_thread": False},
    )
    # ② 建表（相当于 lifespan 里的 create_all，但由测试控制）
    SQLModel.metadata.create_all(test_engine)

    yield test_engine  # 把 engine 交给测试函数

    # ③ 清理：关闭连接 + 删除文件
    test_engine.dispose()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


# 2. 覆盖 get_session 依赖（让测试用的路由指向测试库）
@pytest.fixture(scope="function")
def client(test_engine):
    def override_get_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    client = TestClient(app)
    yield client

    # 清理覆盖（避免影响其他测试文件）
    app.dependency_overrides.clear()


# 3. 重启Engine
def restart_engine_and_get_client(old_engine):
    old_engine.dispose()
    new_engine = create_engine(
        old_engine.url,
        echo=True,
        connect_args={"check_same_thread": False},
    )

    def override_get_session():
        with Session(new_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


# 提交一个任务 → 重启 Engine → 查回来，断言状态一致
def test_create_and_retrieve(client, test_engine):
    resp = client.post(
        "/tasks",
        json={"type": "download", "params": {"url": "http://test-commit.cn/file.zip"}},
    )
    assert resp.status_code == 202
    task_id = resp.json()["task_id"]

    new_client = restart_engine_and_get_client(test_engine)

    try:
        get_resp = new_client.get(f"/tasks/{task_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == task_id
        assert get_resp.json()["type"] == "download"
    finally:
        app.dependency_overrides.clear()


# 不能用 client（TestClient）（因为 Pydantic 会在路由层拦截，不会触发数据库约束）。
# 必须直接操作 Session（通过 test_engine fixture）
def test_check_constraint(test_engine):
    with Session(test_engine) as db:
        task_invalid_type = Task(type="invalid", params={})
        db.add(task_invalid_type)
        with pytest.raises(IntegrityError) as exc_info:
            db.commit()
        assert "CHECK constraint" in str(exc_info)

    with Session(test_engine) as db:
        task_invalid_status = Task(type="download", params={}, status="invalid_status")
        db.add(task_invalid_status)
        with pytest.raises(IntegrityError) as exc_info:
            db.commit()
        assert "CHECK constraint" in str(exc_info)


# 插入 20 条数据（10 done / 10 pending）→
#  查 `status=done&page=1&size=5` →
#  断言返回 5 条、`total=10`、`pages=2`
def test_list_with_pagination(client, test_engine):
    with Session(test_engine) as db:
        for i in range(10):
            task = Task(
                id=f"6{i}ff1d29-d313-48e1-a046-d5be126d841a",
                type="process",
                status="done",
                progress=100,
                message="处理完成",
                created_at=(
                    datetime(2026, 8, 20, 16, i, 0)
                    if i % 2 == 0
                    else datetime(2026, 8, 21, 18, i, 0)
                ),
            )
            db.add(task)
        for i in range(10):
            task = Task(
                id=f"p{i}ff1d29-d313-48e1-a046-d5be126d841a",
                type="download",
                status="pending",
                progress=0,
                created_at=(
                    datetime(2026, 8, 20, 17, i, 0)
                    if i % 2 == 0
                    else datetime(2026, 8, 21, 15, i, 0)
                ),
            )
            db.add(task)
        db.commit()

        resp_done = client.get("/tasks/?status=done&page=1&size=5")
        assert resp_done.status_code == 200
        data_done = resp_done.json()
        assert len(data_done["items"]) == 5
        assert data_done["pages"] == 2
        assert data_done["total"] == 10
        assert (
            data_done["items"][0]["created_at"] > data_done["items"][-1]["created_at"]
        )

        resp_pending = client.get("/tasks/?status=pending&page=2&size=3")
        assert resp_pending.status_code == 200
        data_pending = resp_pending.json()
        assert len(data_pending["items"]) == 3
        assert data_pending["pages"] == 4
        assert data_pending["total"] == 10
        assert (
            data_pending["items"][0]["created_at"]
            > data_pending["items"][-1]["created_at"]
        )

        resp_default = client.get("/tasks/?page=1&size=10")
        assert resp_default.status_code == 200
        data_default = resp_default.json()
        assert len(data_default["items"]) == 10
        assert data_default["pages"] == 2
        assert data_default["total"] == 20
        assert (
            data_default["items"][0]["created_at"]
            > data_default["items"][-1]["created_at"]
        )
