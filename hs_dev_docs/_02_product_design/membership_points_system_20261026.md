# 会员体系与积分体系设计（V1）

> 文档类型：产品机制设计 / 仅设计，暂不改代码
> 日期：2026-10-26
> 适用平台：晨昏线外 OpcHub（一人公司商业操作系统）
> 上游约束：`/DESIGN.md`（液态玻璃 / 克制 / 内容优先）、现有 `user`、`interactions`、`forum`、`perks`、`policies` 领域

---

## 0. 一页纸结论

平台需要的是**三套互不混用的"值"**，而不是一个万能积分：

| 名称 | 作用 | 是否可消费 | 是否可购买 | 是否过期 | 决定什么 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **晨光积分（points）** | 社区贡献的流通货币 | 是 | 否（只能赚/运营发） | 24 个月滚动过期 | 能兑换什么 |
| **成长值（growth）** | 长期贡献的经验值 | 否 | 否 | 永不过期 | 等级 V1–V6 |
| **信誉分（reputation）** | 行为质量的风控分 | 否 | 否 | 可升可降 | 互动是否计分、是否限权 |

**会员（Membership）是独立的一轨**：标准 / PRO / 黑钻，按时间计费，可用现金购买，也可用积分兑换。会员不产生"成长值"，也不能购买点赞或互动计数，只影响**功能额度、分发排序、服务优先级**。

一句话规则：

> 发内容赚积分，好内容赚成长，坏行为扣信誉；积分换会员和周边，会员买效率和额度，等级证明你是老创客。

**三条不可突破的底线**：

1. **积分不可提现、不可转让、不可兑换现金**，只是平台服务权益凭证（合规红线）。
2. **付费不能购买互动数据**：会员可影响排序权重，但绝不虚增点赞/收藏/评论计数。
3. **积分账本必须强一致**：不能用现有 write-behind 快照承载余额，必须走数据库事务 + 只追加流水。

---

## 1. 现状与设计约束

### 1.1 已存在的能力（必须兼容，不推翻）

| 现有资产 | 位置 | 对本设计的约束 |
| :--- | :--- | :--- |
| 会员档位 `STANDARD / PRO / BLACK_DIAMOND` | `backend/src/domains/user/models.py` | 沿用三个档位，不新增命名；中文名沿用「标准创客 / PRO / 黑钻创客」 |
| 定价 0 / 199 / 899 元 | `data/seeds/entitlements.json` | 作为年费锚点，不随意改价 |
| `tier_name`、`active_entitlements`、`entitlement_expiries` | `backend/src/domains/user/service.py` | 继续作为**派生展示字段**写入，保证旧接口/旧前端不炸 |
| 统一互动 `LIKE / FAVORITE / LOVE / DISLIKE` + 评论 | `backend/src/domains/interactions/models.py` | 积分事件直接从互动域发出，不新建一套点赞 |
| 论坛独立 `UPVOTE / DOWNVOTE / CANCEL` | `backend/src/domains/forum/models.py` | 论坛投票走论坛账本，积分侧只订阅事件，避免双写 |
| 内容发布审核门禁 | `moderation` + 各域 create | **审核通过才计分**，未通过/驳回不计分 |
| `perks` 域 | `backend/src/domains/perks/*` | 它是第三方优惠公告，**不是周边商城**，不要复用；商城另建 `loyalty` 域 |
| write-behind 快照持久化 | `backend/src/infrastructure/database/persistence.py` | 适合内容计数，**不适合余额/订单/会员到期**；这些必须强一致 |

### 1.2 设计原则

1. **贡献可积累，作弊必回滚**：所有积分先 `PENDING`，结算后才可用；取消互动、内容下架可反向冲销。
2. **免费用户不被饿死**：政策浏览、发帖、互动、基础模板永久免费；付费买的是"效率与额度"，不是"发言权"。
3. **规则可配置**：分值、上限、兑换价全部进配置表，运营可调，代码不写死。
4. **先小后大**：先上"发布 + 被赞 + 兑换会员"，再上周边、等级、排行榜。
5. **可审计**：任何一分钱的积分都能追到"谁、因为什么、哪条内容、什么时间、什么状态"。

---

## 2. 总体模型：三账本 + 双轨会员

### 2.1 三个正交的"值"

```
                    ┌──────────────────────────────┐
   内容/互动 ──────▶│  晨光积分  (可花，会过期)      │──▶ 会员时长 / 周边 / 曝光券
                    ├──────────────────────────────┤
   优质贡献 ──────▶│  成长值    (不可花，不过期)    │──▶ V1–V6 等级与等级权益
                    ├──────────────────────────────┤
   行为质量 ──────▶│  信誉分    (可升可降)          │──▶ 互动计分权重 / 发布门禁
                    └──────────────────────────────┘
```

