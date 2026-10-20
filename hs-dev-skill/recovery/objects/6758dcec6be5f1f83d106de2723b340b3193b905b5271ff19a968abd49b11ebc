# 任务计划与总结：TASK-033 创客注册流程商用化改造 · 法律合规/防刷风控/双重核验/多主体入驻

- **任务编号**：TASK-033
- **任务分级**：`M` (Medium)
- **优先级**：`P0`
- **执行人**：agent
- **意图**：`REFACTOR / COMPLIANCE / SECURITY`（解决原有注册流程过于简陋、缺乏邮箱真实性核验、无防机器人机制、缺失个保法/网络安全法强制协议签署等缺陷，完成商用级入驻流程改造）
- **关联设计与标准**：
  - 《中华人民共和国网络安全法》第 21/24 条（真实身份信息认证与安全存证）
  - 《中华人民共和国个人信息保护法》(PIPL)（最小必要原则、禁止默认勾选同意）
  - [opchub_rbac_auth_architecture.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_02_system_architecture/opchub_rbac_auth_architecture.md)
  - [_04_framework_detailed_design.md](file:///home/hardstone/Share/Common/CodeSpace/OpcHub/hs_dev_docs/_03_architecture_design/_03_detailed_design/_04_framework_detailed_design.md) §3.3 统一入站网关

---

## 1. 原有流程商用化缺陷排查 (Deficiencies)

1. **法律合规缺陷（法定义务阻断）**：
   - 缺少《用户服务协议》与《隐私政策》明示签署机制，违背个保法与网信办强制合规要求；
   - 无法满足平台合规雷达检查项（`chk_01: 用户注册/登录是否明确展示《隐私政策》且禁止默认勾选？`）。
2. **账号真实性与归属权缺失（垃圾灌库隐患）**：
   - 允许填写任意邮箱直接注册签发 Token，无邮箱所有权凭据核验，极易产生冒领他人邮箱、虚假邮箱垃圾灌库风险。
3. **安全防刷与人机验证空白（无防御暴露）**：
   - 无任何图形验证码或人机交互挑战，极易被自动化爬虫/脚本机暴力撞库或批量注册。
4. **弱口令安全风险**：
   - 仅简单校验长度 `>= 6`，允许诸如 `123456` 等常见字典口令，极易遭受弱口令暴力破解。
5. **主体画像单薄（不适应商业平台）**：
   - 超级个体商业平台存在“个人创客”、“一人公司 (OPC)”、“企业机构”等多形态主体，原有注册缺乏主体属性与赛道标签分类。

---

## 2. 商用化改造方案 (Implementation Architecture)

### ① 安全防刷与合规核验层 `src/domains/user/verification.py`
- `CaptchaService`：轻量自研 SVG 算术/字符动态验证码，零外部 C 库依赖， Retina 视网膜高清渲染，5分钟 TTL，单次核销防重放；
- `EmailVerificationService`：6 位加密安全随机码，60 秒频控冷却（Cooldown Rate-limiting），单 IP 小时频控限流，连续错误 5 次锁定作废机制；
- `PasswordPolicyService`：商用密码熵值计算、字符多样性检测（大/小写字母/数字/符号）、常见弱口令黑名单拦截；
- `LegalAgreementsRepository`：维护《OpcHub 平台用户服务协议 (v1.2.0)》与《隐私保护与个人信息安全指引 (v1.2.0)》法例文本。

### ② 领域模型与持久化扩展
- `UserRegisterRequest` 扩充商用参数：`verification_code`、`captcha_id`、`captcha_code`、`agreed_terms`（默认 True 兼顾兼容，前端与网关严格校验）、`account_type`、`industry_track`、`credit_code`、`phone`、`agreement_version`；
- `db_repository.create_user()` 增强：统一社会信用代码入库，合规签署存证（版本/时间戳/客户端IP）持久化落库至 `metadata_payload.agreement_consent`；
- `UserService.register_by_email()`：全链路执行“协议同意门禁 → 密码安全策略 → 人机验证码核验 → 邮箱验证码所有权核销 → 信用代码校验 → 唯一性检查 → 实体持久化 → 签发商业会话”。

### ③ 统一网关场景注册 (`gateway_routes.yaml`)
新增与升级统一网关场景：
- `auth.captcha`：获取人机安全算术/图形验证码；
- `auth.send-code`：申请发送邮箱核验验证码（含 60s 频控与防刷检测）；
- `auth.verify-code`：验证码预检；
- `auth.password-strength`：密码强度实时动态评估；
- `auth.legal-agreements`：获取法定服务协议与隐私政策；
- `auth.register`：全量商用入驻注册。
同步在 `src/main.py` 暴露对应 RESTful 端点，适配统一网关与微服务反向代理。

### ④ 前端液态拟态体验升级 (`opchub_all_pages_demo.html`)
- **主体类型分段选择**：个人创客 / 一人公司 / 企业机构，动态展开企业全称与 18 位统一社会信用代码；
- **防刷人机验证码**：高分辨率 SVG 算术题预览，点击即时换题；
- **邮箱验证码与倒计时**：带 60s 动态倒计时禁用态与开发测试环境一键识别；
- **实时密码强度色条**：红/橙/绿液态进度条与动态安全建议；
- **法律合规协议强制签署**：复选框默认**严格未勾选**，点击链接弹出协议全屏抽屉，支持阅读并一键签署，未勾选点击注册执行平滑温和拦截。

---

## 3. 验证证据 (Verification & Evidence)

1. **测试套件全绿**：
   - 专门编写新建 `backend/tests/test_commercial_registration.py`（包含 10 项端到端及安全边界测试全部通过）；
   - 全量回归测试：`python3 -m pytest backend/tests/ -q` → **219 passed, 5 skipped**（零失败、零报错）。
2. **代码规范与静态检查**：
   - `python3 -m pyflakes backend/src/ backend/tests/test_commercial_registration.py`：零语法或未引用错误。
3. **真实环境双链路验证**：
   - 真实网关 `POST /api/welcom/opc_world` 发送验证码与未勾选协议拦截（返回 `400 必须阅读并同意《用户服务协议》与《隐私保护指引》`）；
   - 填入验证码并勾选协议后，成功注册一人公司主体 `account_type="OPC"` 并正常签发商用工作台会话。
