# 任务验收备忘：TASK-027 创客邮箱注册、登录认证与关系数据库持久化

- **任务编号**：TASK-027
- **任务标题**：创客邮箱注册、登录认证与关系数据库持久化
- **分级**：`L`
- **执行人**：agent
- **完成时间**：`2026-10-17T18:45:00Z`
- **状态**：`VERIFIED_AND_ACCEPTED`

---

## 1. 交付产物与实现细节

1. **密码哈希与防篡改签名会话管理 (`backend/src/core/security.py`)**：
   - 采用标准库 `hashlib.pbkdf2_hmac`（100,000 次 SHA256 迭代计算与强随机盐值）实现密码哈希与常量时间安全比对，无需依赖 C 编译器库。
   - 实现无状态、防篡改签名会话凭据（HMAC-SHA256 Token），携带 `uid`、`email`、`role`、`exp` 声明，有效杜绝伪造与越权访问。

2. **数据库仓储层与多实体持久化 (`backend/src/infrastructure/database/repository.py`)**：
   - 构建 `DatabaseRepository` 异步仓储类，提供健康探针 `is_ready()`。
   - 启动时自动执行 DDL 迁移建表 (`ensure_schema_and_seed()`)，并向数据库自动注入基础权益目录与演示创客。
   - 提供 `User`、`Policy`、`Demand`、`ForumThread`、`ProductShowcase` 等核心业务实体的异步 CRUD 接口，并具备离线/单测环境平滑内存降级能力。

3. **用户域模型与服务扩充 (`backend/src/domains/user/`)**：
   - 扩充 `UserRegisterRequest`、`UserLoginRequest`、`AuthSessionResponse`。
   - `UserService` 实现邮箱注册格式校验、密码长度安全检查、防重名冲突校验、自动密码哈希与数据库写入。
   - `UserService` 实现邮箱密码鉴权与会话凭证签发，以及基于 Token 的会话状态反解 `get_session_by_token()`。

4. **网关与双路由 API 契约 (`gateway_routes.yaml`, `adapters.py`, `main.py`)**：
   - 在统一网关 `gateway_routes.yaml` 注册 `auth.register`、`auth.login`、`auth.session` 场景路由。
   - 在 `adapters.py` 中实现对应异步适配器，支持 `POST /api/welcom/opc_world` 统一场景网关调用。
   - 在 `main.py` 暴露标准 REST 接口：`POST /api/auth/register`、`POST /api/auth/login`、`GET /api/auth/session`，并同时挂载 `/api/v1/auth/*` 兼容路由。
   - 配置 FastAPI `lifespan` 机制，在服务启动时自动检查数据库就绪状态并完成 DDL 建表。

5. **前端液态玻璃交互与会话指示器 (`hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html`)**：
   - **导航栏右侧状态栏**：未登录时展示【登录】与【注册】液态玻璃按钮；登录后动态渲染创客首字母渐变头像、昵称、会员等级标贴（如 `标准创客` / `黑钻创客`）及安全【退出】按钮，支持直接点击进入创客个人中心。
   - **登录模态弹窗 (`#liquidLoginModal`)**：支持邮箱、密码输入，实时错误提示与回车登录，并提供一键跳转注册引导。
   - **邮箱注册模态弹窗 (`#liquidRegisterModal`)**：支持邮箱、6位以上密码、重复密码二次校验、创客昵称与工作室名称选填。
   - **会话持久化与自动恢复**：注册/登录成功后 Token 存储至 `localStorage.opchub_session_token`，在页面加载 (`DOMContentLoaded`) 时通过 `restoreUserSession()` 自动拉取身份会话并刷新状态栏。

6. **全量自动化测试与回归保障 (`backend/tests/test_auth_and_persistence.py`)**：
   - 验证 PBKDF2-HMAC-SHA256 密码哈希生成、校验与防爆破特性。
   - 验证 Token 签发、解密、篡改签名拦截与过期拒绝机制。
   - 验证邮箱注册输入合法性（非法邮箱格式与密码过短拒绝）。
   - 验证端到端注册、防重名拦截、登录鉴权全流程。
   - 验证网关 `auth.register`、`auth.login`、`auth.session` 场景分发契约。
   - 验证 FastAPI REST 接口返回码与错误响应。
   - 全量回归测试：全工程 163/163 测试用例 100% 绿灯通过。

---

## 2. 门禁验证记录

```bash
# 1. 运行用户认证与数据持久化专用测试
/home/hardstone/.virtualenvs/opchub/bin/pytest backend/tests/test_auth_and_persistence.py -v
# 结果: 6 passed in 1.56s

# 2. 运行工程全量测试用例
/home/hardstone/.virtualenvs/opchub/bin/pytest backend/tests -q
# 结果: 163 passed, 1 warning in 3.27s (100% PASS)

# 3. 本地服务真实 HTTP 请求调用验证
curl --noproxy "*" -s -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"curl_test_user@opchub.cn","password":"Password123!","nickname":"Curl创客","company_name":"极客测试工作室"}'
# 结果: HTTP 201 Created，成功返回 signed session token 与创客主体信息

curl --noproxy "*" -s -X POST http://127.0.0.1:8000/api/welcom/opc_world \
  -H "Content-Type: application/json" \
  -d '{"scenario":"auth.login","version":"v1.0.0","payload":{"email":"curl_test_user@opchub.cn","password":"Password123!"},"context":{}}'
# 结果: code 200 SUCCESS，耗时 20.65ms
```

---

## 3. 验收结论
- 用户需求目标（启动工程、增加邮箱注册与登录页面、保证数据持久化与页面交互正常）已全部达成。
- 163 个单元与集成测试全部通过，代码库质量与架构约束完全合规。
- 验收状态：`VERIFIED_AND_ACCEPTED`。