- **积分**回答"我能换什么"。
- **成长值**回答"我在这平台算老几"。
- **信誉分**回答"你说的话算不算数"。

### 2.2 为什么不用一套积分同时做等级和消费

| 若合并 | 后果 |
| :--- | :--- |
| 消费会掉等级 | 用户不敢兑换，商城形同虚设 |
| 等级靠花钱 | 付费用户碾压社区，内容生态失真 |
| 刷分即刷等级 | 一次作弊永久污染身份体系，无法回收 |

所以：**积分可花可回滚，成长值只增不减，信誉分独立惩罚**。

---

## 3. 会员体系

### 3.1 档位与定价

| 档位 | 内部值 | 中文名 | 月付 | 年付 | 定位 |
| :--- | :--- | :--- | ---: | ---: | :--- |
| L0 | `STANDARD` | 标准创客 | 免费 | 免费 | 能看、能发、能互动 |
| L1 | `PRO` | PRO 创客 | ¥19.9 | ¥199 | 高频做政策/文书/申报的个体 |
| L2 | `BLACK_DIAMOND` | 黑钻创客 | ¥89 | ¥899 | 要接单、要优先派单、要 1v1 的 OPC |

> 年付约为月付的 10 个月，制造"年付更划算"的自然选择；不搞复杂折扣券。

### 3.2 权益矩阵

权益必须能落到现有/规划功能上，避免"写在纸上用不上"。

| 权益 | 标准创客 | PRO 创客 | 黑钻创客 |
| :--- | :--- | :--- | :--- |
| 政策库浏览 / 检索 | 全量 | 全量 | 全量 |
| 政策资格匹配 | 3 次/月 | 无限 | 无限 |
| AI 文书生成 | 5 篇/月 | 100 篇/月 | 300 篇/月 + 优先队列 |
| 模板库 | 基础 30% | 全量 | 全量 + 1 次定制 |
| 导出 | 在线预览 | PDF / Word | PDF / Word / Excel 批量 |
| 需求投标 | 3 个/月 | 20 个/月 | 无限 + 顶格优先派单 |
| 内容分发权重 | 1.0x | 1.2x | 1.5x（仅排序，不改计数） |
| 积分获取倍率 | 1.0x | 1.2x | 1.5x |
| 积分兑换折扣 | 无 | 95 折 | 9 折 |
| 周边折扣 | 无 | 95 折 | 9 折 |
| 会员徽章 | — | PRO | 黑钻 |
| 客服响应 | 工单 48h | 优先 24h | 1v1 4h |
| 平台撮合佣金（如适用） | 10% | 8% | 5% |

**倍率封顶**：会员倍率 × 等级倍率 × 信誉系数，最终不超过 **2.0x**，防止叠乘失控。

### 3.3 获取、续期、升级、降级

| 场景 | 规则 |
| :--- | :--- |
| 现金购买 | 支付成功即生效，开具电子凭证；支付回调幂等 |
| 积分兑换 | 扣分成功即生效；兑换价含 20% 溢价（见 6.2） |
| 官方授予 | 创始会员/活动，写入 `source=GRANT`，带到期日，可被审计 |
| 同档续期 | `expires_at += 周期`，不重置已用配额 |
| 低档升高档 | 立即生效；剩余价值按天折算抵扣，补差价 |
| 高档降低档 | 到期后生效，不立即降权 |
| 到期 | 7 天宽限期（权益保留但提示续费）；宽限后降为 STANDARD |
| 到期后资产 | 积分、成长值、等级、已发布内容**全部保留**；未用配额清零 |
| 自动续费 | **默认关闭**；开启需二次确认，提前 3 天通知，可随时关闭；扣款失败重试 3 次后转宽限 |

### 3.4 与现有 entitlement 的兼容

不新建一套平行权益，而是"会员套餐 → 权益条目"的映射：

```
membership_plans(plan_code, tier, period, price_cny, points_price, benefits_json)
        │ 购买/兑换
        ▼
memberships(uid, tier, source, started_at, expires_at, auto_renew, status)
        │ 同步派生
        ▼
users.metadata.tier_name / active_entitlements / entitlement_expiries   ← 旧字段继续可读
```

- 现有 `ent_policy_radar_basic`、`ent_ai_tax_assistant`、`ent_black_diamond_priority` 保留 ID，作为套餐权益的一部分。
- `tier_name` 由会员服务统一写入，禁止其他模块直接改，避免"会员过期了但 tier_name 还是黑钻"。
- 配额（匹配次数/AI 篇数）单独放 `membership_quotas`，按自然月重置；**不要塞进 metadata**。

---

## 4. 积分体系

### 4.1 定位与命名

