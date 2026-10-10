from typing import Dict, Callable, Awaitable, Optional
from sqlalchemy.orm import Session
from app.models import Task, TaskType
from app.plugins.download import run_download
from app.plugins.process_ai import run_process

# 执行器类型：接收 Task 和 Session，返回 Awaitable[None]
TaskRunnerFn = Callable[[Task, Session], Awaitable[None]]


class RunnerRegistry:
    def __init__(self):
        self._runners: Dict[TaskType, TaskRunnerFn] = {}

    def register(self, task_type: TaskType, runner: TaskRunnerFn) -> None:
        self._runners[task_type] = runner
        print(f"📌 已注册执行器: {task_type.value}")

    def get(self, task_type: TaskType) -> Optional[TaskRunnerFn]:
        return self._runners.get(task_type)

    def has(self, task_type: TaskType) -> bool:
        return task_type in self._runners

    def list(self) -> list:
        return list(self._runners.keys())


# ---------- 全局单例 ----------
_registry: Optional[RunnerRegistry] = None


def get_registry() -> RunnerRegistry:
    """获取全局注册表单例"""
    global _registry
    if _registry is None:
        _registry = RunnerRegistry()
        # 自动注册默认执行器
        _registry.register(TaskType.download, run_download)
        _registry.register(TaskType.process, run_process)
    return _registry


def get_runner(task_type: TaskType) -> Optional[TaskRunnerFn]:
    """便捷方法：获取执行器"""
    return get_registry().get(task_type)
