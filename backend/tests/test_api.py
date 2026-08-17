from pathlib import Path
import pytest # type: ignore
import time
from fastapi.testclient import TestClient # type: ignore
from app.main import app

def post_task(client, task_type, params) -> str:
  resp = client.post("/tasks", json={"type":task_type, "params":params})
  assert resp.status_code == 202, resp.text
  return resp.json()["task_id"]


def wait_for_status(client, task_id, target, timeout=5.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        task = client.get(f"/tasks/{task_id}").json()
        if task["status"] == target:
            return task
        time.sleep(0.1)
    raise AssertionError(f"任务 {task_id} 在 {timeout}s 内未到 {target}，最后: {task['status']}")


# 整个测试会话只用一个事件循环，queue 绑定一次，worker 从头跑到尾：
@pytest.fixture(scope="session")
def client():
  with TestClient(app) as c:   # with = 触发 lifespan = 启动 worker
      yield c                   # 测试用完自动清理 worker

# ============== 测试场景 ==============
# 1. 正常提交 and 查进度 (进行中)→ 200 + status/progress/message
# 2. 404（任务不存在）
# 3. 422（非法 type）
# 4. 取消已完成任务 → 409
# 5. 可取消时取消 → 200 cancelled
# 6. 并发冒烟：5~10 个任务全部 settle


def test_progress_during_run(client):
  tid = post_task(client, "download", {"url": "https://x/f.bin"})
  seen = []
  t0 = time.time()
  while time.time() - t0 < 5.0:            # 加 deadline 防死循环
    task = client.get(f"/tasks/{tid}").json()
    seen.append(task["progress"])
    if task["status"] == "done":
      break
    time.sleep(0.05)     # 0.3s/块 → 每块能被采样 6 次，不会漏中间值
  assert task["status"] == "done"        # 超时会在这里清晰报错
  assert task["progress"] == 100         # ① 最终到 100
  assert seen == sorted(seen)            # ② 进度单调不减（40→20 就说明逻辑坏了）
  assert any(0 < p < 100 for p in seen)  # ③ 过程中真的出现过 20/40/60/80


def test_404_not_found(client):
  tid = "00000000-0000-0000-0000-000000000000"
  resp = client.get(f"/tasks/{tid}")
  assert resp.status_code == 404          # → 协议层：HTTP 语义（传输/浏览器/curl 都靠它）
  body = resp.json()
  assert body["code"] == 404              # → 应用层：我们自己约定的 {code, message} 格式
  assert isinstance(body["message"], str)


def test_invalid_type(client):
  resp = client.post("/tasks", json={"type": "invalid_type", "params": {"url": "https://x/slow.bin"}})
  assert resp.status_code == 422
  assert resp.json()["code"] == 422       # 统一错误格式


def test_cancel_conflict(client):
  tid = post_task(client, "process", {"text": "hi"})
  wait_for_status(client, tid, "done")
  resp = client.delete(f"/tasks/{tid}")
  assert resp.status_code == 409
  assert resp.json()["code"] == 409
  task = client.get(f"/tasks/{tid}").json()
  assert task["status"] == "done"      # 409 = 状态机拒绝 → 状态不变


def test_cancel_pending(client):
  tid = post_task(client, "process", {"text": "hi"})
  resp = client.delete(f"/tasks/{tid}")
  assert resp.status_code == 200
  assert resp.json()["status"] == "cancelled"
  task = wait_for_status(client, tid, "cancelled")   # 最终状态保持 cancelled（execute ④守卫）
  assert not (Path(__file__).resolve().parent.parent / "output" / f"{tid}.txt").exists()


def test_concurrent_smoke(client):
  tids = []
  for i in range(8):
    if i % 2 == 0:
      tids.append(post_task(client,"download", {"url": f"https://example.com/f{i}.bin"}))
    else:
      tids.append(post_task(client,"process", {"text": f"text-{i}"}))
  for i in range(8):
    task = wait_for_status(client, tids[i], "done")
    assert task["progress"] == 100