- 系统名：`points`；对外昵称：**晨光积分**（呼应"晨昏线外"，也可退化为中性的"OPC 积分"）。
- 单位：分。内部计价锚点：**1 分 = ¥0.01**（仅用于定价与财务折算，不可反向兑换现金）。
- 展示：等宽数字 + 千分位，例：`12,480`。

### 4.2 获取规则总表

> 所有"内容类"积分以**审核通过**为触发点；互动类积分 **T+1 结算**。

#### A. 一次性任务（每个账号一次）

| 事件码 | 行为 | 积分 | 成长值 | 备注 |
| :--- | :--- | ---: | ---: | :--- |
| `PROFILE_COMPLETE` | 完善头像 + 行业 + 公司/身份 | +200 | +50 | 资料完整度 ≥ 80% |
| `VERIFY_EMAIL` | 邮箱验证 | +100 | +20 | 注册流程内 |
| `VERIFY_IDENTITY` | 实名 / 企业认证 | +500 | +200 | 人工/三方核验通过 |
| `FIRST_PUBLISH` | 首次发布并通过审核 | +300 | +50 | 防"注册即刷" |

#### B. 发布内容（审核通过后即时入账）

| 事件码 | 内容类型 | 积分 | 成长值 |
| :--- | :--- | ---: | ---: |
| `PUBLISH_POLICY` | 政策 | +100 | +20 |
| `PUBLISH_SOP` | 文书 / 模板 / 流程 | +120 | +25 |
| `PUBLISH_FORUM` | 论坛主题 | +50 | +10 |
| `PUBLISH_PRODUCT` | 产品展示 | +60 | +12 |
| `PUBLISH_DEMAND` | 需求发布 | +60 | +12 |

发布类合计上限：**5 篇/日、500 分/日**；同一内容重复编辑不重复计分。

#### C. 被互动（T+1 结算，可回滚）

| 事件码 | 触发 | 积分 | 成长值 | 单篇上限 | 每日上限 |
| :--- | :--- | ---: | ---: | ---: | ---: |
| `RECEIVE_LIKE` | 他人点赞 | +5 | +2 | 300 | 300 |
| `RECEIVE_FAVORITE` | 他人收藏 | +10 | +5 | 500 | 400 |
| `RECEIVE_LOVE` | 他人喜欢 | +3 | +1 | 150 | 150 |
| `RECEIVE_COMMENT` | 他人评论（≥15 字） | +8 | +3 | 400 | 300 |
| `RECEIVE_READ` | 他人打开内容详情 | +1 | 0 | 200 | 50 |
| `RECEIVE_DISLIKE` | 他人踩（已确认不扣分） | 0 | 0 | — | — |
| `COMMENT_CREATED` | 我发表有效评论 | +5 | +1 | 3 条/篇 | 50 |

> 阅读积分按「读者 + 内容 + 自然日」幂等，同一读者同一天重复打开只计一次；作者自读不计分。
>
> 论坛的 `UPVOTE` 映射为 `RECEIVE_LIKE`，`DOWNVOTE` 映射为 `RECEIVE_DISLIKE`；`CANCEL` 触发回滚。避免论坛与统一互动重复计分。

#### D. 运营与持续性奖励

| 事件码 | 行为 | 积分 | 成长值 | 频率 |
| :--- | :--- | ---: | ---: | :--- |
| `QUALITY_BONUS` | 加精 / 优质内容 | +500 ~ +1500 | +300 | 运营发放 |
| `DAILY_STREAK_7` | 连续活跃 7 天 | +100 | +20 | 每周一次 |
| `DAILY_STREAK_30` | 连续活跃 30 天 | +500 | +100 | 每月一次 |
| `INVITE_SUCCESS` | 被邀请人首发通过审核 | +1000 | +50 | 5 人/月 |
| `MONTHLY_TOP` | 月度贡献榜 | +500 ~ +3000 | +200 | 每月 |

#### E. 兜底上限

| 维度 | 上限 |
| :--- | ---: |
| 单用户日获取（不含运营奖励） | 1,000 分 |
| 单用户月获取 | 20,000 分 |
| 单篇内容终身可产生积分 | 3,000 分 |
| 同一对用户 30 天内互动计分 | 20 次 |

### 4.3 结算与入账

| 类型 | 入账时机 | 可撤销窗口 |
| :--- | :--- | :--- |
| 发布 / 认证 / 任务 | 审核通过即时 `SETTLED` | 内容下架时回滚 |
| 互动 | T+1 凌晨批量 `PENDING → SETTLED` | 结算前取消直接撤销；结算后反向流水 |
| 运营奖励 | 即时 | 7 天内可撤销 |
| 兑换扣减 | 即时 | 订单取消则退回 |

流水状态机：

```
PENDING ──结算──▶ SETTLED ──过期──▶ EXPIRED
   │                  │
   └──取消/风控──▶ REVOKED ◀──冲销──┘
```

