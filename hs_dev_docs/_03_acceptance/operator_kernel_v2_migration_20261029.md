# 算子内核 v2 全量迁移验收（2026-10-29）

> 目标：后端业务统一为「业务无关算子 + 场景 YAML 编排」，算子单一职责。
> 规范：`hs_dev_docs/_03_architecture_design/_03_detailed_design/_06_operator_kernel_v2.md`

## 1. 分层结果

```
Gateway (config/gateway_routes.yaml)
  └── pipeline: OPC_xxx                  # 路由只声明场景，不再 import service
        └── config/scenarios/*.yaml      # 业务编排（唯一业务真相）
              └── Operator               # core/operators + domains/*/functions
                    └── EntitySpec       # domains/*/entities.py
```

- 通用算子：`guard.*` / `validate.*` / `transform.*` / `entity.*` / `notify.*` / `audit.*` / `metric.*` / `render.*` / `external.*` / `response.*`
- 领域算子：仅 `calc.*` / `assemble.*` / `policy.*` 单职责纯函数
- 控制面：`src/domains/orchestration/control_ops.py`（目录、DAG 保存）独立于业务算子内核

## 2. 迁移清单

| 域 | 实体 | 场景 | 路由映射 |
|---|---|---|---|
| products | `product.item` | 3 | `config/routes/`（内联） |
| policies | `policy.item` | 3 | policies.yaml |
| demands | `demand.item` / `demand.bid` | 7 | demands.yaml |
| perks | `perk.item` / `perk.claim` | 8 | perks.yaml |
| compliance | `compliance.item` | 5 | compliance.yaml |
| moderation | `moderation.item` | 6 | moderation.yaml |
| forum | thread/answer/comment/vote/follow/tombstone | 14 | forum.yaml |
| sop | 9 个实体 | 23 | sop.yaml |
| loyalty | account/ledger/membership/order/item | 14 | loyalty.yaml |
| interactions | stat/record/comment/rating | 9 | interactions.yaml |
| notifications | notification.item / inbox | 6 | notifications.yaml |
| user | account/captcha/code/rate-limit/entitlement | 3 | user.yaml |
| auth | 同上 | 10 | auth.yaml |
| external | — | 7 | external.yaml |
| framework | — | 5 | framework.yaml |
| telemetry/home | — | 2 | telemetry.yaml / home.yaml |
| orchestration | 控制面 | 3 | 直连控制面（豁免） |

## 3. 引擎能力

- 节点 `params` / `inputs_map` / `when` / `output_key`
- 拓扑分层并行（同层节点 `asyncio.gather`）
- Saga 逆序补偿；`entity.create` 自动注册删除补偿
- 安全表达式求值（无函数调用/无属性写入）
- 网关统一 `pipeline:` 执行；`response` 或主结果键自动解包
- 动态实体名（`entity` 可由节点输出传入），避免为多态目标新增业务算子

## 4. 合规校验

- `tests/test_operator_contract.py`：
  1. 通用算子不得 import `src.domains`
  2. 通用算子命名必须属于通用前缀
  3. 领域 `functions.py` 不得 I/O、跨域 import、调用编排
  4. 场景资产单入口/单出口且算子已注册
- 所有领域新增 `tests/test_<domain>_operator_flows.py`，覆盖写场景成功与关键失败。

## 5. 迁移中修复的缺陷

1. **论坛列表/feed 网关解包**：`feed` 加入统一解包键，`forum.threads.list` / `forum.feed.stream` 恢复正确结构。
2. **实体不存在语义**：`entity.get` 保持 `KeyError → 404`；场景层不得吞掉。
3. **legacy 索引遮蔽**：moderation / perks 兼容视图改为 entity store 优先，写入后旧缓存不再覆盖权威文档。
4. **SOP 互动计数**：`SOP_DOCUMENT → sop.node`、`SOP_FLOW → sop.flow_template`，恢复喜欢/收藏计数回写。
5. **blocklist 拦截回执**：声明式关键词拦截同样写入 `notification.item` 的 `BLOCKED` 回执。
6. **管理员代发归属**：products/policies/demands/perks/compliance/forum 统一支持 ADMIN 指定 `author_id/author_name`，普通用户仍强制 context 身份。
7. **错误语义**：引擎向网关透传 `error_type`，`KeyError` 恢复为 404（论坛详情/投票目标/SOP 文书不存在等），并清理引擎节点前缀与引号。
8. **数据库兼容闸门**：启动时探测 `users.handle` / `domain_snapshots.entity_key`；旧 schema 下自动禁用持久化并输出迁移命令，算子内核仍可内存启动。

## 6. 已知边界

1. **内容审核**：`guard.moderation` 组合本地 NLP 预筛与外部审核网关；发布场景可声明 `blocklist` 做确定性关键词拦截。外部服务不可用时按 fail-open 降级。
2. **Feed 缓存**：算子内核 v2 移除 feed 缓存，排序/游标由纯函数计算；响应保留 `cache_hit=false` 兼容字段。
3. **故障注入**：旧 `simulate_downstream_failure` 钩子已移除，Saga 由真实节点异常触发。
4. **控制面豁免**：orchestration 目录/锁/DAG 保存属于低代码控制面，仍由控制面适配器直连 `catalog_service`；其写操作内部走 `OPC_ORCHESTRATION_CATALOG_PIPELINE`。
5. **持久化**：沿用 `domain_snapshots` family；新实体通过 `EntitySpec` 声明，启动时 `entity_store.initialize()` 重建。
6. **RAG**：语义检索仍由 `core/rag` 索引服务实体数据，场景通过 `external.rag.*` 调用。
