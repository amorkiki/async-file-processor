from pydantic import BaseModel, Field # type: ignore
from uuid import uuid4
from enum import Enum
from datetime import datetime

class TaskType(str,Enum):
    download = "download"
    process = "process"

class TaskStatus(str, Enum):
    pending = "pending" 
    running = "running"
    done = "done"
    failed = "failed"
    cancelled = "cancelled"

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: TaskType = TaskType.download    
    params: dict = {}    
    status: TaskStatus = TaskStatus.pending
    progress: int = 0
    message: str | None = None     
    result_path: str | None = None 
    created_at: datetime = Field(default_factory=datetime.now)


class TaskCreate(BaseModel):
    type:TaskType
    params:dict


class TaskOut(BaseModel):
    id: str              # ← 从 Task 传进来，不是自己生成
    type: TaskType = TaskType.download    
    status: TaskStatus = TaskStatus.pending
    progress: int    
    message: str | None = None
    created_at: datetime  # ← 从 Task 传进来，不是自己生成


class ErrorOut(BaseModel):
    code: int            # 用 HTTP 状态码本身当业务码
    message: str