### 4.4 扣分与回滚（重点）

**踩（DISLIKE）的产品判断（已确认）**：**踩不直接扣积分**。

1. 踩只进入内容质量分与排序，不影响作者积分余额。
2. 恶意打压风险由信誉分与举报机制承担，而不是让踩变成扣分武器。
3. 作者只能看到聚合数，**永远看不到是谁踩的**。
4. 论坛 `DOWNVOTE` 同样不扣分，仅影响排序。

**回滚规则**：

| 触发 | 处理 |
| :--- | :--- |
| 取消点赞/收藏/喜欢 | 生成反向流水；未结算直接撤销 |
| 评论被删除 | 评论者与作者的对应积分回滚 |
| 内容下架 / 判定违规 | 该内容产生的**全部**积分回滚，成长值不回滚，信誉分扣 20 |
| 余额不足 | 允许负余额，标记 `debt`，**限制兑换/提现类操作**直到补齐 |
| 风控冻结 | 收益转 `FROZEN`，人工复核后放行或撤销 |

### 4.5 成长值与等级

| 等级 | 名称 | 成长值门槛 | 等级权益 |
| :--- | :--- | ---: | :--- |
| V1 | 微光 | 0 | 基础权益 |
| V2 | 破晓 | 500 | 积分 1.05x；日互动上限 +20 |
| V3 | 晨光 | 2,000 | 积分 1.10x；兑换 95 折；专属徽章 |
| V4 | 炽阳 | 6,000 | 积分 1.15x；兑换 9 折；分发权重 1.1x |
| V5 | 长明 | 15,000 | 积分 1.20x；兑换 85 折；优先审核；分发 1.2x |
| V6 | 恒星 | 40,000 | 积分 1.30x；兑换 8 折；年度实体礼；分发 1.3x |

- 成长值**只增不减**（严重违规也不扣，改用信誉分惩罚），避免"一夜回到解放前"。
- 等级权益与会员权益**叠加但封顶 2.0x**。
- 等级不发"免费会员"，避免削弱付费转化；只给折扣与曝光。

### 4.6 信誉分

- 初始 80，区间 0–100。
- 加分：内容通过审核 +1（上限 100）；连续 30 天无违规 +5。
- 减分：举报成立 -5；一般违规 -20；严重违规 -50；刷分 -30 起。
- 分档影响：

| 区间 | 影响 |
| :--- | :--- |
| 80–100 | 正常；互动全额计分 |
| 60–79 | 互动计分 0.5x |
| 40–59 | 互动不计分；发布转人工审核 |
| 20–39 | 禁言 7 天；不可兑换实物 |
| 0–19 | 封禁；收益冻结 |

- 恢复：连续 30 天无违规 +5，上限回到 100。

---

## 5. 防刷与风控

积分系统真正的难点不是"发分"，而是"不被刷"。以下规则必须在 P1 就上，不能等出事再补。

### 5.1 计分资格

一个互动要计分，必须同时满足：

1. 互动者 ≠ 作者（自赞/自评一律 0）。
2. 互动者注册 ≥ 3 天、邮箱已验证、信誉 ≥ 60、未封禁。
3. 互动者与作者不在同一设备指纹 / 同一 `/24` IP 段（可疑则降权不计分）。
4. 新账号注册 7 天内，互动权重 **0.3x**（不足 1 分不计）。
5. 互动未被风控标记。

### 5.2 反互刷

| 风险 | 规则 |
| :--- | :--- |
| 互赞小队 | A→B 每日计分 3 次、30 天 20 次；超出只显示不计数 |
| 小号刷量 | 同设备/同 IP 多账号 → 收益冻结，人工复核 |
| 秒赞秒取消 | T+1 结算，结算前取消直接撤销 |
| 批量点赞 | 单账号 60 次/小时、评论 20 条/小时限流 |
| 爆量异常 | 1 小时内单篇 > 50 赞且来源集中 → 自动冻结待审 |
| 内容农场 | 单日发布超限、模板化重复内容 → 不计分 + 降权 |
| 刷评论 | 评论 ≥ 15 字、每用户每篇 ≤ 3 条计分 |

### 5.3 风控动作

- `FLAG`：标记，继续观察。
- `FREEZE`：收益冻结，用户可申诉。
- `REVOKE`：撤销收益 + 扣信誉。
- `BAN`：封禁，收益清零。

所有动作写 `risk_events`，保留证据（IP、设备、行为序列），申诉窗口 7 天。

---

## 6. 积分消耗

### 6.1 兑换目录

#### A. 会员时长（核心出口）

