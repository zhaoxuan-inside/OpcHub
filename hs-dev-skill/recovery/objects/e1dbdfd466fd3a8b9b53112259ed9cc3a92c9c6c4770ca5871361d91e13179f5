<template>
  <div class="view-panel active">
    <!-- Header -->
    <div class="glass-box" style="padding: 24px 32px 18px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
            <h1 class="page-title" style="font-size: 26px; margin: 0;">产品开发合规指南</h1>
            <span class="mono-tag" style="background: rgba(52, 199, 89, 0.12); color: #34C759; border-color: rgba(52, 199, 89, 0.3);">
              六维合规防线体系
            </span>
          </div>
          <p style="font-size: 13px; color: var(--text-secondary);">
            六维合规防线体系 · 典型避坑案例剖析 · 上线前合规自检雷达
          </p>
        </div>
        <div style="display: flex; gap: 10px;">
          <button class="btn-liquid-outline" @click="activeSubTab = 'radar'">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/>
            </svg>
            <span>自检雷达</span>
          </button>
          <button class="btn-liquid" @click="$emit('switch-tab', 'demand')">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
            </svg>
            <span>法律求助</span>
          </button>
        </div>
      </div>

      <!-- Segment Tabs -->
      <div style="display: flex; gap: 8px; margin-top: 16px; border-top: 1px solid var(--glass-border-subtle); padding-top: 14px; flex-wrap: wrap;">
        <button
          class="btn-liquid-outline"
          :class="{ active: activeSubTab === 'dimensions' }"
          style="padding: 5px 14px; font-size: 12.5px;"
          @click="activeSubTab = 'dimensions'"
        >
          六维防线
        </button>
        <button
          class="btn-liquid-outline"
          :class="{ active: activeSubTab === 'cases' }"
          style="padding: 5px 14px; font-size: 12.5px;"
          @click="activeSubTab = 'cases'"
        >
          避坑案例
        </button>
        <button
          class="btn-liquid-outline"
          :class="{ active: activeSubTab === 'radar' }"
          style="padding: 5px 14px; font-size: 12.5px; color: var(--accent); border-color: rgba(0,113,227,0.3);"
          @click="activeSubTab = 'radar'"
        >
          自检雷达
        </button>
      </div>
    </div>

    <!-- Tab 1: Dimensions Grid -->
    <div v-if="activeSubTab === 'dimensions'" class="grid-3" style="margin-top: 18px;">
      <div v-for="d in dimensions" :key="d.code" class="glass-card">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <span class="mono-tag" style="background: rgba(0,113,227,0.15); color: var(--accent);">{{ d.name }}</span>
            <span style="font-size: 11px; font-family: var(--font-mono); color: var(--text-tertiary);">{{ d.code }}</span>
          </div>
          <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 6px;">{{ d.title }}</h3>
          <p style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 12px;">
            {{ d.desc }}
          </p>
          <div style="background: var(--glass-surface-subtle); padding: 8px 10px; border-radius: var(--radius-sm); font-size: 11.5px; color: #ef4444; margin-bottom: 12px;">
            ⚠️ 违规罚则: {{ d.penalty }}
          </div>
        </div>
        <div style="font-size: 11.5px; color: var(--text-tertiary); border-top: 1px solid var(--glass-border-subtle); padding-top: 10px;">
          法条依据: {{ d.law }}
        </div>
      </div>
    </div>

    <!-- Tab 2: Pitfall Cases -->
    <div v-else-if="activeSubTab === 'cases'" style="display: flex; flex-direction: column; gap: 14px; margin-top: 18px;">
      <div v-for="c in pitfallCases" :key="c.title" class="glass-card" :style="{ borderLeft: `4px solid ${c.color}`, padding: '20px 24px' }">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px;">
          <span class="mono-tag" :style="{ background: c.badgeBg, color: c.color, fontWeight: '600' }">{{ c.badge }}</span>
          <span style="font-size: 12px; color: var(--text-tertiary);">{{ c.industry }}</span>
        </div>
        <h3 style="font-size: 16px; margin-bottom: 6px;">{{ c.title }}</h3>
        <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.6; margin-bottom: 10px;">
          <strong>【案情背景】</strong> {{ c.background }}
          <br><strong>【监管处罚】</strong> {{ c.penalty }}
        </div>
        <div style="background: var(--glass-surface-subtle); padding: 10px 14px; border-radius: var(--radius-sm); font-size: 12.5px; color: var(--accent);">
          💡 <strong>避坑经验：</strong> {{ c.tip }}
        </div>
      </div>
    </div>

    <!-- Tab 3: Interactive Self-Audit Radar -->
    <div v-else-if="activeSubTab === 'radar'" style="margin-top: 18px;">
      <div class="glass-card" style="padding: 24px 28px; margin-bottom: 18px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; margin-bottom: 16px;">
          <div>
            <div style="font-size: 12px; font-family: var(--font-mono); color: var(--text-tertiary); margin-bottom: 4px;">
              COMPLIANCE SAFETY SCORE
            </div>
            <div style="display: flex; align-items: baseline; gap: 8px;">
              <span style="font-size: 42px; font-weight: 700; font-family: var(--font-display); letter-spacing: -0.03em; color: var(--accent);">
                {{ auditScore }}
              </span>
              <span style="font-size: 15px; color: var(--text-tertiary);">/ 100 分</span>
              <span class="mono-tag" style="background: rgba(52,199,89,0.15); color: #34C759; margin-left: 6px;">
                {{ auditScore >= 90 ? '极佳合规' : '存在合规风险' }}
              </span>
            </div>
          </div>
          <div style="display: flex; gap: 10px;">
            <button class="btn-liquid-outline" style="padding: 6px 14px; font-size: 12px;" @click="resetAudit">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
              </svg>
              <span>重置自测</span>
            </button>
            <button class="btn-liquid" style="padding: 6px 14px; font-size: 12px;" @click="$emit('switch-tab', 'demand')">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
              </svg>
              <span>发布法务委托</span>
            </button>
          </div>
        </div>

        <!-- Progress Bar -->
        <div style="height: 8px; background: var(--glass-surface-subtle); border-radius: 4px; overflow: hidden; margin-bottom: 12px;">
          <div :style="{ width: `${auditScore}%`, height: '100%', background: auditScore >= 90 ? '#34C759' : '#FF9500', transition: 'width 0.4s ease' }"></div>
        </div>
        <div style="font-size: 12.5px; color: var(--text-secondary);">
          {{ auditScore === 100 ? '✅ 恭喜！当前 10 项核心合规检查点全部达标，满足境内上线与合规展业标准。' : '⚠️ 提示：仍有检查项未完成勾选，建议在正式商用上线前逐一整改。' }}
        </div>
      </div>

      <!-- 10 Checkpoints List -->
      <div class="glass-box" style="padding: 20px 24px;">
        <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 14px;">创客产品上线前 10 项标准化合规自检清单</h3>
        <div style="display: flex; flex-direction: column; gap: 12px;">
          <label
            v-for="(item, index) in checkpoints"
            :key="index"
            style="display: flex; align-items: flex-start; gap: 10px; cursor: pointer; padding: 10px 14px; border-radius: var(--radius-sm); background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle);"
          >
            <input type="checkbox" v-model="item.checked" style="margin-top: 3px; accent-color: var(--accent);" />
            <div>
              <div style="font-size: 13.5px; font-weight: 600; color: var(--text-primary);">
                {{ item.title }}
              </div>
              <div style="font-size: 12px; color: var(--text-secondary); margin-top: 2px;">
                {{ item.desc }}
              </div>
            </div>
          </label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

