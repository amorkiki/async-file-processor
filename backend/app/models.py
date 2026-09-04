# models.py
from typing import Optional
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, JSON
from sqlalchemy import Index, CheckConstraint, text
from uuid import uuid4
from enum import Enum
from datetime import datetime


class TaskType(str, Enum):
    download = "download"
    process = "process"


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"


status_values = [f"'{item.value}'" for item in TaskStatus]
type_values = [f"'{item.value}'" for item in TaskType]


class Task(SQLModel, table=True):
    __table_args__ = (
        Index("ix_task_status_created", "status", text("created_at DESC")),
        CheckConstraint(
            f"status IN ({','.join(status_values)})",
            name="ck_status_valid",
        ),
        CheckConstraint(
            f"type IN ({','.join(type_values)})",
            name="ck_type_valid",
        ),
    )
    id: str = Field(
        default_factory=lambda: str(uuid4()), primary_key=True, nullable=False
    )
    type: TaskType = Field(default=TaskType.download, nullable=False)
    source_name: Optional[str] = Field(default=None, nullable=True)
    params: dict = Field(sa_type=JSON, default_factory=dict, nullable=False)
    status: TaskStatus = Field(default=TaskStatus.pending, nullable=False)
    progress: int = Field(default=0, nullable=False)
    message: str | None = None
    result_path: str | None = None
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column_kwargs={"onupdate": datetime.now},
        nullable=False,
    )


class TaskCreate(BaseModel):
    type: TaskType
    params: dict


class TaskOut(BaseModel):
    id: str  # ← 从 Task 传进来，不是自己生成
    source_name: str | None = None
    type: TaskType = TaskType.download
    status: TaskStatus = TaskStatus.pending
    progress: int
    message: str | None = None
    created_at: datetime


class TaskListResponse(BaseModel):
    items: list[TaskOut]
    total: int
    page: int
    size: int
    pages: int


class ErrorOut(BaseModel):
    code: int  # 用 HTTP 状态码本身当业务码
    message: str