| 商品 | 积分价 | 说明 |
| :--- | ---: | :--- |
| PRO 月卡 | 2,400 | ≈ ¥24 价值，溢价 20% |
| PRO 年卡 | 24,000 | ≈ ¥240 价值 |
| 黑钻月卡 | 10,800 | ≈ ¥108 价值 |
| 黑钻年卡 | 108,000 | ≈ ¥1,080 价值 |

#### B. 实体周边（第二批上）

| 商品 | 积分价 | 库存策略 |
| :--- | ---: | :--- |
| 贴纸包 | 1,500 | 常备 |
| 亚克力徽章 | 3,000 | 常备 |
| 工牌 + 挂绳 | 4,500 | 常备 |
| 帆布袋 | 6,000 | 季度补货 |
| 年度年鉴 | 12,000 | 年度限量 |
| 桌面摆件 | 15,000 | 限量 |
| 联名限量款 | 30,000 | 抢购 |

- 满 8,000 分包邮，否则 ¥8 运费（运费不走积分，避免"积分当钱"的合规观感）。
- 实物兑换需填收货信息，订单状态：`CREATED → PAID → SHIPPED → COMPLETED`，7 天无理由（不影响二次销售）。

#### C. 数字权益（低成本、高感知）

| 商品 | 积分价 | 说明 |
| :--- | ---: | :--- |
| 内容置顶 24h | 3,000 | 每人每周 1 次 |
| 加精申请 | 5,000 | 审核不通过全额退 |
| AI 加量包（50 篇） | 2,000 | 仅会员可买 |
| 模板解锁券 | 800 | 单模板 |
| 改名卡 | 1,000 | 90 天 1 次 |

### 6.2 定价锚与兑换比率

- 内部锚点：**1 分 = ¥0.01**。
- 现金价 → 积分价：`积分价 = 现金价 × 100 × 1.2`（20% 溢价，四舍五入到百位）。
- 意义：积分是"忠诚度折扣"，不是"等价货币"；现金永远比积分略划算，保护现金流。
- 会员再叠加兑换折扣（PRO 95 折 / 黑钻 9 折），但**不得低于成本线**。

### 6.3 兑换规则

1. 积分不足不可下单；负余额账号禁止兑换。
2. 实物每人每商品每月限 2 件；数字权益按表内限制。
3. 兑换会员：同档顺延、升档补差、降档到期生效。
4. 兑换成功即扣分，订单取消/审核不过原路退回（含过期批次按原有效期退回）。
5. 积分**不可转赠、不可合并账号、不可开发票**（会员现金部分可开票）。

---

## 7. 数据模型

### 7.1 新增表（建议放 `domains/loyalty`，与 `perks` 明确区分）

```sql
-- 余额账户：一人一条，行锁更新
points_accounts(
  uid PK, balance BIGINT NOT NULL DEFAULT 0, frozen BIGINT DEFAULT 0,
  total_earned BIGINT DEFAULT 0, total_spent BIGINT DEFAULT 0,
  debt BIGINT DEFAULT 0, version INT DEFAULT 0, updated_at TIMESTAMP
)

-- 只追加流水：唯一真相源
points_ledger(
  id PK, uid, delta BIGINT, balance_after BIGINT,
  event_code, ref_type, ref_id, actor_id,
  status ENUM(PENDING, SETTLED, REVOKED, EXPIRED, FROZEN),
  settle_at, expires_at,
  idempotency_key UNIQUE,           -- 幂等，防重复入账
  note, created_at
)

-- 规则配置：运营可调，不写死代码
points_rules(
  code PK, name, delta, daily_cap, monthly_cap, per_target_cap,
  enabled, effective_from, version
)

-- 会员套餐
membership_plans(
  plan_code PK, tier, period_months, price_cny, points_price,
  benefits_json, active
)

-- 会员实例：一人一条当前 + 历史归档
memberships(
  uid PK, tier, source ENUM(CASH, POINTS, GRANT),
  started_at, expires_at, auto_renew, status,
  last_order_id, updated_at
)

-- 配额：按周期重置，独立于 metadata
membership_quotas(
  uid, benefit_code, period_start, period_end, used, quota_limit,
  PRIMARY KEY(uid, benefit_code, period_start)
)

-- 兑换商品与订单
reward_items(
  code PK, name, type ENUM(MEMBERSHIP, PHYSICAL, DIGITAL),
  points_price, stock, per_user_limit, active, meta_json
)
redemption_orders(
  id PK, uid, item_code, qty, points_cost, status,
  address_json, tracking_no, created_at, updated_at
)

-- 成长与信誉
user_growth(uid PK, growth BIGINT, level INT, updated_at)
user_reputation(uid PK, score INT, updated_at)

-- 风控
risk_events(id PK, uid, type, payload_json, action, created_at)
```

### 7.2 与现有表的关系

