# 算子内核 v2：算子粒度与编排规范

> 状态：BINDING（本轮全量迁移基准）
> 目标：所有业务由「业务无关算子 + 场景 YAML 编排」表达；Service 不再承载流程与决策。

## 1. 分层与依赖

```
Gateway (config/gateway_routes.yaml)
  └── pipeline: OPC_xxx            # 只声明场景，不再 import service/adapter
        └── Scenario YAML (config/scenarios/*.yaml)
              └── Operator (core/operators/* 或 domains/*/functions.py)
                    └── EntitySpec + EntityStore (domains/*/entities.py)
```

- `core/operators/**`：**禁止** `import src.domains`。只能做 guard / validate / transform / entity / notify / audit / metric / render / external / response。
- `domains/<d>/functions.py`：只允许**单职责纯函数算子**（CALC / ASSEMBLE / POLICY），禁止 I/O、禁止调用其他算子、禁止 `execute_scenario`、禁止 import 其他 domain。
- `domains/<d>/entities.py`：只允许声明 `EntitySpec` 并 `entity_store.register`，禁止业务逻辑。
- `domains/<d>/service.py`：迁移完成后只保留兼容 shim 或删除；不得再承载业务流程。

## 2. 算子契约

每个算子必须满足：

1. **单算子单功能**：名称能唯一描述一个动作；一个算子内不得串联两个业务步骤。
2. **无编排**：不得调用 `microkernel_engine` / `orchestration_service` / 其他算子。
3. **无隐式上下文**：输入来自 `args`（节点映射）与 `params`（节点静态配置）；身份只从 `context` 读取。
4. **幂等/可补偿**：写算子要么天然幂等，要么在场景中声明补偿节点。
5. **可复用**：通用能力放 `core/operators`；领域函数至少被一个场景使用，且不得包含 CRUD/流程。

命名：

- 通用：`guard.*` / `validate.*` / `transform.*` / `entity.*` / `query.*` / `notify.*` / `audit.*` / `metric.*` / `render.*` / `external.*` / `response.*`
- 领域纯函数：`calc.<domain>.<verb>` / `assemble.<domain>.<noun>` / `policy.<domain>.<state_transition>`

## 3. EntitySpec 规范

```python
EntitySpec(
    name="forum.thread",          # 全局唯一实体名（业务配置引用它）
    family="forum.threads",        # 持久化文档族（沿用现有 domain_snapshots 族名）
    model=ForumThreadResponse,     # 可选：创建/更新时校验
    key_fields=("id",),            # 复合键可写多字段
    id_prefix="thr",
    search_fields=("title", "content"),
    owner_field="author_id",
    default_order="-created_at",
    defaults={...},                # 仅字段默认值，不放业务规则
)
```

- 实体名使用 `<domain>.<singular>`；关联表也用实体表达（如 `forum.vote`，复合键 `("user_id","target_type","target_id")`）。
- 旧数据族名必须沿用（`products.items`、`forum.threads`…），保证持久化兼容。
- 角色/权限/审核状态等**不放在 defaults**，由场景节点与纯函数处理。

## 4. 场景 YAML 规范

```yaml
scenarios:
  - scenario: OPC_FORUM_THREAD_PUBLISH      # 必须全局唯一
    version: v1.0.0
    domain: forum
    description: 发布头脑风暴帖子
    saga: true
    nodes:
      - id: auth
        operator: guard.authn
      - id: create
        operator: entity.create
        params: {entity: forum.thread}
        inputs:
          data: $nodes.normalize
      - id: metric
        operator: metric.incr
        params: {metric: forum.thread.published}
    edges:
      - [auth, create]
      - [create, metric]
```

- `inputs` 表达式：`$inputs.x`、`$context.user_id`、`$nodes.<id>.x`、`$params.x`。
- `when` 为布尔表达式（无 `$` 前缀），作用域：`inputs` / `context` / `nodes` / `params`。
- 条件分支用 `when` + 独立节点表达；禁止在算子里写 if/else 流程。
- 所有写场景必须有 `auth`（除非明确公开）与至少一个 `metric` 或 `audit` 节点。

## 5. 网关路由规范

`config/gateway_routes.yaml` 的每条业务路由只允许：

```yaml
- scenario: "forum.threads.publish"
  version: "v1.0.0"
  domain: "forum"
  description: "..."
  is_default: true
  pipeline: "OPC_FORUM_THREAD_PUBLISH"
  required_permission: "content:publish"
```

禁止 `handler:` / `model:` / `args_type:`。路由的 RBAC/ABAC 仍由网关统一执行。

## 6. 交付清单（每个领域）

1. `src/domains/<d>/entities.py`：全部实体 spec。
2. `src/domains/<d>/functions.py`：纯函数算子（有则写，无则空文件）。
3. `config/scenarios/<d>.yaml`：该领域全部业务场景。
4. `config/routes/<d>.yaml`：`gateway_scenario -> pipeline` 映射（供主控汇总）。
5. `tests/test_<d>_operator_flows.py`：至少覆盖写场景成功 + 关键失败。
6. 移除 `service.py` 中的业务流程；保留的公开类方法必须是数据/兼容 shim。

## 7. 验收命令

```bash
cd backend
python3 -m pytest tests/test_<d>_operator_flows.py -q
python3 -m pytest tests/test_operator_contract.py -q
```

禁止为了让测试通过而在算子里塞业务分支；测试应改为断言场景输出。
