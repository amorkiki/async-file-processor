# Async File Processor

异步文件处理平台 —— 支持任务提交、实时进度、历史管理、任务取消。

## ✨ 特性

- 🚀 异步任务引擎（可复用，位于 `backend/fastapi_async_lib/`）
- 📊 实时进度轮询
- 🧩 插件化任务类型（download / process，可扩展）
- 🎯 状态机驱动的生命周期管理
- 🐳 Docker 一键部署
- ✅ 前后端完整测试覆盖

## 🚀 快速开始

```bash
git clone <your-repo-url>
cd async-file-processor
docker compose up -d --build
```

访问 http://localhost:3000

## 📚 文档

- [部署指南](./DEPLOY.md)
- [架构说明](./ARCHITECTURE.md)

## 🛠️ 技术栈

| 后端 | 前端 | 部署 |
| :--- | :--- | :--- |
| FastAPI + SQLModel | React + Vite | Docker Compose |
| asyncio.Queue | Shadcn + Tailwind | Nginx |
| SQLite | Vitest + RTL | Python 3.11 |

## 📖 目录结构

（见 ARCHITECTURE.md）

## 🧪 测试

```bash
# 后端
cd backend && uv run pytest tests/ -v

# 前端
cd frontend && npm run test
```

## 📄 License

MIT