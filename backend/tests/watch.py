import json
import time
import urllib.request

BASE = "http://127.0.0.1:8000"

def post_task(task_type: str, params: dict) -> str:
    body = json.dumps({"type": task_type, "params": params}).encode()
    req = urllib.request.Request(f"{BASE}/tasks", data=body,
                                 headers={"Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["task_id"]

def get_task(task_id: str) -> dict:
    with urllib.request.urlopen(f"{BASE}/tasks/{task_id}") as resp:
        return json.load(resp)

cases = [
    ("download", {"url": "https://example.com/file.bin"}),
    ("download", {"url": "https://bad.example.com/x"}),     # 失败演示
    ("process",  {"text": "hello world"}),
]

# ① 提交 3 个任务
ids = [post_task(t, p) for t, p in cases]
print("已提交:", [i[:8] for i in ids])

# ② 疯狂轮询 6 秒，每 0.3 秒打印一次三个任务的快照
start = time.time()
while time.time() - start < 6: 
    snaps = []
    for tid in ids:
        t = get_task(tid)
        msg = (t.get("message") or "")[:16] # 防御 + 截断（message 可能是 None（比如旧任务），取不到就用空串——防止打印 None 刷屏）
        # t['status'][:1]：只取状态首字母（r/d/f），列窄
        # t['progress']:>3：右对齐占 3 位，进度整齐
        snaps.append(f"{t['status'][:1]} {t['progress']:>3}% {msg}")   # 快照格式：如 r  40%  正在下载 2/5 块…
    print(f"{time.time()-start:>4.1f}s  " + "   ".join(snaps))
    time.sleep(0.3)