# 一体化验证：并发压测 + 取消 + 错误格式
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE = "http://127.0.0.1:8000"
OUTPUT_DIR = Path("output")


def post_task(task_type: str, params: dict) -> str:
    body = json.dumps({"type": task_type, "params": params}).encode()
    req = urllib.request.Request(
        f"{BASE}/tasks/",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["task_id"]


def get_task(task_id: str) -> dict:
    with urllib.request.urlopen(f"{BASE}/tasks/{task_id}") as resp:
        return json.load(resp)


def delete_task(task_id: str) -> tuple[int, dict]:
    req = urllib.request.Request(f"{BASE}/tasks/{task_id}", method="DELETE")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:  # 409/404 也要能读到错误体
        return e.code, json.load(e)


def check(name: str, ok: bool, detail: str = ""):
    print(f"  {'✅' if ok else '❌'} {name}  {detail}")


# ========== 1. 并发压测：8 个任务同时提交 ==========
print("== 1. 并发压测 ==")
ids = []
for i in range(8):
    if i % 2 == 0:
        ids.append(post_task("download", {"url": f"https://example.com/f{i}.bin"}))
    else:
        ids.append(post_task("process", {"text": f"text-{i}"}))
print(f"  已提交{len(ids)} 个：", [i[:8] for i in ids])

t0 = time.time()
settled = False
while time.time() - t0 < 15:
    states = [get_task(i)["status"] for i in ids]
    n = sum(s in ("done", "failed") for s in states)
    print(f"  {time.time()-t0:>4.1f}s  完成 {n}/8  " + " ".join(s[:1] for s in states))
    if n == 8:
        settled = True
        break
    time.sleep(0.3)

check("8 个任务全部 settle（不崩、不卡）", settled)
check(
    "所有成功任务产出文件",
    all((OUTPUT_DIR / f"{i}.txt").exists() for i in ids),
    f"output/ 应有 {len(ids)} 个文件",
)


# ========== 2. 取消验证 ==========
print("\n== 2. 取消验证 ==")
# tid = post_task("download", {"url": "https://example.com/slow.bin"})
tid = post_task("process", {"text": "xiao-bao"})
time.sleep(0.2)
st, body = delete_task(tid)
print(f"  DELETE running/pending 任务 → {st} {body}")
for _ in range(15):
    t = get_task(tid)
    if t["status"] == "cancelled":
        break
    time.sleep(0.3)

check("取消后最终状态为 cancelled", t["status"] == "cancelled", f"实际 {t['status']}")
check("取消的任务没有产出文件", not (OUTPUT_DIR / f"{tid}.txt").exists())


# 2b: 取消已完成任务 → 409
tid2 = post_task("process", {"text": "quick"})
while get_task(tid2)["status"] not in ("done", "failed"):
    time.sleep(0.2)
st2, body2 = delete_task(tid2)
check("取消 done 任务 → 409", st2 == 409, f"实际 {st2} {body2}")
check("409 是统一错误格式", "code" in body2 and "message" in body2, str(body2))

# 2c: 取消不存在任务 → 404
st3, body3 = delete_task("00000000-0000-0000-0000-000000000000")
check("取消不存在任务 → 404", st3 == 404, f"实际 {st3} {body3}")
check("404 是统一错误格式", "code" in body3 and "message" in body3, str(body3))


# 2d: 取消 running 的 process 任务（覆盖 process 类型的取消路径）
tid4 = post_task("process", {"text": "slow-process"})
time.sleep(0.2)  # 让它进到「读取」阶段
st4, body4 = delete_task(tid4)
print(f"  DELETE running process 任务 → {st4} {body4}")
for _ in range(15):
    t4 = get_task(tid4)
    if t4["status"] == "cancelled":
        break
    time.sleep(0.3)
check(
    "取消的 process 任务最终为 cancelled",
    t4["status"] == "cancelled",
    f"实际 {t4['status']}",
)
check("取消的 process 任务没有产出文件", not (OUTPUT_DIR / f"{tid4}.txt").exists())
