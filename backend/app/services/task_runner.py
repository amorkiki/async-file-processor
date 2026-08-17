# execute逻辑
# main.py中 取任务 → `running` → `await execute(task)` → done/failed
# 模块级 async 函数 + 分派表
import asyncio
import hashlib
from pathlib import Path
from app.models import Task, TaskType,TaskStatus

OUTPUT_DIR = Path("output")          # uvicorn 从 backend/ 启动 → backend/output/

async def run_download(task:Task)->None:
  url = task.params.get("url", "https://if-no-url-key")
  chunks = 5  # 分为5块下载
  # for 循环 5 次，每次"模拟耗时 + 更新进度"：
  for i in range(1, chunks+1):
    if task.status == TaskStatus.cancelled: 
      return
    
    await asyncio.sleep(0.3)
    task.progress = round(i/chunks*100)  # 20/40/60/80/100
    task.message = f"正在下载 {i}/{chunks} 块…"
    if i == 3 and "bad" in url: # 方便模拟测试的判断
      raise ConnectionError(f"第 {i}/{chunks} 块下载失败(404):{url}")
  
  content = f"下载完成\nURL: {url}\n分块数: {chunks}\n"  # 模拟

  # 下载完成后要写入output/下面
  await _write_result(task,content)
  task.message = "下载完成"


async def run_process(task:Task)->None:
  # 读
  input_text = task.params.get("text", "if no text key")
  if task.status == TaskStatus.cancelled: return
  task.progress, task.message = 20, "读取输入…"
  await asyncio.sleep(0.3) # 模拟耗时

  # 算（模拟：哈希）
  if task.status == TaskStatus.cancelled: return
  task.progress, task.message = 55, "处理中…"
  await asyncio.sleep(0.3)
  if task.status == TaskStatus.cancelled: return
  result = hashlib.md5(input_text.encode()).hexdigest()
  
  # 写
  content = f"输入: {input_text}\nMD5: {result}\n"         # 把结果拼成要落盘的内容
  task.progress, task.message = 90, "写入结果…"
  if task.status == TaskStatus.cancelled: return

  # 处理完成后要写入output/下面
  await _write_result(task,content)
  task.message = "处理完成"
  
# 分派表
RUNNERS={
  TaskType.download:run_download,
  TaskType.process: run_process
}

# 唯一入口：分流 + 兜底
async def execute(task:Task)->None:
  try:
    runner = RUNNERS.get(task.type) 
    if not runner:
      raise ValueError(f"未知任务类型: {task.type}")
    await runner(task)
    if task.status == TaskStatus.cancelled:   # 协作式：runner 中途退出的
      return 
    task.progress = 100
    task.status= TaskStatus.done
  except Exception as e:
    task.status = TaskStatus.failed
    task.message = f"执行失败：{e}"


async def _write_result(task: Task, content: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)          # ① 确保目录存在
    path = OUTPUT_DIR / f"{task.id}.txt"                   # ② 结果文件名
    await asyncio.to_thread(path.write_text, content)      # ③ 同步 I/O 丢出事件循环
    task.result_path = str(path)                           # ④ 填回任务