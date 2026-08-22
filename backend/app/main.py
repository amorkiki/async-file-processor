# 入口mian.py：FastAPI() 实例 + 挂路由
import asyncio
from sqlmodel import SQLModel
from sqlalchemy.exc import IntegrityError
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.routers import tasks
from app.models import ErrorOut
from app.core.db import engine
from app.core.queue import worker


# 两个时机的钩子：启动时（yield 前）把 worker 放后台，关闭时（yield 后）取消 worker.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 建表（若没有）
    SQLModel.metadata.create_all(engine)
    print("✅ 数据库就绪")
    # 启动 3 个 worker 后台任务
    workers = [asyncio.create_task(worker()) for _ in range(3)]
    yield
    # 关闭时全部取消
    for w in workers:
        w.cancel()


app = FastAPI(
    title="异步文件处理服务",
    description="基于 FastAPI 的异步任务服务：提交 download/process 任务，后台 worker 并发执行，支持查询进度与取消。所有错误统一返回 {code, message} 格式。",
    version="0.1.0",
    lifespan=lifespan,
)


# ------------------- 挂载路由 -------------------
app.include_router(tasks.router)


# ------------------- 根路径（健康检查） -------------------
@app.get("/")
async def root():
    return {"message": "Async File Processor API"}


# ------------------- 全局异常处理 -------------------
def error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorOut(code=status_code, message=message).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return error_response(exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return error_response(422, "请求参数校验失败")


@app.exception_handler(IntegrityError)
async def integrity_err_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    error_msg = str(exc.orig) if exc.orig else str(exc)
    if "NOT NULL" in error_msg:
        message = "缺少必填字段"
    elif "CHECK constraint" in error_msg:
        message = "字段值不合法（枚举范围外）"
    elif "UNIQUE constraint" "PRIMARY KEY" in error_msg:
        message = "主键或唯一键冲突"
    else:
        message = f"数据完整性错误: {error_msg}"
    return error_response(400, message)


@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
    # ⚠️ 生产环境这里要先 logger.exception(exc) 记录堆栈，再返回 500
    print(f"⚠️ 未捕获异常: {exc}")  # 临时打印，方便调试
    return error_response(500, "服务器内部错误")
