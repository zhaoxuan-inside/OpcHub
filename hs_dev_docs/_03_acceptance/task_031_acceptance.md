# 任务验收备忘：TASK-031 服务器交付版编排（自建 pg/redis + 镜像包）

- **任务编号**：TASK-031
- **任务标题**：交付自建 pgsql/redis 的 compose 与前后端镜像包（用户自行上传服务器启动）
- **分级**：`S`
- **执行人**：agent
- **完成时间**：`2026-10-25T19:10:00+08:00`
- **状态**：`VERIFIED_AND_ACCEPTED`

---

## 1. 需求澄清与最终部署模型

用户最终明确：目标为**远程服务器**，由用户自行上传镜像；compose 在服务器上**自建** PostgreSQL 与 Redis 并启动四服务（推翻 TASK-030 后临时尝试的"直连宿主机 pgsql-18"方案，该方案的网络连接、.env 派生串已全部回退）。

## 2. 交付产物

1. **`docker-compose.yml`（服务器运行版）**：
   - 四服务：`backend` / `frontend`（仓库构建的镜像）/ `postgres`（pgvector/pgvector:pg18）/ `redis`（redis:8-alpine），同一 `opchub-net` 网络，服务名互访。
   - **纯镜像、无 build 段**——服务器无需源码，`docker load` 后 `up -d` 即可；重建镜像命令写在文件头注释。
   - pg/redis 不发布宿主端口（安全默认，管理用途的 ports 段以注释形式内置）；`./backend/config` 挂载默认注释（服务器无 checkout，路由 YAML 已烘焙进镜像）。
   - `DATABASE_URL` 支持 `OPCHUB_DATABASE_URL` 整体串覆盖（密码含特殊字符时用），默认由 `OPCHUB_PG_*` 拼装。
2. **`deploy/` 交付包**（gitignore，本机产物）：
   - `opchub-images.tar.gz`（93MB，`docker save` 双镜像 + gzip，`gzip -t` 校验通过）
   - `docker-compose.yml` / `.env.example`（与仓库同步的副本）
   - `README.md` 服务器 runbook：load → 配 .env → up → 健康检查；离线服务器的 pg/redis 镜像导出命令；数据卷与升级说明。
3. **`.env.example` 更新**：`BACKEND_PORT` / `FRONTEND_PORT` 与 `OPCHUB_PG_*` 凭据段（含密码 URL 安全字符约束与整体连接串示例）。

## 3. 验证（BACKEND_PORT=18000 FRONTEND_PORT=13000，全新卷）

- `docker compose up -d` 四容器全部 healthy。
- 全新 initdb 自举：21 张表 + 管理员引导（users=1）+ 种子持久化，`home.overview` 网关 200，`/console` 200。
- 中间方案回退干净：`opchub-infra` 网络已删、pgsql-18 连接已断、`.env` 派生串已移除、pgsql-18 数据未受影响（10 用户基线不变）。

## 4. 遗留观察

- 后端 DB 不可达静默回退内存模式的风险仍未治理（TASK-030 遗留），服务器首次部署后建议按 runbook 检查 `docker compose ps` 与 `/health` 之外，再抽查库中表数量确认真实落库。
