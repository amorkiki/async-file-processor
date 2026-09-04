from abc import ABC, abstractmethod
from typing import Optional, Protocol
from enum import Enum
from datetime import datetime


# ---------- 抽象状态和类型枚举 ----------
class BaseTaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


class BaseTaskType(str, Enum):
    # 不定义具体值，由子类实现
    pass


# ---------- 异步任务抽象基类，所有具体业务 Task 需继承此接口 ----------
class BaseTask(Protocol):
    """
    任务抽象接口（协议）

    引擎层只依赖这个协议，不依赖具体的 SQLModel 模型。
    具体业务层需要实现这个协议。
    """

    # ---------- 核心字段（只读） ----------
    @property
    def id(self) -> str:
        """任务唯一标识"""
        ...

    @property
    def status(self) -> BaseTaskStatus:
        """当前状态"""
        ...

    @property
    def progress(self) -> int:
        """进度0~100"""
        ...

    @property
    def message(self) -> Optional[str]:
        """状态消息"""
        ...

    @property
    def source_name(self) -> Optional[str]:
        """源文件名"""
        ...

    @property
    def params(self) -> dict:
        """任务参数"""
        ...

    @property
    def created_at(self) -> datetime:
        """创建时间"""
        ...

    # ---------- 引擎层需要的方法 ----------
    def update_status(
        self, status: BaseTaskStatus, message: Optional[str] = None
    ) -> None:
        """更新状态（引擎层调用）"""
        ...

    def update_progress(self, progress: int, message: Optional[str] = None) -> None:
        """更新进度（引擎层调用）"""
        ...
