# tasks.py
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from sqlmodel import Session, select, func
from uuid import UUID, uuid4
import shutil
from app.models import (
    Task,
    TaskCreate,
    TaskListResponse,
    TaskOut,
    TaskStatus,
    ErrorOut,
)
from app.core.db import get_session
from app.core.engine import submit_task_to_queue
from app.core.config import UPLOAD_DIR
from fastapi_async_lib.engine.state_machine import (
    create_task_state_machine,
    TransitionError,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "/",
    status_code=202,
    summary="提交任务",
    description="提交一个异步任务（download 或 process）。任务进入队列后由后台 worker 执行，立即返回 task_id（202），不等待执行完成。",
    responses={422: {"model": ErrorOut, "description": "参数校验失败（非法 type 等）"}},
)
async def submit_task(payload: TaskCreate, db: Session = Depends(get_session)):
    # 1. 创建 Task 对象
    source_name = payload.params.get("source_name")
    task = Task(type=payload.type, params=payload.params, source_name=source_name)
    # 2. 持久化到数据库
    db.add(task)
    db.commit()
    db.refresh(task)
    # 3. 放入队列（引擎会异步处理）
    submit_task_to_queue(task)
    # 4. return task_id
    return {"task_id": task.id}


@router.get(
    "/{task_id}",
    response_model=TaskOut,
    summary="查询任务状态",
    description="按 task_id 查询任务的状态、进度与消息。任务完成后可去 output/ 目录查看产出文件。",
    responses={404: {"model": ErrorOut, "description": "任务不存在"}},
)
async def get_task(task_id: UUID, db: Session = Depends(get_session)) -> TaskOut:
    task = db.get(Task, str(task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get(
    "/",
    response_model=TaskListResponse,
    summary="查询历史任务列表",
    description="支持按状态过滤、分页、按创建时间降序排列。",
    responses={400: {"model": ErrorOut, "description": "参数校验失败"}},
)
async def list_tasks(
    status: TaskStatus | None = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_session),
) -> TaskListResponse:
    if page < 1 or size < 1:
        raise HTTPException(status_code=400, detail="page 和 size 必须 >= 1")

    # 构建基础查询，默认降序
    stmt = select(Task).order_by(Task.created_at.desc())
    # 构建count查询
    count_stmt = select(func.count()).select_from(Task)

    # 根据status动态过滤
    if status is not None:
        stmt = stmt.where(Task.status == status)
        count_stmt = count_stmt.where(Task.status == status)

    # 分页
    stmt = stmt.offset((page - 1) * size).limit(size)

    # 执行两次查询（同一个session下）
    items = db.execute(stmt).scalars().all()  # 提取 ORM 对象列表 (list[Task])
    total = db.execute(count_stmt).scalar()  # 直接取标量数值 (int)

    # 显式转换每个 Task 为 TaskOut
    items_out = [TaskOut.model_validate(item, from_attributes=True) for item in items]

    return TaskListResponse(
        items=items_out,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.delete(
    "/{task_id}",
    status_code=200,
    summary="取消任务",
    description="取消 pending/running 状态的任务（协作式取消：设置 cancelled 标记，worker 在检查点停止）。已完成/已失败/已取消的任务不可取消。",
    responses={
        404: {"model": ErrorOut, "description": "任务不存在"},
        409: {
            "model": ErrorOut,
            "description": "任务已终态（done/failed/cancelled），无法取消",
        },
    },
)
async def delete_task(task_id: UUID, db: Session = Depends(get_session)) -> dict:
    task = db.get(Task, str(task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    sm = create_task_state_machine()
    sm.reset(task.status.value)

    try:
        sm.transition_to(TaskStatus.cancelled.value)
    except TransitionError as e:
        raise HTTPException(
            status_code=409, detail=f"任务当前状态 {task.status.value}，无法取消"
        )

    task.status = TaskStatus.cancelled
    task.message = "任务已取消"
    db.commit()
    return {"task_id": task.id, "status": task.status.value}


@router.post(
    "/upload",
    status_code=200,
    summary="上传文件",
    description="上传一个文件到服务器，返回服务器上的绝对路径。前端拿到路径后，再提交任务时使用该路径。",
)
async def upload_file(file: UploadFile = File(...)):
    # 1. 生成唯一文件名，避免冲突
    ext = file.filename.split(".")[-1] if "." in file.filename else "file"
    unique_name = f"{uuid4()}.{ext}"
    save_path = UPLOAD_DIR / unique_name

    # 2. 保存文件
    try:
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    finally:
        await file.close()  # 确保文件句柄释放

    # 3. 返回绝对路径（前端将用它作为 file_path）
    return {"file_path": str(save_path.absolute())}
