# 入口mian.py：FastAPI() 实例 + 挂路由
from sqlmodel import SQLModel
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from contextlib import asynccontextmanager
from app.routers import tasks
from app.models import ErrorOut
from app.core.db import engine
from app.core.engine import start_engine, stop_engine
from app.plugins.registry import get_registry
from app.core.config import WORKER_COUNT


# 两个时机的钩子：启动时（yield 前）把 worker 放后台，关闭时（yield 后）取消 worker.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 建表
    SQLModel.metadata.create_all(engine)
    print("✅ 数据库就绪")

    # 2. 注册业务执行器
    get_registry()
    print("✅ 执行器注册完成")

    # 3. 启动引擎（3 个 Worker）
    await start_engine(worker_count=WORKER_COUNT)

    yield

    # 4. 关闭时停止引擎
    await stop_engine()


app = FastAPI(
    title="异步文件处理服务",
    description="...",
    version="0.1.0",
    lifespan=lifespan,
)

# ------------------- 配置 CORS -------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    elif "UNIQUE constraint" in error_msg or "PRIMARY KEY" in error_msg:
        message = "主键或唯一键冲突"
    else:
        message = f"数据完整性错误: {error_msg}"
    return error_response(400, message)


@app.exception_handler(Exception)
async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
    # ⚠️ 生产环境这里要先 logger.exception(exc) 记录堆栈，再返回 500
    print(f"⚠️ 未捕获异常: {exc}")  # 临时打印，方便调试
    return error_response(500, "服务器内部错误")
