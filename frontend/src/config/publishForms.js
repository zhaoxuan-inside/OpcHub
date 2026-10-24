/**
 * Shared publish form schemas.
 *
 * All publish boards (policy / product / demand / perk / compliance) render
 * through a single <PublishForm> component. Keeping the field definitions here
 * avoids duplicating form markup across views and keeps the visual rhythm
 * identical.
 *
 * Layout contract (统一编辑体验)：
 * - 正文优先：标题与富文本正文置于最前，无分组标题干扰；
 * - 分区/类别等枚举一律下拉选择（type: 'select'）；
 * - 正文用 type: 'richtext'（Markdown + 富文本双模式），图标用 type: 'icon'
 *   （仅内置图标库，不支持上传），两者自动占满整行。
 */

export const POLICY_FIELDS = [
  { key: 'title', label: '政策公文标题', type: 'text', required: true, span: 2,
    placeholder: '如：国家高新技术企业所得税15%税收优惠' },
  { key: 'summary', label: '白话提炼摘要（正文）', type: 'richtext', required: true,
    placeholder: '【白话要点】简明扼要说明红利要点、受惠对象、节税额度与关键指标……支持标题、列表、表格与高亮提示框。' },

  { section: '分区与属性' },
  { key: 'policy_level', label: '发文层级', type: 'select',
    options: [
      { value: '国家级', label: '国家级' },
      { value: '省市级', label: '省市级' },
      { value: '园区级', label: '园区级' },
    ] },
  { key: 'category', label: '扶持类别', type: 'select',
    options: [
      { value: 'TAX', label: 'TAX（税费减免）' },
      { value: 'SUBSIDY', label: 'SUBSIDY（直接补贴）' },
      { value: 'RENT', label: 'RENT（场地免租）' },
      { value: 'TALENT', label: 'TALENT（人才激励）' },
    ] },
  { key: 'region', label: '适用区域', type: 'text', placeholder: '如：长三角 / 全国统一 / 深圳南山' },
  { key: 'code', label: '政策编号', type: 'text', placeholder: '如：POL-2026-130' },
  { key: 'subsidy_amount_max', label: '最高扶持金额（元）', type: 'number', min: 0, placeholder: '0' },
  { key: 'deadline', label: '申报截止期限', type: 'text', placeholder: '如：常年开放申报 / 2026-12-31' },
  { key: 'conditionsText', label: '适用资格条件', type: 'text', span: 2,
    placeholder: '以逗号分隔，如：科技型中小企业, 软件研发从业者, 一人公司' },

  { section: '依据' },
  { key: 'legal_basis', label: '官方法规公文依据', type: 'text', required: true, span: 2,
    placeholder: '如：财政部 税务总局公告 2023年第12号' },
];

export const PRODUCT_FIELDS = [
  { key: 'title', label: '产品名称', type: 'text', required: true, placeholder: '如：InkFlow AI 专注编辑器' },
  { key: 'version', label: '软件版本', type: 'text', placeholder: '如：v1.0.0' },
  { key: 'tagline', label: '一句话卖点简介', type: 'text', required: true, span: 2,
    placeholder: '如：专为长文研究员与独立小说家打造的本地离线增强写作工作台' },
  { key: 'description', label: '详细应用介绍（正文）', type: 'richtext', required: true,
    placeholder: '详细介绍产品核心功能、应用场景、技术亮点与解决的用户痛点……支持标题、列表、代码块与表格。' },

  { section: '上架设置' },
  { key: 'category', label: '应用分区', type: 'select',
    options: ['AI 原生写作', '跨境出海', '开发工具', '微SaaS工具', '自动化工作流', '设计系统'] },
  { key: 'pricing_model', label: '商业计费模式', type: 'select',
    options: [
      { value: 'FREE', label: '免费体验' },
      { value: 'FREEMIUM', label: '免费增值（Freemium）' },
      { value: 'ONE_TIME', label: '买断制（One-Time）' },
      { value: 'SUBSCRIPTION', label: '周期订阅（Subscription）' },
    ] },
  { key: 'price_cny', label: '参考定价（元）', type: 'number', min: 0, step: 0.01, placeholder: '0.00',
    visible: (model) => model.pricing_model !== 'FREE' },

  { section: '图标与链接' },
  { key: 'icon_url', label: '应用图标', type: 'icon', span: 2,
    hint: '仅支持从平台内置图标库选择，不支持外部图片上传；留空使用名称首字占位。' },
  { key: 'official_url', label: '官方网站', type: 'url', placeholder: 'https://yourproduct.com' },
  { key: 'download_url', label: '安装包下载地址', type: 'url', placeholder: 'https://download.yourproduct.com/setup.dmg' },
  { key: 'demo_url', label: '在线体验或演示链接', type: 'url', span: 2, placeholder: 'https://yourproduct.com/demo' },
];

