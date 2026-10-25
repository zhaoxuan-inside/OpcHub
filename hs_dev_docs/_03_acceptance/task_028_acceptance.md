# 任务验收备忘：TASK-028 内置画像头像（20 种用户画像 · 换头像能力）

- **任务编号**：TASK-028
- **任务标题**：内置画像头像与创客自主更换头像
- **分级**：`M`
- **执行人**：agent
- **完成时间**：`2026-10-25T12:55:00+08:00`
- **状态**：`VERIFIED_AND_ACCEPTED`

---

## 1. 交付产物与实现细节

1. **内置画像头像目录 (`frontend/src/components/personaAvatarCatalog.js`)**：
   - 20 种常见创客用户画像：独立开发者 / 产品设计师 / 内容创作者 / 创业者 / 电商卖家 / 咨询顾问 / 摄影师 / 插画师 / 视频博主 / 音乐人 / 知识讲师 / 财税顾问 / 法律顾问 / 跨境卖家 / 独立研究员 / 手工艺人 / 健身教练 / 美食创作者 / 旅行博主 / 新农人。
   - **人物头像形态**（按用户反馈修订：初版为职业图标，已全部重绘为人像）：每个画像是「一个人」——圆脸 + 五官 + 发型（短发/长发/刘海/侧分/丸子头/马尾/卷发/寸头）+ 肤色（6 档）+ 帽饰（毛线帽/棒球帽/头巾）+ 配饰（眼镜/胡须/耳环/腮红）+ 服饰组合，风格对齐 Notion 内置头像的扁平人像。
   - 全部为内联 SVG（64×64 视窗），零外部图片资源依赖；附昵称稳定散列兜底色。

2. **头像渲染组件 (`frontend/src/components/PersonaAvatar.vue`)**：
   - `id / name / size` 三属性；画像 id 未收录或为空时自动回退昵称首字圆标。
   - 单一组件同时服务导航栏（22px）、档案头（72px）、选择器网格（46px）与论坛编辑位（38px）。

3. **档案头像字段与白名单校验（后端）**：
   - `MakerProfileResponse` / `UserProfileUpdateRequest` 新增 `avatar_id`（`backend/src/domains/user/models.py`）。
   - `UserService` 以 `BUILTIN_AVATAR_IDS`（20 项 frozenset）做服务端白名单校验，非法标识直接拒绝且不改动既有档案；空串表示重置为首字头像（`backend/src/domains/user/service.py`）。
   - 内存索引即时生效 + `users.metadata_payload` 持久化（重启后由 `_record_from_db_user` 回灌）；`user_profile_update_adapter` 透传 `avatar_id`（`backend/src/core/gateway/adapters.py`）。
   - 读链路零改动：`user.profile`（DAG OPC_USER_PROFILE_PIPELINE）与 `auth.session` 均返回模型全量字段，自动携带 `avatar_id`。

4. **前端更换入口与全站生效**：
   - 个人档案页新增「更换画像头像」入口与 20 宫格选择面板（选中高亮、保存/取消）；保存走 `user.profile.update` 写链路（`frontend/src/views/ProfileView.vue`）。
   - 保存成功后刷新本地会话档案并向上抛 `session-updated`，导航栏头像即时换新无需刷新（`frontend/src/App.vue`、`frontend/src/components/Navbar.vue`）。
   - 头脑风暴编辑位（编辑讨论帖 / 撰写观点）使用当前用户画像头像（`frontend/src/components/ForumDetailView.vue`）。
   - 其他用户展示位（帖子卡片、评论区等）维持既有首字圆标兜底形态——后端列表契约暂未携带作者头像字段，属后续扩展项而非死代码。

## 2. 自动化与浏览器验收证据

1. **后端 pytest**：`tests/test_persona_avatar.py` 4 项（保存/切换/清空回显、白名单拒绝且原值保持、目录完整性 20 项与前端 id 集合一致、访客空头像）；连带回归 `test_user_dag_pipeline.py`、`test_auth_and_persistence.py`、`test_commercial_registration.py` 全部通过（8 + 18 passed）。
2. **浏览器 E2E（真实 UI 操作）**：个人页打开选择面板（20 画像全部渲染）→ 选择「摄影师」→ 保存按钮由禁用转可用 → 保存后面板关闭、导航栏与档案头两处头像即时切换 → 刷新页面后头像保持（服务端持久化回路）。
3. **人像形态独立视觉校验**（初版图标改版后）：截取 20 宫格画面交视觉模型评审——确认全部为人物头像（脸部+发型+五官，非相机/火箭等职业物体图标）、20 个画像之间发型/肤色/帽饰/眼镜差异明显、无畸形错位条目。
4. **文案合规**：全部界面文案无实现术语（无 SVG/字段/接口名），产品语气完整。

## 3. 边界与已知非目标

- 头像仅内置 20 种画像，不做本地上传（按需求约定）。
- 论坛信息流等其他用户的头像展示需要列表契约扩展 `author_avatar_id`，本任务未包含，现有首字圆标为设计内兜底。