| 现有 | 关系 |
| :--- | :--- |
| `users` | 不新增余额字段；`metadata.tier_name` 由会员服务派生写入 |
| `entitlements` / `user_entitlements` | 套餐权益仍映射到 `ent_*`，保持旧接口兼容 |
| `content.interaction_stats` | 只做展示计数，**不作为积分依据**；积分依据是 `interaction_records` 事件 |
| `domain_snapshots` | 可存规则/商品目录等弱一致数据；**禁止存余额、订单、会员到期** |

### 7.3 一致性要求（架构关键）

现有 `persistence.py` 是 write-behind 快照，适合内容索引，**不适合账务**。积分/会员/订单必须：

1. 走数据库事务：`INSERT ledger` + `UPDATE account` 同一事务，行锁 + `version` 乐观锁。
2. 幂等键唯一索引兜底，重复事件直接忽略。
3. 事件采用 **Outbox 模式**：业务域写 `loyalty_outbox`，后台 worker 消费并记账，保证"内容发布成功但积分丢了"不会发生。
4. 每日对账：`SUM(ledger.delta) == accounts.balance`，不一致告警并冻结相关账户。

---

## 8. 事件与接口草案

### 8.1 领域事件

| 事件 | 来源 | 载荷 |
| :--- | :--- | :--- |
| `content.published` | policies / sop / forum / products / demands | `target_type, target_id, author_id, moderation_status` |
| `content.removed` | moderation / admin | `target_type, target_id, reason` |
| `interaction.toggled` | interactions | `actor_id, target_type, target_id, kind, active` |
| `comment.created` / `comment.deleted` | interactions / forum | `actor_id, target_id, comment_id, length` |
| `forum.voted` | forum | `actor_id, target_id, vote_type` |
| `membership.purchased` / `expired` | payment / scheduler | `uid, plan_code, source` |
| `redemption.created` / `shipped` | loyalty | `uid, item_code, points_cost` |

统一原则：**业务域只发事件，不直接改余额**；loyalty 域是唯一记账方。

### 8.2 API 草案（前缀沿用 `settings.api_prefix`）

```
GET    /points/account                 余额、冻结、本月收支、等级进度
GET    /points/ledger?cursor=&event=   流水分页（只读）
GET    /points/rules                   当前生效规则（前端展示"怎么赚"）

GET    /membership/plans               套餐与权益对比
GET    /membership/me                  当前会员、到期日、配额用量
POST   /membership/subscribe           { plan_code, pay_method: CASH|POINTS }
POST   /membership/renew
POST   /membership/auto-renew          { enabled }
POST   /membership/cancel              到期不续（非退款）

GET    /rewards/items                  兑换目录（含库存/限购）
POST   /rewards/redeem                 { item_code, qty, address? }
GET    /rewards/orders                 我的兑换单
POST   /rewards/orders/{id}/cancel     未发货可取消

# 管理端
POST   /admin/points/grant             { uid, delta, reason }  人工补/扣
POST   /admin/points/rules             改规则（版本化）
POST   /admin/rewards/items            上下架/补库存
POST   /admin/rewards/orders/{id}/ship 发货
GET    /admin/loyalty/reconciliation   对账报表
```

约定：

- 所有写接口要求登录态，`uid` 从网关注入，**不接受前端传 uid**（防越权）。
- 兑换/购买接口必须带 `Idempotency-Key` 头。
- 金额与积分一律整数分/整数积分，禁止浮点。

---

## 9. 关键流程

### 9.1 发布得分

```
用户提交 → 审核门禁 → 通过 → content.published
   → loyalty 消费事件 → 检查资格/上限 → 写 PENDING
   → 即时 SETTLED（发布类）→ 更新余额 → 推送"积分 +100"
审核驳回/下架 → content.removed → 反向流水 → 余额回滚
```

### 9.2 点赞得分

```
A 点赞 B 的内容 → interaction.toggled(active=true)
   → 资格校验（非自赞/注册天数/信誉/设备/互刷上限）
   → 写 PENDING(+5, settle_at=T+1)
   → T+1 worker 批量 SETTLED
A 取消点赞 → 反向流水（未结算撤销 / 已结算冲销）
```

### 9.3 积分兑换会员

```
选套餐 → 校验余额/负余额/限购 → 事务：扣分 + 建订单 + 延长会员
   → 同步派生 tier_name / entitlements → 返回新到期日
失败（余额不足/并发）→ 整体回滚，不产生半成品订单
```

### 9.4 会员到期

```
每日扫描 expires_at < now → 7 天宽限（发通知）
   → 宽限结束 → 降级 STANDARD → 回收配额（未用清零）
   → 保留积分/成长值/内容/等级 → 发"会员已到期"通知
```

---

## 10. 运营、财务与合规

### 10.1 积分负债管理

