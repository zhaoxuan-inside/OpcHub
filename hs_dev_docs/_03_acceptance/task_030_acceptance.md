# 任务验收备忘：TASK-030 前后端 Docker 镜像与四服务 Compose 编排

- **任务编号**：TASK-030
- **任务标题**：前后端分别打包 Docker 镜像，docker compose 管理 backend/frontend/postgres/redis 四服务
- **分级**：`M`
- **执行人**：agent
- **完成时间**：`2026-10-25T18:55:00+08:00`
- **状态**：`VERIFIED_AND_ACCEPTED`

---

## 1. 交付产物

1. **`Dockerfile`（后端镜像 `opchub-backend:latest`，355MB）**：
   - 修复原硬编码 pip 清单缺 `asyncpg/pgvector/alembic/greenlet/pydantic-settings` 的问题——改为 `pip install /build/backend`，依赖严格来自 `backend/pyproject.toml`。
   - 全部依赖走 cp312 manylinux 预编译 wheel，**删除 build-essential 编译环节**（国内网络下 apt 直连 debian 源下载 82MB 需 30 分钟以上）。
   - `ARG PIP_INDEX_URL`（默认清华源）；非 root 用户 `opc`(10001)；`/health` 原生 Python healthcheck。
2. **`frontend/Dockerfile`（前端镜像 `opchub-frontend:latest`，254MB）**：
   - Stage 1 `node:20-slim`：`npm ci` + `vite build` 产出 dist（`ARG NPM_REGISTRY` 默认 npmmirror）。
   - Stage 2 `python:3.12-slim`：复用 `frontend/server.py`（静态服务 + `/api` 反向代理到 `backend:8000`），非 root，`/health` healthcheck。
3. **`docker-compose.yml` 重写为四服务**：`backend` / `frontend` / `postgres`(pgvector/pgvector:pg18，与宿主机既有 pgsql-18 同版本) / `redis`(redis:8-alpine，同 redis-8)，统一 `opchub-net` 桥接网络，服务名互访；`pgdata`/`redisdata`/`appdata` 具名卷持久化；`backend/config` 只读挂载支持路由 YAML 热更新；端口 `BACKEND_PORT`/`FRONTEND_PORT` 可覆盖。
4. **`.dockerignore` 修订**：`**/node_modules`、`**/dist` 通配（根目录级模式匹配不到 `frontend/node_modules`，曾致 36MB 上下文在 hgfs 上传输数十分钟）；排除运行时 SQLite 但**保留 `backend/data/seeds/`**——种子 JSON 是启动引导持久化的数据源，曾误排除会导致空库空平台。
5. **凭据解耦**：compose 内数据库凭据改用 `OPCHUB_PG_*` 变量前缀。根目录开发用 `.env` 的 `POSTGRES_*`（用户 `opchub`、密码含 `@`）会被 compose 自动读取并破坏 `DATABASE_URL` 插值，导致后端静默回退内存模式（表面正常、实际零持久化）——已通过隔离变量名根除。

## 2. 关键判定：数据库使用 PostgreSQL 而非 MySQL

需求原话为 "mysql"，但平台数据层深度绑定 PostgreSQL：`models.py` 50 处 `JSONB`/PG 方言 `UUID`、`pgvector Vector(128)` 向量列与 HNSW 余弦检索、asyncpg 驱动。迁 MySQL 属独立移植工程。且宿主机既有数据库容器 `pgsql-18` 即 `pgvector/pgvector:pg18`——"同主机的其他 docker 容器"实为 PostgreSQL。故 compose 数据库采用 `pgvector/pgvector:pg18`，与代码栈及既有容器一致。Redis 平台暂未消费，按需求作为基础设施就绪位纳管。

## 3. 验证（BACKEND_PORT=18000 FRONTEND_PORT=13000）

- `docker compose up -d` 四容器全部 healthy。
- 后端 `/health` 200（kernel_operators_count=116）；前端 `/health` UP、`/console` 返回标题、assets 200（716KB）。
- 前端 → 后端网关代理：`POST /api/welcom/opc_world (home.overview)` 200。
- 后端 → PostgreSQL：21 张表建表、`vector` 扩展安装、管理员 `admin@opchub.cn` 引导落库、种子数据持久化（此前失败尝试时库中 0 表，证实修复生效）。
- Redis `redis-cli ping` PONG；`docker compose down -v` 仅清理本项目卷，不影响宿主机既有 `pgsql-18`/`redis-8`。

## 4. 遗留观察

- 后端在数据库不可达时**静默回退内存模式**，无显式告警——生产环境存在零持久化风险，建议单列任务在启动时对 DB 连接失败 fail-fast 或至少打出 ERROR 级横幅。
- `:8000/console`（后端直出 HTML 无 /assets 路由）白屏问题仍在（TASK-029 遗留观察）；compose 部署下请统一走前端端口。
