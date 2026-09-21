import pytest
from app.plugins.registry import get_registry, get_runner, RunnerRegistry
from app.models import Task, TaskType


async def mock_runner(task, db):
    """一个假的业务执行器，仅用于测试注册和获取"""
    pass


async def another_mock_runner(task, db):
    """另一个假执行器，用于测试覆盖注册"""
    pass


def test_register_and_get():
    """注册一个 runner 后，能通过 get 取回同一个函数对象"""
    registry = RunnerRegistry()
    # 注册
    registry.register(TaskType.download, mock_runner)
    # 获取
    retrieved = registry.get(TaskType.download)
    # 验证是同一个函数
    assert retrieved is mock_runner
    assert registry.has(TaskType.download) is True


def test_get_unregistered_returns_none():
    registry = RunnerRegistry()
    assert registry.get(TaskType.process) is None
    assert registry.has(TaskType.process) is False


def test_register_overwrite():
    registry = RunnerRegistry()

    registry.register(TaskType.download, mock_runner)
    assert registry.get(TaskType.download) is mock_runner

    # 覆盖注册
    registry.register(TaskType.download, another_mock_runner)
    assert registry.get(TaskType.download) is another_mock_runner
    assert registry.get(TaskType.download) is not mock_runner


def test_registry_singleton():
    """两次调用 get_registry() 应该返回同一个实例"""
    reg1 = get_registry()
    reg2 = get_registry()

    assert reg1 is reg2

    # 通过 reg1 注册，reg2 应该能看到
    reg1.register(TaskType.download, mock_runner)
    assert reg2.get(TaskType.download) is mock_runner
