# 架构说明（ARCHITECTURE）

> 本文档记录项目的目录结构、核心概念、数据流和扩展方式。

---

## 一、项目定位

**异步文件处理平台** 是一个支持异步任务提交、进度查询、历史管理的全栈应用。

核心设计目标：**通用异步任务引擎可剥离、可复用**。
- `backend/fastapi_async_lib/` 是零业务依赖的通用引擎。
- `backend/app/` 是业务层，通过适配器与引擎通信。

---

## 二、技术栈

| 层级 | 技术 | 说明 |
| :--- | :--- | :--- |
| 后端框架 | FastAPI + Uvicorn | 异步 Web 框架 |
| ORM | SQLModel + SQLAlchemy | 数据库映射 |
| 数据库 | SQLite | 开发环境用；生产可换 PostgreSQL |
| 异步队列 | asyncio.Queue + Worker 协程 | 单进程内任务调度 |
| 文件存储 | 本地 `data/uploads/` + `data/output/` | 后续可接 S3 |
| 前端框架 | React + TypeScript + Vite | 组件化开发 |
| UI 组件 | Shadcn + Tailwind CSS | 设计系统 |
| HTTP 客户端 | axios | 封装统一错误处理 |
| 部署 | Docker + Docker Compose | 一键启动 |

---

## 三、后端分层架构（五层）

| 层 | 目录 | 职责 | 依赖方向 |
| :--- | :--- | :--- | :--- |
| ① 契约层 | `fastapi_async_lib/schemas/` | 定义 `BaseTask` 协议 | 无依赖 |
| ② 通用引擎层 | `fastapi_async_lib/engine/` | 队列、Worker、状态机 | 仅依赖契约层 |
| ③ 适配层 | `app/adapters/` | 将业务模型适配为引擎协议 | 依赖 ① + `app/models` |
| ④ 业务层 | `app/plugins/` | 具体业务执行器（download/process） | 依赖 `app/models` |
| ⑤ 集成层 | `app/core/engine.py` | 依赖注入，组装一切 | 依赖 ②③④ |
| ⑥ 入口层 | `app/routers/` | HTTP 接口 | 依赖 ⑤ |

**核心原则**：`fastapi_async_lib` 完全不导入 `app/`，两者通过 `BaseTask` 协议解耦。

---

## 四、核心概念

### 1. 任务（Task）
数据库中的一行记录，包含：
- `id`：UUID 主键
- `type`：`download` / `process`
- `params`：任务参数（JSON）
- `status`：`pending` / `running` / `done` / `failed` / `cancelled`
- `progress`：0~100
- `message`：当前状态描述
- `result_path`：结果文件路径（成功后）

### 2. 队列（QueueManager）
封装 `asyncio.Queue`，单进程内存队列。
- `put(task)`：入队
- `get(timeout=1.0)`：出队
- `task_done()`：标记处理完成

未来可替换为 Redis，只需重写 `QueueManager`，Worker 无感知。

### 3. Worker（worker.py）
一个异步协程，从队列取任务并执行：
1. 从队列取出任务
2. 从数据库读取最新状态
3. 用状态机锁定为 `running`
4. 调用业务执行器（通过注册表获取）
5. 根据结果置为 `done` / `failed` / `cancelled`

Worker **不关心** 具体业务逻辑，只负责调度。

### 4. WorkerPool（worker_pool.py）
管理 N 个 Worker 协程的启动/停止。项目启动时创建 2 个 Worker。

### 5. 状态机（state_machine.py）
校验状态转换合法性。

合法转换：
```
pending → running, cancelled
running → done, failed, cancelled
终态（done/failed/cancelled）→ 不可再转
```

任何非法转换都会抛出 `TransitionError`。

### 6. 适配器（TaskAdapter）
将 SQLModel 的 `Task` 模型包装成引擎认识的 `BaseTask` 协议：

```python
class TaskAdapter:
    def __init__(self, task: Task, db: Session): ...
    @property
    def id(self) -> str: ...
    @property
    def status(self) -> BaseTaskStatus: ...
    def update_status(self, status, message): ...
    def update_progress(self, progress, message): ...
```

### 7. 插件注册表（registry.py）
维护任务类型到执行器的映射：

```python
RUNNERS = {
    "download": run_download,
    "process": run_process,
}
```

新增任务类型时，只需注册新执行器，引擎层零改动。

---

## 五、数据流（提交任务）

```
用户点击「提交任务」
    │
    ▼
前端 POST /tasks/ (TaskCreate)
    │
    ▼
routers/tasks.py: submit_task()
    ├─ 创建 Task 记录，状态 pending
    ├─ db.commit()
    └─ submit_task_to_queue(task)
         │
         ▼
    QueueManager.put(task)  ──► 队列
                                  │
                                  ▼
                        Worker 取出任务
                                  │
                                  ▼
                        状态机: pending → running
                                  │
                                  ▼
                        registry.get(type) → runner
                                  │
                                  ▼
                     run_download / run_process
                                  │
                          （协作式取消检查点）
                                  │
                                  ▼
                        状态机: running → done/failed
                                  │
                                  ▼
                        前端轮询 GET /tasks/ 看到结果
```

