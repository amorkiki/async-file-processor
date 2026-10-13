import os
from pathlib import Path

# 项目根目录（backend/）
BASE_DIR = Path(os.getenv("DATA_DIR", "./data"))

# 上传文件存放目录
UPLOAD_DIR = BASE_DIR / "uploads"

# 输出文件存放目录（下载的文件、清洗后的 JSON）
OUTPUT_DIR = BASE_DIR / "output"

# 确保目录存在（可选，但最好在启动时创建）
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _read_int_env(
    name: str, default: int, min_value: int = 1, max_value: int = 32
) -> int:
    """从环境变量读取整数，带默认值和范围校验。"""
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default

    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"环境变量 {name} 必须是整数，当前为 {raw!r}") from exc

    if not (min_value <= value <= max_value):
        raise RuntimeError(
            f"环境变量 {name} 必须在 [{min_value}, {max_value}] 范围内，当前为 {value}"
        )

    return value


# Worker 协程数量
WORKER_COUNT = _read_int_env("WORKER_COUNT", default=3)
