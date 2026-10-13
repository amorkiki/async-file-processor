# 部署指南（DEPLOY）

> 本指南面向本地开发环境，使用 Docker + Docker Compose 一键启动整个项目。

---

## 一、前置条件

在开始之前，请确保你的机器已安装以下工具：

| 工具 | 最低版本 | 检查命令 | 安装地址 |
| :--- | :--- | :--- | :--- |
| **Docker Desktop** | 24.0+ | `docker --version` | https://www.docker.com/products/docker-desktop |
| **Docker Compose** | v2.20+ | `docker compose version` | 随 Docker Desktop 一起安装 |
| **Git** | 2.30+ | `git --version` | https://git-scm.com/ |

> ⚠️ **不需要**宿主机安装 Python/Node/uv/npm”仅针对启动和运行应用；若要执行测试或本地开发，需安装对应工具，或使用容器内测试命令。

---

## 二、快速启动（3 步）

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd async-file-processor
```

### 2. 启动所有服务

```bash
docker compose up -d --build
```

首次构建需要 3~5 分钟（下载基础镜像 + 安装依赖），之后会走缓存，几秒即可完成。

### 3. 访问应用

| 服务 | 地址 | 说明 |
| :--- | :--- | :--- |
| **前端页面** | http://localhost:3000 | 主界面 |
| **后端 API 文档** | http://localhost:8000/docs | Swagger UI |
| **后端健康检查** | http://localhost:8000/ | 返回服务状态 |

---

## 三、项目结构

```
async-file-processor/
├── docker-compose.yml          # 多容器编排
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/                    # 业务代码
│   └── fastapi_async_lib/      # 通用异步引擎（可复用）
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
└── data/                       # 数据持久化目录（自动生成）
    ├── app.db                  # SQLite 数据库
    ├── uploads/                # 用户上传的文件
    └── output/                 # 任务处理结果
```

---

## 四、环境变量说明

所有环境变量已在 `docker-compose.yml` 中配置好，无需手动设置。如需修改，编辑该文件后重新 `docker compose up -d`。

| 变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///data/app.db` | 数据库连接字符串 |
| `WORKER_COUNT` | `3` | 后台 Worker 协程数量 |
| `VITE_API_URL` | `http://localhost:8000` | 前端请求后端的地址（构建时注入） |

> ⚠️ **修改 `VITE_API_URL` 后必须重新构建前端镜像**（`docker compose up -d --build frontend`），因为 Vite 环境变量在构建时被编译进代码。
> ⚠️ 后端 CORS 白名单在 backend/app/main.py 中配置。如果修改了前端端口（如从 5173 改为 3000），必须同步更新 allow_origins，否则浏览器会拦截请求。
---

## 五、数据持久化

项目使用 **bind mount** 将容器内 `/app/data` 映射到宿主机 `./data` 目录。`docker-compose.yml` 中对应配置为：

```yaml
volumes:
  - ./data:/app/data
```

- **数据库、上传文件、处理结果** 全部保存在 `./data` 下。
- **容器删除后，数据不会丢失**。
- 如果要彻底清空数据，删除 `./data` 目录即可。 `rm -rf ./data`


---

## 六、常用运维命令

```bash
# 启动所有服务（后台）
docker compose up -d

# 重新构建并启动
docker compose up -d --build

# 查看运行状态
docker compose ps

# 查看实时日志
docker compose logs -f

# 只看后端日志
docker compose logs -f backend

# 重启某个服务
docker compose restart backend

# 进入容器内部（调试用）
docker exec -it async-processor-backend bash

# 停止并删除容器（bind mount 数据保留）
docker compose down

# 对 bind mount 来说，-v 不会删除 ./data；要清空需手动删目录
docker compose down -v
rm -rf ./data
```

---

## 七、从 0 到 1 完整复现流程（验收清单）

- [ ] 安装 Docker Desktop
- [ ] `git clone` 项目
- [ ] `docker compose up -d --build`
- [ ] 访问 `http://localhost:3000`，看到「异步文件处理平台」
- [ ] 上传一个 `.txt` 文件，选择 Process，提交任务
- [ ] 观察进度条从 0% → 100%
- [ ] 访问 `http://localhost:8000/docs`，测试 `GET /tasks/` 接口
- [ ] 重启容器 `docker compose restart`，确认数据仍然存在

全部通过 ✅ 即代表部署成功。

---

## 八、卸载

```bash
# 停止并删除容器
docker compose down

# 删除所有相关镜像（可选）
docker rmi async-file-processor-backend async-file-processor-frontend

# 删除数据（可选）
rm -rf ./data
```