- 积分是**平台负债**：`负债 ≈ 总余额 × ¥0.01 × 预计兑换率(30%)`。
- 每月出报表：发放量、回收量、净增、人均余额、兑换率、过期量。
- 目标健康区间：**发放 : 回收 ≈ 1 : 0.6**；净增过快就收紧规则或加兑换出口。
- 有效期：**24 个月滚动过期**，按批次 FIFO 扣减；过期前 30 天通知。

### 10.2 合规红线

1. 积分**不可提现、不可转让、不可兑换现金**，用户协议明确"服务权益凭证"。
2. 自动续费默认关闭，开通需显著提示，随时可取消（《网络交易监督管理办法》）。
3. 积分规则变更提前 7 天公示，**不溯及既往**；已获得积分按旧规则有效。
4. 周边为"赠品/兑换品"，标注数量有限、兑完即止，非销售行为。
5. 会员现金部分可开票；积分部分不开票。
6. 未成年人、实名、内容合规沿用现有 `moderation` 与 `compliance` 能力。

### 10.3 健康指标（北极星）

| 指标 | 目标 |
| :--- | :--- |
| 月活跃创作者占比 | ≥ 8% |
| 内容互动率（互动/曝光） | ≥ 3% |
| 积分兑换率（年） | ≥ 40% |
| 会员付费转化（活跃用户） | 3%–5% |
| 积分相关客诉率 | < 0.5% |
| 刷分识别率 / 误伤率 | > 90% / < 1% |

---

## 11. 前端信息架构与视觉

遵循 `/DESIGN.md`：液态玻璃、单一 CTA、等宽数字、零 Emoji、零廉价图标。

### 11.1 页面

| 页面 | 内容 | 关键交互 |
| :--- | :--- | :--- |
| 个人中心 · 资产卡 | 晨光积分余额、等级进度、本月 +/– | 点击进入明细 |
| 积分明细 | 按日分组流水，`+100 发布政策` / `-24,000 兑换 PRO 年卡` | 筛选、下拉加载 |
| 积分商城 | 会员 / 周边 / 数字权益三组 | 库存、所需积分、兑换确认 |
| 会员中心 | 三档权益对比、当前档高亮、到期日 | 唯一主 CTA「升级 / 续费」 |
| 赚积分说明 | 规则表 + 上限 + 结算说明 | 静态页，降低客诉 |

### 11.2 视觉细节

- 余额用 `SF Mono`，字号大、字距收紧，作为视觉主角。
- 收入 `+` 用 `accent` 蓝，支出用 `text-secondary` 灰；**不用红绿**，避免廉价感。
- 等级进度用一条 1px 发丝线 + 柔和光晕，不做花哨进度条。
- 兑换确认用底部轻量毛玻璃 Modal，二次确认，写明"积分一经兑换不可逆"。
- 会员徽章只用单色几何标记，不做金色渐变。

---

## 12. 分期落地

| 阶段 | 范围 | 产出 | 预估 |
| :--- | :--- | :--- | :--- |
| **P0 账本底座** | 账户、流水、规则表、outbox、幂等、对账 | 能安全记账 | 3–4 天 |
| **P1 赚分闭环** | 发布得分、点赞/收藏/评论得分、T+1 结算、回滚、基础上限 | 积分能赚能退 | 4–5 天 |
| **P2 会员闭环** | 套餐、购买/兑换、到期降级、配额、tier 派生 | 会员能买能续 | 4–5 天 |
| **P3 兑换商城** | 会员兑换、数字权益、实物订单与发货 | 积分能花 | 4–6 天 |
| **P4 成长与风控** | 成长值/等级、信誉分、互刷检测、风控后台 | 体系自洽 | 5–7 天 |
| **P5 运营增强** | 排行榜、连续活跃、邀请、活动积分 | 拉活跃 | 按需 |

> 建议 P0–P2 先上，P3 周边可以先用"预约登记 + 人工发货"验证需求，再重投入做库存与物流。

---

## 13. 待确认决策

以下 6 个点会显著改变实现，建议先拍板：

1. **踩是否直接扣积分？**
   ✅ 已确认：**不扣积分**，只影响内容质量分与排序。理由：防恶意打压。
2. **积分能否兑换年卡？**
   ✅ 已确认：**可以**，年卡按现金价 ×1.2 溢价兑换，同时保留月卡。
3. **是否上线成长等级？**
   推荐：上线，但放 P4。理由：它是留存钩子，但不影响交易闭环。
4. **积分有效期？**
   推荐：24 个月滚动过期。理由：控制负债，行业惯例。
5. **会员自动续费？**
   推荐：默认关闭，显式开启。理由：合规与口碑。
6. **积分能否转赠？**
   推荐：不能。理由：一旦可转赠，就接近"虚拟货币"，合规风险陡增。

