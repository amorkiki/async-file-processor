# 入口：FastAPI() 实例 + 挂路由
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI ,HTTPException # type: ignore
from fastapi.exceptions import RequestValidationError # type: ignore
from fastapi.responses import JSONResponse # type: ignore
from app.models import ErrorOut, Task,TaskCreate,TaskOut,TaskStatus
from uuid import UUID
from app.services.task_runner import execute

# 模块级：queue,因为worker和submit_task必须用同一个queue
queue: asyncio.Queue[Task] = asyncio.Queue()
# 模块级：任务仓库（所有任务存这里）
tasks: dict[str, Task] = {}


async def worker():
    while True:
        task=await queue.get()
        try:
            if task.status == TaskStatus.cancelled:  # 在队列里就被取消了 → 跳过
                continue
            task.status = TaskStatus.running
            await execute(task)
        finally:
            queue.task_done()   # 不会关闭队列。它是记账：告诉队列"我从 get() 拿走的那个任务，处理完了"。


#两个时机的钩子：启动时（yield 前）把 worker 放后台，关闭时（yield 后）取消 worker.
@asynccontextmanager
async def lifespan(app:FastAPI):
    workers = [asyncio.create_task(worker()) for _ in range(3)]  # 3 个引用全存住
    yield
    for w in workers:          # 关闭时全部取消
        w.cancel()

app = FastAPI(
    title="异步文件处理服务",
    description="基于 FastAPI 的异步任务服务：提交 download/process 任务，后台 worker 并发执行，支持查询进度与取消。所有错误统一返回 {code, message} 格式。",
    version="0.1.0",
    lifespan=lifespan)


@app.post('/tasks',
        status_code=202,
        summary="提交任务",
        description="提交一个异步任务（download 或 process）。任务进入队列后由后台 worker 执行，立即返回 task_id（202），不等待执行完成。",
        responses={422: {"model": ErrorOut, "description": "参数校验失败（非法 type 等）"}})
async def submit_task(payload:TaskCreate) -> dict:
    task = Task(type=payload.type, params=payload.params)
    tasks[task.id] = task  #仓库持有引用
    await queue.put(task)   #队列也持有引用（同一个对象）
    return {"task_id": task.id}


@app.get('/tasks/{task_id}',
        response_model=TaskOut,
        summary="查询任务状态",
        description="按 task_id 查询任务的状态、进度与消息。任务完成后可去 output/ 目录查看产出文件。",
        responses={404: {"model": ErrorOut, "description": "任务不存在"}})
async def get_task(task_id:UUID)->TaskOut:
    task = tasks.get(str(task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task 


@app.delete('/tasks/{task_id}',
            status_code=200,
            summary="取消任务",
            description="取消 pending/running 状态的任务（协作式取消：设置 cancelled 标记，worker 在检查点停止）。已完成/已失败/已取消的任务不可取消。",
            responses={
                404: {"model": ErrorOut, "description": "任务不存在"},
                409: {"model": ErrorOut, "description": "任务已终态（done/failed/cancelled），无法取消"},
            })
async def delete_task(task_id:UUID)->dict:
    task = tasks.get(str(task_id))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in (TaskStatus.done,TaskStatus.cancelled,TaskStatus.failed):
        raise HTTPException(status_code=409, detail=f"任务当前状态 {task.status.value}，无法取消")
    task.status = TaskStatus.cancelled
    task.message = "任务已取消"
    return {"task_id":task.id, "status": task.status.value}


def error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code,
                        content=ErrorOut(code=status_code, message=message).model_dump())

@app.exception_handler(HTTPException)
async def http_exc_handler(request, exc):
    # return JSONResponse(status_code = exc.status_code, content={"code": exc.status_code, "message": str(exc.detail)})
    return error_response(exc.status_code,str(exc.detail))

@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    # return JSONResponse(status_code = 422, content={"code": 422, "message": "请求参数校验失败"})
    return error_response(422, "请求参数校验失败")

@app.exception_handler(Exception)
async def generic_handler(request, exc):
    # ⚠️ 生产环境这里要先 logger.exception(exc) 记录堆栈，再返回 500
    # return JSONResponse(status_code = 500, content={"code": 500, "message": "服务器内部错误"})
    return error_response(500, "服务器内部错误")