defineEmits(['switch-tab']);

const activeSubTab = ref('dimensions');

const dimensions = [
  {
    code: 'DIM-01',
    name: '个人隐私安全',
    title: '独立隐私指引与最小化采集合规',
    desc: '前端注册必须提供《隐私政策》勾选并默认不选中；严禁未授权采集用户剪贴板、通讯录及精准地理位置。',
    penalty: '责令下架或暂停涉案 App 服务，处以违法所得 1~5 倍罚款。',
    law: '《个人信息保护法》第13条、第47条',
  },
  {
    code: 'DIM-02',
    name: '支付结算反二清',
    title: '严禁设立私有资金池与自建分账',
    desc: '平台严禁触碰交易资金，全量接入持牌机构商户分账（如微信分账、支付宝直付通），交易款项由银行直连划付。',
    penalty: '没收违法所得并处以 50 万元以上罚款，涉嫌非法吸收公众存款罪。',
    law: '《中国人民银行支付结算办法》银发〔2017〕217号',
  },
  {
    code: 'DIM-03',
    name: '开源许可证治理',
    title: '杜绝 AGPL 强传染性代码侵入闭源组件',
    desc: '商业闭源模块严格选用 MIT、Apache-2.0 许可证组件；引入 GPL/AGPL 代码必须在 CI 门禁中断拦截。',
    penalty: '法院判决强制开源商业核心代码，并赔偿权利人知识产权损失。',
    law: '《著作权法》第49条及开源许可司法裁判先例',
  },
  {
    code: 'DIM-04',
    name: '网络安全与审计',
    title: 'IP属地展示与180天访问日志留存',
    desc: '社区交流强制标注发帖人属地；网关前置拦截涉违禁敏感词；系统审计与网络访问日志必须加密留存至少 180 天。',
    penalty: '责令停机整顿，吊销增值电信业务经营许可（ICP/EDI）。',
    law: '《网络安全法》第21条、《互联网用户账号管理规定》',
  },
  {
    code: 'DIM-05',
    name: '跨境数据合规',
    title: '境外用户数据评估与出境申报通道',
    desc: '出海应用向境外传输境内公民个人信息超过阈值，必须依法向网信部门申报数据出境安全评估。',
    penalty: '通报批评并责令停止数据跨境传输，暂停境外展业资格。',
    law: '《数据出境安全评估办法》网信办令第11号',
  },
  {
    code: 'DIM-06',
    name: '商事与财税合规',
    title: '开票合规与增值税小微免税申报',
    desc: '按期登录电子税务局完成小微免税纳税申报；真实业务发生后开具发票，坚决杜绝虚开或偷逃增值税。',
    penalty: '补缴税款与滞纳金，并处少缴税款百分之五十以上五倍以下罚款。',
    law: '《税收征收管理法》第63条、财税〔2023〕12号',
  },
];

