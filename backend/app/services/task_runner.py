# execute逻辑
# main.py中 取任务 → `running` → `await execute(task)` → done/failed
# 模块级 async 函数 + 分派表
import asyncio
import hashlib
from pathlib import Path
from sqlmodel import Session
from app.models import Task, TaskType, TaskStatus

OUTPUT_DIR = Path("output")  # uvicorn 从 backend/ 启动 → backend/output/


async def run_download(task: Task, db: Session) -> None:
    await asyncio.sleep(0.1)  # ✅ 增加微小延迟，确保取消请求能抢先
    url = task.params.get("url", "https://if-no-url-key")
    chunks = 5  # 分为5块下载
    # for 循环 5 次，每次"模拟耗时 + 更新进度"：
    for i in range(1, chunks + 1):
        # ✅ 每次循环先从数据库刷新对象，确保是 attached 状态
        db.refresh(task)
        if task.status == TaskStatus.cancelled:
            return

        await asyncio.sleep(1)
        task.progress = round(i / chunks * 100)  # 20/40/60/80/100
        task.message = f"正在下载 {i}/{chunks} 块…"

        db.commit()
        print(f"✅ 提交进度: {task.progress}%")
        if i == 3 and "bad" in url:  # 方便模拟测试的判断
            raise ConnectionError(f"第 {i}/{chunks} 块下载失败(404):{url}")

    content = f"下载完成\nURL: {url}\n分块数: {chunks}\n"  # 模拟

    # 下载完成后要写入output/下面
    await _write_result(task, content)
    task.message = "下载完成"


async def run_process(task: Task, db: Session) -> None:
    await asyncio.sleep(0.1)  # ✅ 增加微小延迟，确保取消请求能抢先
    # 读
    input_text = task.params.get("text", "if no text key")
    # 第一步：20%
    db.refresh(task)
    if task.status == TaskStatus.cancelled:
        return
    task.progress, task.message = 20, "读取输入…"
    await asyncio.sleep(2)
    db.commit()  # ✅ 立即提交
    print(f"✅ 提交进度: 20%")

    # 第二步：55%
    db.refresh(task)
    if task.status == TaskStatus.cancelled:
        return
    task.progress, task.message = 55, "处理中…"
    await asyncio.sleep(2)
    db.commit()  # ✅ 立即提交
    print(f"✅ 提交进度: 55%")

    # 算
    result = hashlib.md5(input_text.encode()).hexdigest()

    # 第三步：90%
    db.refresh(task)
    if task.status == TaskStatus.cancelled:
        return
    task.progress, task.message = 90, "写入结果…"
    await asyncio.sleep(2)
    db.commit()  # ✅ 立即提交
    print(f"✅ 提交进度: 90%")

    # 写
    content = f"输入: {input_text}\nMD5: {result}\n"  # 把结果拼成要落盘的内容
    await _write_result(task, content)
    task.message = "处理完成"


# 分派表
RUNNERS = {TaskType.download: run_download, TaskType.process: run_process}


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

        task.progress = 100
        task.status = TaskStatus.done

        # ✅ 不需要 db.add(task)，因为 task 已经是托管对象
        db.commit()

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


async def _write_result(task: Task, content: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)  # ① 确保目录存在
    path = OUTPUT_DIR / f"{task.id}.txt"  # ② 结果文件名
    await asyncio.to_thread(path.write_text, content)  # ③ 同步 I/O 丢出事件循环
    task.result_path = str(path)  # ④ 填回任务
