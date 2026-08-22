# db.py
from sqlmodel import create_engine
from app.models import Task
from sqlalchemy.orm import sessionmaker

# 1. 创建数据库引擎
# echo=True 会在终端打印所有执行的 SQL 语句，方便开发调试
engine = create_engine(
    "sqlite:///app.db", echo=True, connect_args={"check_same_thread": False}
)

# 2. 创建会话工厂（SessionLocal）
# 每次调用 SessionLocal() 就会创建一个新的数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 3. 定义依赖注入函数（供 FastAPI 路由使用）
def get_session():
    """
    FastAPI 依赖注入：每个请求进来时创建一个 Session，请求结束时自动关闭。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
