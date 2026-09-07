import os
import asyncio
import aiohttp
import aiofiles
from sqlmodel import Session
from app.models import Task, TaskStatus
from app.core.config import OUTPUT_DIR


async def run_download(task: Task, db: Session) -> None:
    # 1. 获取参数
    url = task.params.get("url")
    if not url:
        raise ValueError("缺少下载链接 (url)")

    # 本地保存路径
    local_path = OUTPUT_DIR / f"{task.id}.dat"

    # 2. 异步下载
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise ConnectionError(f"下载失败，HTTP{resp.status}")

            try:
                total_size = int(resp.headers.get("content-length", 0))
            except (ValueError, TypeError):
                total_size = 0

            downloaded = 0

            async with aiofiles.open(local_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 64):  # 64KB 每块
                    # ① 写入磁盘
                    await f.write(chunk)
                    downloaded += len(chunk)

                    # ② 检查取消（协作式）
                    db.refresh(task)
                    if task.status == TaskStatus.cancelled:
                        # 删除已下载的半截文件
                        if local_path.exists():
                            await asyncio.to_thread(os.remove, local_path)
                        return

                    # ③ 计算进度并更新数据库（每 100KB 更新一次，避免太频繁）
                    if downloaded % (1024 * 100) < 1024 * 64:
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                            msg = f"下载中 {downloaded // 1024}KB / {total_size // 1024}KB"
                        else:
                            progress = 0
                            msg = f"下载中 {downloaded // (1024*1024)}MB（未知总大小）"
                        task.progress = progress
                        task.message = msg
                        db.commit()
                        print(f"✅ 下载进度: {progress}%")
    # ④ 下载完成
    db.refresh(task)
    if task.status == TaskStatus.cancelled:
        return
    task.progress = 100
    task.message = "下载完成"
    task.result_path = str(local_path)
    db.commit()
    print(f"✅ 文件已下载到: {local_path}")
