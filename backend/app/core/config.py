from pathlib import Path

# 项目根目录（backend/）
BASE_DIR = Path("/app/data")

# 上传文件存放目录
UPLOAD_DIR = BASE_DIR / "uploads"

# 输出文件存放目录（下载的文件、清洗后的 JSON）
OUTPUT_DIR = BASE_DIR / "output"

# 确保目录存在（可选，但最好在启动时创建）
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