const pitfallCases = [
  {
    title: '某知名独立开发者工具因内嵌资金池涉二清被微信支付永久封号',
    badge: '二清违规冻结 · 涉案 68 万元',
    badgeBg: 'rgba(239,68,68,0.15)',
    color: '#ef4444',
    industry: '微支付 / 工具聚合行业',
    background: '某独立开发者搭建团队任务众包工具，在前端为用户提供充值钱包，开发者个人银行卡作为资金池中转结算，每周人工给创客分账打款。',
    penalty: '触发央行反洗钱备付金监控模型，商户号被微信支付风控永久冻结账户余额 68 万元并移交金融办排查。',
    tip: '平台绝不触碰资金！全量接入持牌机构商户分账（如微信分账、支付宝直付通），交易款项由牌照机构在底层完成结算拆分。',
  },
  {
    title: '某海外出海 SaaS 因未提供数据注销与遗忘通道被欧盟重罚',
    badge: 'GDPR 隐私罚单 · 处罚 12 万欧元',
    badgeBg: 'rgba(249,115,22,0.15)',
    color: '#f97316',
    industry: '海外出海工具行业',
    background: '一款出海 AI 笔记软件仅在个人中心提供退出登录，用户多次申请彻底注销账号并删除云端笔记，均被客服拒绝。',
    penalty: '欧盟数据保护委员会（EDPB）认定其严重违反 GDPR “被遗忘权”，处以 12 万欧元行政罚款并限制展业。',
    tip: '产品开发前置落地“账号安全注销通道”，用户确认后必须在后端完成个人敏感信息的不可逆脱敏或物理清除。',
  },
  {
    title: '某商业闭源项目误引 AGPL-3.0 模块被法院判决限期开源商业代码',
    badge: '开源传染诉讼 · 强制开源核心代码',
    badgeBg: 'rgba(234,179,8,0.15)',
    color: '#eab308',
    industry: '企业级 SaaS 行业',
    background: '某商业 SaaS 在核心微服务中静态链接引入了某开源项目 AGPL-3.0 协议分析代码，未依法向用户开放全量源码。',
    penalty: '法院裁定该闭源商业组件构成 AGPL 衍生作品，判令其履行开源许可义务，限期公开核心业务代码。',
    tip: '建立 CI/CD 开源许可证扫描门禁，商业闭源模块严格选用 MIT、Apache-2.0 许可证组件，杜绝 GPL/AGPL 强传染性风险。',
  },
];

const checkpoints = ref([
  { title: '注册同意机制默认不勾选', desc: '《用户服务协议》与《隐私政策》已提供完整正文，注册复选框未被默认勾选', checked: true },
  { title: '提供清晰便捷的账号注销路径', desc: '在个人创客中心提供注销账号入口，并提示不可逆风险', checked: true },
  { title: '全站 HTTPS 与敏感字段单向加密', desc: '全链路 TLS 1.3，数据库用户密码采用 Argon2id / bcrypt 加密存储', checked: true },
  { title: '第三方支付通过持牌机构直连分账', desc: '不自建沉淀资金池，通过官方微信/支付宝商户完成受托结算', checked: true },
  { title: 'UGC 社区发帖包含 IP 属地展示', desc: '在头脑风暴社区与作品评论中真实展示发表人省级/境外 IP 归属', checked: true },
  { title: '敏感违规词前置网关初筛', desc: '涉暴、涉恐、资金盘违禁词由网关 Sentinel 前置阻断，不入库存储', checked: true },
  { title: '系统访问与审计日志加密留痕 180 天', desc: '符合网络安全法要求，访问请求记录与溯源日志留存至少 6 个月', checked: true },
  { title: '开源组件无 AGPL/GPL 强传染性依赖', desc: '生产依赖经扫描均为 MIT、Apache-2.0、BSD 标准宽容协议', checked: true },
  { title: '出海应用跨境个人信息出境合规备案', desc: '涉及欧洲与北美用户严格遵守 GDPR 与 CCPA 权利行使指引', checked: true },
  { title: '商用发票与小微免税如实记账申报', desc: '一人公司经营收入纳入记账凭证，每季度依法向税务局按时申报', checked: true },
]);

const auditScore = computed(() => {
  const total = checkpoints.value.length;
  const passed = checkpoints.value.filter((i) => i.checked).length;
  return Math.round((passed / total) * 100);
});

function resetAudit() {
  checkpoints.value.forEach((i) => (i.checked = true));
}
</script>
