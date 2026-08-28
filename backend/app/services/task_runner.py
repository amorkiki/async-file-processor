# execute逻辑
# main.py中 取任务 → `running` → `await execute(task)` → done/failed
# 模块级 async 函数 + 分派表
import asyncio
import os
import json
import re
import aiohttp
import aiofiles
import pdfplumber
from pathlib import Path
from docx import Document
from sqlmodel import Session
from app.models import Task, TaskType, TaskStatus

OUTPUT_DIR = Path("output")  # uvicorn 从 backend/ 启动 → backend/output/


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

            total_size = int(resp.headers.get("content-length", 0))
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
                            os.remove(local_path)
                        return

                    # ③ 计算进度并更新数据库（每 100KB 更新一次，避免太频繁）
                    if downloaded % (1024 * 100) < 1024 * 64:
                        if total_size > 0:
                            progress = int((downloaded / total_size) * 100)
                        else:
                            # 如果不知道总大小，按 10MB 估算，最多到 90%
                            progress = min(
                                90, int((downloaded / (10 * 1024 * 1024)) * 100)
                            )
                        task.progress = progress
                        task.message = (
                            f"下载中 {downloaded // 1024}KB / {total_size // 1024}KB"
                        )
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


# ---------- 辅助函数：根据文件后缀提取纯文本，并做基础清洗 ----------
def extract_clean_text(file_path: Path) -> str:
    ext = file_path.suffix.lower()  # 文件后缀
    raw_text = ""

    if ext == ".pdf":
        # 优先尝试 pdfplumber（更稳健）
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        raw_text += text
        except Exception as e:
            # 如果 pdfplumber 失败，回退到 pypdf
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    raw_text += text
    elif ext == ".doxc":
        doc = Document(file_path)
        for para in doc.paragraphs:
            raw_text += para.text + "\n"
    elif ext in [".txt", ".md", ".csv", ".json"]:
        raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(
            f"不支持的文件格式: '{ext}'（支持: .pdf, .docx, .txt, .md, .csv, .json）"
        )

    # 基础清洗：合并多余换行、空白
    cleaned = " ".join(raw_text.split())
    return cleaned


# ---------- 辅助函数：按字符数切分文本，每块不超过 max_chars ----------
def chunk_text_by_chars(text: str, max_chars: int = 1000) -> list[str]:
    try:
        chunks = []
        current_chunk = []
        current_len = 0

        # 按句子分割（保留标点）
        sentences = re.split(r"(?<=[。！？.!?])\s*", text)

        for sent in sentences:
            if not sent:
                continue
            sent_len = len(sent)
            # 如果单句超过阈值，强制截断（极少情况）
            if sent_len > max_chars:
                chunks.append(sent[: int(max_chars * 0.8)])
                chunks.append(sent[int(max_chars * 0.8) :])
                continue

            if current_len + sent_len <= max_chars:
                current_chunk.append(sent)
                current_len += sent_len
            else:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sent]
                current_len = sent_len

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    except Exception as e:
        print(f"❌ 分块时出错: {e}")
        import traceback

        traceback.print_exc()
        raise


async def run_process(task: Task, db: Session) -> None:
    # 1. 获取参数
    file_path = task.params.get("file_path")
    if not file_path:
        raise ValueError("缺少文件路径 (file_path)")

    source_name = task.params.get("source_name")
    if source_name:
        task.source_name = source_name
        db.commit()

    source_path = Path(file_path)
    if source_path.is_dir():
        raise ValueError("当前仅支持处理单个文件，请选择文件而非目录")
    if not source_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # ---- 阶段 1: 提取与清洗 (进度 30%) ----
    db.refresh(task)
    if task.status == TaskStatus.cancelled:
        return
    task.progress = 30
    task.message = f"正在清洗文档: {source_path.name}"
    db.commit()

    loop = asyncio.get_event_loop()
    clean_text = await loop.run_in_executor(None, extract_clean_text, source_path)

    if not clean_text:
        raise ValueError("文档内容为空或无法解析")

    total_chars = len(clean_text)
    estimated_tokens = total_chars // 2  # 粗略估算

    # ---- 阶段 2: 按字符分块 (进度 70%) ----
    db.refresh(task)
    if task.status == TaskStatus.cancelled:
        return
    task.progress = 70
    task.message = f"正在分块 (约 {estimated_tokens} tokens)"
    db.commit()

    chunks = await loop.run_in_executor(None, chunk_text_by_chars, clean_text, 1000)

    # ---- 阶段 3: 生成结果 JSON (进度 100%) ----
    result_json = {
        "source_file": source_path.name,
        "total_chars": total_chars,
        "estimated_tokens": estimated_tokens,
        "chunk_count": len(chunks),
        "chunks": [
            {"index": i, "text": chunk, "chars": len(chunk)}
            for i, chunk in enumerate(chunks)
        ],
    }

    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result_path = OUTPUT_DIR / f"{task.id}_cleaned.json"
    async with aiofiles.open(result_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(result_json, indent=2, ensure_ascii=False))

    # 检查取消
    db.refresh(task)
    if task.status == TaskStatus.cancelled:
        if result_path.exists():
            os.remove(result_path)
        return

    task.progress = 100
    task.message = f"清洗完成！生成 {len(chunks)} 个知识块，总字符数 {total_chars}"
    task.result_path = str(result_path)
    db.commit()
    print(f"✅ 文件预处理完成: {result_path}")


# ---------- 分派表 ----------
RUNNERS = {
    TaskType.download: run_download,
    TaskType.process: run_process,
}


# 唯一入口：分流 + 兜底
async def execute(task: Task, db: Session) -> None:
    print(f"🚀 execute 被调用，任务 ID: {task.id}, 类型: {task.type}")
    try:
        runner = RUNNERS.get(task.type)
        if not runner:
            raise ValueError(f"未知任务类型: {task.type}")
        await runner(task, db)  # 传的是托管对象

        if task.status == TaskStatus.cancelled:  # 协作式：runner 中途退出的
            return
        if task.status != TaskStatus.done:
            task.status = TaskStatus.done
            task.progress = 100
            db.commit()  # ✅ 不需要 db.add(task)，因为 task 已经是托管对象

    except asyncio.CancelledError:
        # ✅ 关键：捕获 CancelledError，转为 cancelled 状态，而不是让 worker 误判为 failed
        task.status = TaskStatus.cancelled
        task.message = "任务被外部取消"
        # 取消状态也落库
        db.commit()

    except Exception as e:
        # 真正的业务错误（如 ConnectionError、ValueError 等）
        task.status = TaskStatus.failed
        task.message = f"执行失败：{e}"
        # 失败状态也落库
        db.commit()