---

## 六、如何新增一种任务类型

以新增 `compress`（压缩）任务为例：

### 步骤 1：编写执行器 `app/plugins/compress.py`

```python
import asyncio
from sqlmodel import Session
from app.models import Task, TaskStatus
from app.core.config import OUTPUT_DIR

async def run_compress(task: Task, db: Session) -> None:
    file_path = task.params.get("file_path")
    if not file_path:
        raise ValueError("缺少 file_path")

    task.progress = 10
    task.message = "准备压缩..."
    db.commit()

    await asyncio.sleep(1)

    db.refresh(task)
    if task.status == TaskStatus.cancelled:
        return

    result_path = OUTPUT_DIR / f"{task.id}.zip"

    task.progress = 100
    task.message = "压缩完成"
    task.result_path = str(result_path)
    db.commit()
```

### 步骤 2：注册执行器 `app/plugins/registry.py`

```python
from app.plugins.compress import run_compress

RUNNERS = {
    "download": run_download,
    "process": run_process,
    "compress": run_compress,   # ← 新增一行
}
```

### 步骤 3：前端添加选项

在 `frontend/src/components/TaskForm.tsx` 的 `RadioGroup` 中添加：

```tsx
<div className="flex items-center gap-2">
  <RadioGroupItem value="compress" id="compress" />
  <Label htmlFor="compress" className="cursor-pointer">Compress</Label>
</div>
```

### 步骤 4：后端类型定义（可选）

在 `app/models.py` 的 `TaskType` 枚举中添加 `compress`。

完成！**引擎层、路由层、队列层完全不需要修改**。这就是插件化架构的威力。

---

## 七、关键设计决策

### 1. 为什么用 asyncio.Queue 而不是 Redis？
- 当前是单机部署，内存队列开销最小。
- `QueueManager` 已抽象，未来切换 Redis 只需替换实现。

### 2. 为什么用状态机而不是 if/else？
- 状态转换规则集中管理，避免业务代码中散落 `if status == ...`。
- 添加新状态只需修改状态机配置，不影响已有代码。

### 3. 为什么用适配器而不是让引擎直接依赖 Task？
- 引擎（`fastapi_async_lib`）要能复用到其他项目。
- 如果引擎直接 `import app.models.Task`，就无法剥离。
- 适配器让业务模型与引擎协议彻底分离。

### 4. 为什么用协作式取消而不是强杀 Worker？
- Python 的 asyncio 无法安全强杀协程（会泄漏资源）。
- 业务执行器在关键检查点主动检查 `task.status == cancelled`，自行清理退出。
- 这是业界标准做法。

### 5. 为什么前端用 Nginx 而不是 Vite Preview？
- Nginx 是生产级静态文件服务器。
- 支持 SPA 路由重定向、缓存控制、Gzip。
- Vite Preview 仅用于开发调试。

---

## 八、可复用资产清单

如果要在新项目中使用本引擎，只需复制：

- `backend/fastapi_async_lib/`（整个目录）
- 编写新的 `Adapter` 和 `Plugin`
- 参考 `app/core/engine.py` 进行依赖注入

`fastapi_async_lib` 不依赖任何第三方业务代码，可独立运行。

---

## 九、测试策略

### 后端测试（pytest）

| 文件 | 类型 | 覆盖 |
| :--- | :--- | :--- |
| `test_state_machine.py` | 单元 | 状态机转换合法性 |
| `test_registry.py` | 单元 | 注册表增删查 |
| `test_task_adapter.py` | 单元 | 适配器属性映射 |
| `test_data_layer.py` | 单元 | 数据层 CRUD |
| `test_api.py` | 集成 | 完整任务生命周期 + 取消 |

运行：`cd backend && uv run pytest tests/ -v`

### 前端测试（Vitest + RTL）

| 文件 | 覆盖 |
| :--- | :--- |
| `App.test.tsx` | 根组件：轮询、状态管理 |
| `TaskForm.test.tsx` | 表单：上传、提交、切换 |
| `TaskItem.test.tsx` | 单条任务渲染 |
| `TaskList.test.tsx` | 列表渲染与空状态 |
| `ProgressCard.test.tsx` | 进度卡片 |
| `CancelTaskButton.test.tsx` | 取消弹窗交互 |

运行：`cd frontend && npm run test`

---

## 十、未来演进方向

| 方向 | 改动 |
| :--- | :--- |
| 换成 PostgreSQL | 修改 `DATABASE_URL`；`CheckConstraint` 语法兼容 |
| 换 Redis 队列 | 重写 `QueueManager`，保持接口一致 |
| 分布式 Worker | `fastapi_async_lib` 可独立部署到多台机器 |
| 对象存储 | `upload`/`output` 替换为 S3/MinIO SDK |
| 认证鉴权 | 路由层加 `Depends(get_current_user)` |
| 前端 SSR | 替换 Vite 为 Next.js |