export const DEMAND_FIELDS = [
  { key: 'title', label: '委托标题', type: 'text', required: true, span: 2,
    placeholder: '如：外贸 CRM 系统的垂直行业 Agent 工作流搭建' },
  { key: 'description', label: '详细需求说明（正文）', type: 'richtext', required: true,
    placeholder: '详细描述技术栈、交付物、验收标准与期望周期……支持标题、列表、代码块与表格。' },

  { section: '预算与周期' },
  { key: 'category', label: '商机分区', type: 'select',
    options: [
      { value: 'DEV', label: '技术开发' },
      { value: 'AI', label: 'AI 智能体' },
      { value: 'TAX', label: '财税合规' },
      { value: 'LEGAL', label: '法律求助' },
      { value: 'BIZ', label: '商业运营' },
    ] },
  { key: 'budget_cny', label: '托管预算（元）', type: 'number', min: 0, step: 100, placeholder: '35000' },
  { key: 'deadline_days', label: '交付周期（天）', type: 'number', min: 1, max: 365, placeholder: '14' },
];

export const PERK_FIELDS = [
  { key: 'name', label: '公告标题', type: 'text', required: true, span: 2,
    placeholder: '如：火山方舟 豆包大模型 Token 畅用券' },
  { key: 'summary', label: '公告摘要（正文）', type: 'richtext', required: true,
    placeholder: '【白话要点】简明扼要说明优惠力度、适用范围与限制条件……支持标题、列表与高亮提示框。' },

  { section: '领取设置' },
  { key: 'provider', label: '服务商', type: 'text', required: true, placeholder: '如：火山引擎方舟 / 阿里云' },
  { key: 'category', label: '优惠分区', type: 'select', options: [] },
  { key: 'value_cny', label: '预估价值（元）', type: 'number', min: 0, placeholder: '0' },
  { key: 'quota_remaining', label: '领取配额', type: 'number', min: 1, placeholder: '100' },
  { key: 'effective_start', label: '生效时间', type: 'date' },
  { key: 'effective_end', label: '截止时间', type: 'date' },
  { key: 'redeem_url', label: '领取 / 详情直达链接', type: 'url', span: 2,
    placeholder: '如：https://console.volcengine.com/ark' },
  { key: 'highlightsText', label: '核心卖点', type: 'text', span: 2,
    placeholder: '以逗号分隔，如：豆包全系可用, 抵扣额度 ¥5,000, 新老创客均可领取' },
];

/**
 * 合规指南（法条 / 案例）发布 schema。
 * kind 决定后续字段的可见性；法条正文与案例背景使用富文本。
 */
export const COMPLIANCE_FIELDS = [
  { key: 'kind', label: '收录类型', type: 'select', required: true,
    options: [
      { value: 'law', label: '法条 · 法律法规白话提炼' },
      { value: 'case', label: '案例 · 监管处罚与避坑教训' },
    ] },
  { key: 'title', label: '标题', type: 'text', required: true, span: 2,
    placeholder: '如：个人信息保护法 · 最小必要原则' },

  { section: '法条要素', visible: (model) => model.kind === 'law' },
  { key: 'summary', label: '白话要点', type: 'text', required: true, span: 2,
    placeholder: '简明说明法条核心要求与适用对象', visible: (model) => model.kind === 'law' },
  { key: 'level', label: '效力级别', type: 'select',
    options: ['法律', '行政法规', '部门规章', '地方性法规'], visible: (model) => model.kind === 'law' },
  { key: 'issuer', label: '发布机关', type: 'text', placeholder: '如：全国人民代表大会常务委员会',
    visible: (model) => model.kind === 'law' },
  { key: 'published_at', label: '发布日期', type: 'text', placeholder: '如：2021-08-20',
    visible: (model) => model.kind === 'law' },
  { key: 'code', label: '法条编号', type: 'text', placeholder: '如：LAW-07',
    visible: (model) => model.kind === 'law' },
  { key: 'content', label: '核心条文内容（正文）', type: 'richtext',
    placeholder: '摘录或提炼法条核心条文……支持标题、列表与高亮提示框。',
    visible: (model) => model.kind === 'law' },
  { key: 'penalties', label: '违规罚则', type: 'text', span: 2,
    placeholder: '违反本法的法律责任……', visible: (model) => model.kind === 'law' },
  { key: 'law_ref', label: '官方法条依据', type: 'text', required: true, span: 2,
    placeholder: '如：《个人信息保护法》第十三条', visible: (model) => model.kind === 'law' },

  { section: '案例要素', visible: (model) => model.kind === 'case' },
  { key: 'industry', label: '涉及行业', type: 'text', placeholder: '如：微支付 / 工具聚合',
    visible: (model) => model.kind === 'case' },
  { key: 'badge', label: '徽章文案', type: 'text', placeholder: '如：二清违规冻结 · 涉案 68 万元',
    visible: (model) => model.kind === 'case' },
  { key: 'violation', label: '案情背景与违规事实（正文）', type: 'richtext', required: true,
    placeholder: '描述违规行为与背景……支持标题、列表与高亮提示框。',
    visible: (model) => model.kind === 'case' },
  { key: 'consequence', label: '监管处罚结果', type: 'text', required: true, span: 2,
    placeholder: '处罚结果……', visible: (model) => model.kind === 'case' },
  { key: 'lesson', label: '避坑经验', type: 'text', required: true, span: 2,
    placeholder: '给创客的避坑建议……', visible: (model) => model.kind === 'case' },
];
