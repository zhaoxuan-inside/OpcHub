# UUID 身份体系迁移（2026-10-28）

> 目标：PostgreSQL 中所有表的主键/外键 `id`、`*_id` 列统一为 `uuid`。
> 原则：**数据库身份用 UUID，人类可读编码用 code / key / handle，不再占用 `*_id` 列名。**

---

## 1. 契约

```sql
-- 任何列名为 id 或以 _id 结尾的列，data_type 必须是 uuid
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND (column_name = 'id' OR column_name LIKE '%\_id')
  AND data_type <> 'uuid';
-- 期望 0 行
```

业务编码映射：

| 原列 | 新列 | 类型 |
|---|---|---|
| `users.uid` | `users.handle` | varchar（账号句柄） |
| `entitlements.id`（业务码） | `entitlements.code` | varchar，唯一 |
| `entitlements.id`（身份） | `entitlements.id` | uuid，PK |
| `sop_templates.id`（业务码） | 保留 `sop_templates.code` | varchar，唯一 |
| `sop_templates.id`（身份） | `sop_templates.id` | uuid，PK |
| `domain_snapshots.entity_id` | `domain_snapshots.entity_key` | varchar |
| `domain_snapshots` 身份 | 新增 `id` | uuid，PK |
| `rag_vectors.doc_id` | `rag_vectors.doc_key` | varchar |
| `rag_vectors` 身份 | 新增 `id` | uuid，PK |
| `audit_logs.actor_id` | `actor_uid` | varchar |
| `audit_logs.resource_id` | `resource_key` | varchar |
| `audit_logs.trace_id` | `trace_code` | varchar |
| `content_moderation_logs.target_id` | `target_key` | varchar |
| `content_moderation_logs.author_id` | `author_uid` | varchar |
| `content_moderation_logs.moderator_id` | `moderator_uid` | varchar |

所有 UUID `id` 列都带数据库默认值：

```sql
DEFAULT gen_random_uuid()
```

## 2. 产物

| 文件 | 用途 |
|---|---|
| `backend/sql/schema_uuid.sql` | 全新数据库的完整 DDL（21 张表、索引、约束） |
| `backend/sql/migrate_uuid_ids_20261028.sql` | 已有数据库的一次性迁移 |
| `backend/sql/README.md` | 执行说明与验证 SQL |
| `backend/tests/test_postgresql_pgvector_persistence.py::test_every_id_column_is_uuid` | 元数据层强制契约 |

## 3. 迁移执行记录

```bash
# 1. 备份
docker exec opchub-postgres pg_dump -U opc -d opchub > opchub_before_uuid.sql

# 2. 迁移
docker exec -i opchub-postgres psql -U opc -d opchub -v ON_ERROR_STOP=1 \
  < backend/sql/migrate_uuid_ids_20261028.sql

# 3. 校验
SELECT ... -- 见第 1 节，0 行
```

迁移后实测：

- 20 张表的 UUID `id` 全部有 `gen_random_uuid()` 默认值；
- 41 个 `id` / `*_id` 列全部为 `uuid`；
- `admin@opchub.cn` 登录成功；
- 后端容器健康；
- 全量测试：478 passed / 5 skipped / 2 个既有基线失败（docker-compose 旧断言、hot-reload 基线）。

## 4. 边界说明

这次改的是**数据库身份层**。领域服务对外返回的业务键（如 `pol_...`、`perk_...`、`tpl_...`）仍然保留在 `entity_key` / payload 中，以兼容现有 API、前端路由与历史数据。

如果还要求**API / 前端 URL 中的实体 ID 也全部替换为 UUID**，需要第二阶段：

1. 领域服务生成 `uuid4` 作为实体 ID；
2. seed/fixture 全部改为 UUID；
3. 前端路由参数、测试断言、历史数据做映射迁移；
4. `entity_key` 与 UUID 建立双向别名表，避免旧链接失效。
