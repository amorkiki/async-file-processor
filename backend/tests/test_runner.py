import asyncio
from pathlib import Path
from app.models import Task, TaskType
from app.services.task_runner import execute

async def one(task: Task, label: str):  # 用 label 参数 + 打印，代替断言
    await execute(task)
    print(f"[{label}] status={task.status.value} progress={task.progress}")
    print(f"    message     = {task.message}")
    print(f"    result_path = {task.result_path}")
    if task.result_path:
        p = Path(task.result_path)
        print(f"    文件存在?    = {p.exists()}")   # 没有返回值 ≠ 没产出
        if p.exists():
            print(f"    文件内容    = {p.read_text()!r}")  # 用 repr 打印文件内容，换行会显示成 \n——避免多行文本把输出刷花。

async def main():
    # 直接传内存对象Task，不走 HTTP（"单测"的精髓）
    await one(Task(type=TaskType.download, params={"url": "https://example.com/file.bin"}), "download-成功")
    await one(Task(type=TaskType.download, params={"url": "https://bad.example.com/x"}),    "download-失败")
    await one(Task(type=TaskType.process,  params={"text": "hello world"}),                 "process-成功")
    # 并行：3 个任务同时 execute，模拟 worker（在单测里做"小集成"）
    t0 = Task(type=TaskType.process,  params={"text": "a"})
    t1 = Task(type=TaskType.download, params={"url": "https://bad.com/a"})
    t2 = Task(type=TaskType.download, params={"url": "https://x.com/b"})
    await asyncio.gather(execute(t0), execute(t1), execute(t2))
    print("并行结果:", [t.status.value for t in (t0, t1, t2)])

#execute 是 async，而 await 只能写在 async 函数里，不能在文件顶层裸写 await。
# asyncio.run(main()) 新建一个事件循环 → 跑 main() → 结束后关掉它。
asyncio.run(main()) # async 代码的唯一入口



# [download-成功] status=done progress=100
#     message     = 正在下载 5/5 块…
#     result_path = output/eb821dd1-4795-46fb-bcd2-0b29b05ef6cd.txt
#     文件存在?    = True
#     文件内容    = '下载完成\nURL: https://example.com/file.bin\n分块数: 5\n'
# [download-失败] status=failed progress=60
#     message     = 执行失败：第 3/5 块下载失败(404):https://bad.example.com/x
#     result_path = None
# [process-成功] status=done progress=100
#     message     = None
#     result_path = output/6db70aff-fe75-4d9d-a7c0-1245986fe4ba.txt
#     文件存在?    = True
#     文件内容    = '输入: hello world\nMD5: 5eb63bbbe01eeed093cb22bb8f5acdc3\n'
# 并行结果: ['done', 'failed', 'done']