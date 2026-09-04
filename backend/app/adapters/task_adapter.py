from typing import Optional
from datetime import datetime
from app.models import Task, TaskStatus
from fastapi_async_lib.schemas.base_task import BaseTask, BaseTaskStatus


class TaskAdapter(BaseTask):
    """
    Task 适配器：将 app.models.Task 适配为 引擎层fastapi_async_lib 的 BaseTask 协议

    这样引擎层就可以操作业务层（app.models）的对象，而不需要让 Task 直接继承 BaseTask。
    """

    def __init__(self, task: Task, db_session):
        self._task = task
        self._db = db_session

    # ---------- 属性映射 ----------
    @property
    def id(self) -> str:
        return self._task.id

    @property
    def params(self) -> dict:
        return self._task.params

    @property
    def status(self) -> BaseTaskStatus:
        return BaseTaskStatus(self._task.status.value)

    @property
    def progress(self) -> int:
        return self._task.progress

    @property
    def message(self) -> Optional[str]:
        return self._task.message

    @property
    def source_name(self) -> Optional[str]:
        return self._task.source_name

    @property
    def created_at(self) -> datetime:
        return self._task.created_at

    # ---------- 引擎层需要的方法 ----------
    def update_status(
        self, status: BaseTaskStatus, message: Optional[str] = None
    ) -> None:
        self._task.status = TaskStatus(status.value)
        if message:
            self._task.message = message
            self._db.commit()

    def update_progress(self, progress: int, message: Optional[str] = None) -> None:
        self._task.progress = progress
        if message:
            self._task.message = message
            self._db.commit()

    def get_raw_task(self) -> Task:
        return self._task
