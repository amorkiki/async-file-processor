import os
import re
import json
import asyncio
import pdfplumber
import aiofiles
from pathlib import Path
from docx import Document
from sqlmodel import Session
from app.models import Task, TaskStatus
from app.core.config import OUTPUT_DIR

MAX_CHARS_LIMIT = 5_000_000


# ---------- 辅助函数 1 ：根据文件后缀提取纯文本，并做基础清洗 ----------
def extract_clean_text(file_path: Path) -> str:
    ext = file_path.suffix.lower()  # 文件后缀
    raw_text = ""

    if ext == ".pdf":
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        raw_text += text
        except Exception as e:
            # 如果 pdfplumber 失败，回退到 pypdf
            print(f"⚠️ pdfplumber 解析失败，回退到 pypdf: {e}")
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    raw_text += text
    elif ext == ".docx":
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


# ---------- 辅助函数 2 ：按字符数切分文本，每块不超过 max_chars ----------
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
    if source_path.is_dir() or source_path.is_symlink():
        raise ValueError("当前仅支持处理单个文件，请勿使用目录或符号链接")
    if not source_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # ---- 阶段 1: 提取与清洗 (进度 30%) ----
    db.refresh(task)
    if task.status == TaskStatus.cancelled:
        return
    task.progress = 30
    task.message = f"正在清洗文档: {source_path.name}"
    db.commit()

    clean_text = await asyncio.to_thread(extract_clean_text, source_path)
    if not clean_text:
        raise ValueError("文档内容为空或无法解析")

    total_chars = len(clean_text)
    if total_chars > MAX_CHARS_LIMIT:
        raise ValueError(f"文件过大（{total_chars} 字符），当前限制 {MAX_CHARS_LIMIT}")

    estimated_tokens = total_chars // 2  # 粗略估算

    # ---- 阶段 2: 按字符分块 (进度 70%) ----
    db.refresh(task)
    if task.status == TaskStatus.cancelled:
        return
    task.progress = 70
    task.message = f"正在分块 (约 {estimated_tokens} tokens)"
    db.commit()

    chunks = await asyncio.to_thread(chunk_text_by_chars, clean_text, 1000)

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
            await asyncio.to_thread(os.remove, result_path)
        return

    task.progress = 100
    task.message = f"清洗完成！生成 {len(chunks)} 个知识块，总字符数 {total_chars}"
    task.result_path = str(result_path)
    db.commit()
    print(f"✅ 文件预处理完成: {result_path}")
