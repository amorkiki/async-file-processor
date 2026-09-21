import pytest
from unittest.mock import MagicMock
from app.adapters.task_adapter import TaskAdapter
from app.models import Task, TaskStatus, TaskType


def test_task_adapter_property_mapping():
    """测试适配器能正确映射 Task 的属性"""
    task = Task(
        id="test-1",
        type=TaskType.download,
        params={"url": "http://example.com/file-1.pdf"},
        status=TaskStatus.pending,
        progress=0,
        source_name="test1.pdf",
    )
    mock_db = MagicMock()
    adapter = TaskAdapter(task, mock_db)

    assert adapter.id == "test-1"
    assert adapter.status == TaskStatus.pending
    assert adapter.params == {"url": "http://example.com/file-1.pdf"}
    assert adapter.progress == 0
    assert adapter.source_name == "test1.pdf"
    assert adapter.created_at is not None


def test_task_adapter_update_status():
    task = Task(
        id="test-2",
        type=TaskType.download,
        params={"url": "http://example.com/file-2.pdf"},
        status=TaskStatus.pending,
        progress=0,
        source_name="test2.pdf",
    )
    mock_db = MagicMock()
    adapter = TaskAdapter(task, mock_db)

    adapter.update_status(TaskStatus.running, "任务开始执行")

    assert task.status == TaskStatus.running
    assert task.message == "任务开始执行"

    mock_db.commit.assert_called_once()


def test_task_adapter_update_progress():
    task = Task(
        id="test-3",
        type=TaskType.process,
        params={"url": "http://example.com/file-3.pdf"},
        status=TaskStatus.running,
        progress=0,
        source_name="test3.pdf",
    )
    mock_db = MagicMock()
    adapter = TaskAdapter(task, mock_db)

    adapter.update_progress(50, "正在解析")

    assert task.progress == 50
    assert task.message == "正在解析"

    mock_db.commit.assert_called_once()


def test_task_adapter_get_raw_task():
    """测试 get_raw_task 能返回原始 Task 对象本身（同一个引用）"""
    task = Task(
        id="test-4",
        type=TaskType.process,
        params={"url": "http://example.com/file-4.pdf"},
        status=TaskStatus.running,
        progress=50,
        source_name="test4.pdf",
    )
    mock_db = MagicMock()
    adapter = TaskAdapter(task, mock_db)

    # 执行：拆包
    raw_task = adapter.get_raw_task()
    assert raw_task is task

    # 修改 raw_task 会影响 adapter 内部
    raw_task.progress = 60
    assert adapter.progress == 60