---

## 14. 风险清单

| 风险 | 影响 | 缓解 |
| :--- | :--- | :--- |
| 刷分产业化 | 积分通胀、会员被薅 | 资格门槛 + 互刷上限 + T+1 + 风控冻结 |
| 积分负债失控 | 财务隐性成本 | 24 个月过期 + 月发放上限 + 兑换率监控 |
| 付费破坏社区公平 | 用户流失 | 会员只买额度/排序，不买计数；倍率封顶 2.0x |
| 权益承诺无法交付 | 客诉/退款 | 权益矩阵只写已上线或确定上线的能力 |
| 周边物流成本 | 亏损 | 包邮门槛 + 限量 + 季度补货 |
| 账务不一致 | 信任崩塌 | 强一致事务 + 幂等 + 每日对账 |
| 规则频繁变更 | 用户不满 | 版本化 + 提前公示 + 不溯及既往 |

---

## 15. 实现落地（V1）

### 15.1 后端

| 层 | 文件 | 说明 |
| :--- | :--- | :--- |
| 领域模型 | `backend/src/domains/loyalty/models.py` | 积分规则 / 流水 / 账户 / 会员 / 兑换订单 |
| 领域服务 | `backend/src/domains/loyalty/service.py` | 唯一记账方；余额、幂等、上限、倍率、会员同步、兑换履约 |
| 原子算子 | `backend/src/domains/loyalty/operators.py` | `loyalty.identity_guard / event_resolve / award_guard / points_settle / points_revoke / redeem_guard / redeem_settle / subscribe_guard / subscribe_settle / telemetry.incr` |
| 算子编排 | `backend/src/domains/loyalty/pipelines.py` | `OPC_LOYALTY_AWARD_PIPELINE`、`OPC_LOYALTY_REVOKE_PIPELINE`、`OPC_LOYALTY_REDEEM_PIPELINE`、`OPC_LOYALTY_SUBSCRIBE_PIPELINE` |
| 网关路由 | `backend/config/gateway_routes.yaml` | `loyalty.account / ledger / rules / membership.* / rewards.* / content.read / admin.grant` |
| 业务联动 | `backend/src/core/gateway/adapters.py` | 发布、点赞/收藏/喜欢/踩、评论、论坛投票、阅读、注册、资料完善 |
| 会员同步 | `backend/src/domains/user/service.py` | `sync_membership()` 将会员档位投影到 `tier_name / active_entitlements` |
| 数据种子 | `backend/data/seeds/loyalty_rules.json`、`membership_plans.json`、`reward_items.json` | 规则、套餐、兑换目录 |

### 15.2 前端

| 文件 | 说明 |
| :--- | :--- |
| `frontend/src/views/MembershipView.vue` | 会员与积分中心：资产卡、会员卡、商城、权益、明细、赚积分、兑换弹窗 |
| `frontend/src/config/membership.js` | 档位 / 分区 / 类型 / 流水筛选等展示配置 |
| `frontend/src/utils/loyalty.js` | 阅读埋点、积分格式化、日期格式化 |
| `frontend/src/views/ProfileView.vue` | 个人中心积分与会员快捷卡 |
| `frontend/src/components/Navbar.vue` | 新增「会员积分」入口 |
| 内容详情页 | `PolicyView / ShowcaseView / DemandsView / PerksView / ForumView` 打开详情时上报阅读 |

### 15.3 V1 已知差异（后续迭代）

1. **互动积分当前即时结算**，未走 T+1 批量结算；取消互动已支持反向冲销与幂等墓碑，防刷效果等价，后续可切换为 `PENDING → SETTLED` 批处理。
2. **24 个月过期**已写入每条流水 `expires_at`，但尚未挂定时过期任务；上线前需补每日扫描。
3. **实物发货后台**未做，当前订单状态 `PAID`，需运营侧补发货与物流单号录入。
4. **数字权益**已生成订单，具体效果（置顶、AI 加量、模板解锁）需各业务域消费订单。
5. **SOP / 合规内容的阅读积分**因缺少稳定的作者 ID 字段暂未接入，发布积分已接入（SOP 在审核通过后发放）。
6. **成长等级、信誉分**已建模并影响积分倍率，但信誉分的举报/违规扣分入口尚未接入管理端。
7. **账本持久化**当前复用平台 `domain_snapshots` write-behind；生产前建议将 `points_accounts / points_ledger / memberships / orders` 迁移到独立关系表，使用数据库事务、行锁与每日对账，避免快照丢失导致账实不符。

---

## 附：一句话记住这套体系

> **积分是工资，成长值是工龄，信誉分是口碑，会员是会员卡。**
> 工资可以花，工龄不会掉，口碑坏了要修，会员卡到期要续。
