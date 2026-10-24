<template>
  <aside
    class="content-disclaimer-wrapper"
    :class="[`disclaimer-${mode}`, { 'disclaimer-compact': compact }]"
    role="note"
    aria-label="免责声明"
  >
    <div class="disclaimer-header">
      <div class="disclaimer-badge">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
        </svg>
        <span>{{ displayTitle }}</span>
      </div>
      <span class="disclaimer-ugc-hint">用户自主发布 · 平台免责</span>
    </div>

    <p class="disclaimer-text">
      {{ displayText }}
    </p>

    <div v-if="displaySubtext && !compact" class="disclaimer-footer">
      <span class="disclaimer-tip">{{ displaySubtext }}</span>
      <span class="disclaimer-tag">OpcHub 合规公约</span>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  type: {
    type: String,
    default: 'general', // 'forum' | 'showcase' | 'product' | 'policy' | 'demand' | 'sop' | 'perk' | 'compliance' | 'general'
  },
  mode: {
    type: String,
    default: 'banner', // 'banner' | 'card' | 'inline'
  },
  title: {
    type: String,
    default: '',
  },
  text: {
    type: String,
    default: '',
  },
  subtext: {
    type: String,
    default: '',
  },
  compact: {
    type: Boolean,
    default: false,
  },
});

const DISCLAIMER_MAP = {
  forum: {
    title: '头脑风暴免责声明',
    text: '头脑风暴社区内容由创客用户自主发布，仅代表作者个人观点与实战探索，不代表平台立场。平台不对内容的真实性、时效性、完整性或操作后果作任何明示或暗示的保证或背书。内容仅供交流学习，不构成商业投资、法律合规或技术实施承诺；请结合自身业务场景审慎评估风险。',
    subtext: '如发现违法违规、虚假宣传或侵权内容，请及时点击举报。',
  },
  showcase: {
    title: '产品橱窗免责声明',
    text: '产品橱窗所展示的独立作品、工具及服务规格均由创客或企业主体自主发布与维护，平台仅提供展示与交流渠道，不对产品质量、可用性、交易履约及第三方数据安全提供担保。用户在体验、下载或采购前请自行核实开发者资质及服务条款。',
    subtext: '商业交易与软件使用前请自行审慎评估，如遇侵权违规请向平台举报。',
  },
  product: {
    title: '产品橱窗免责声明',
    text: '产品橱窗所展示的独立作品、工具及服务规格均由创客或企业主体自主发布与维护，平台仅提供展示与交流渠道，不对产品质量、可用性、交易履约及第三方数据安全提供担保。用户在体验、下载或采购前请自行核实开发者资质及服务条款。',
    subtext: '商业交易与软件使用前请自行审慎评估，如遇侵权违规请向平台举报。',
  },
  policy: {
    title: '政策中心免责声明',
    text: '政策中心所收录的政策解读、白话要点及测算数据由用户及合作方整理提报，旨在降低小微与个体经营者的信息门槛，仅供学习交流与申报参考，不构成任何行政审批、资质认定或财政补贴承诺。申报准入条件、申报期限与扶持额度均以国家及各级政府主管机关正式红头文件为准。',
    subtext: '具体申报资格与款项审批以各属地政务部门最终核定为准。',
  },
  demand: {
    title: '需求集市免责声明',
    text: '需求集市展示的企业商机、外包需求及预算信息均由委托方用户自主发布。平台仅提供供需撮合与信息展示服务，不对委托方资信、需求真实性、项目交付质量或最终结算款项承担连带担保责任。双方洽谈合作建议签署正规法律合同并审慎核实对方资质。',
    subtext: '合作洽谈请防范商业风险，建议走正规合同签约与履约流程。',
  },
  sop: {
    title: '流程文书免责声明',
    text: '流程文书与模板由用户及社区整理共享，属于标准化辅助起草参考工具，不构成任何执业律师、注册会计师或税务师的正式法律、税务、工商或投资意见。正式签署盖章或提交行政审批前，请自行核对当事人真实意愿与最新法规口径，必要时请咨询执业专业人士。',
    subtext: '文书仅供辅助起草，正式法律行为请由具备资质的专业人员把关。',
  },
  perk: {
    title: '生态特权免责声明',
    text: '生态特权所展示的优惠折扣、福利券与特权公告由生态伙伴或用户提报，平台仅作信息聚合与展示，不对权益兑现、服务稳定性或后续收费政策提供担保。各项特权的适用范围、有效期及领取门槛均以第三方服务商官方公布规则为准。',
    subtext: '第三方服务商保留活动调整权利，平台不对第三方履约承担担保责任。',
  },
  compliance: {
    title: '合规指南免责声明',
    text: '合规指南收录之法条白话提炼与典型避坑案例由社区用户共同整理与分享，仅作为行业常识科普与合规参考，不构成针对特定主体或纠纷的正式法律诊断、合规意见或诉讼指引。企业及个人在处理涉法涉税事务时，应以国家现行法律法规文本及行政/司法正式裁决为法定依据。',
    subtext: '具体涉法涉税事务请以国家现行法律法规及主管机关权威文件为准。',
  },
  general: {
    title: '平台免责声明',
    text: '本平台各版块内容均支持注册用户自主发布与提报，平台不对内容的真实性、准确性、时效性或合法性做任何明示或暗示的担保或背书。内容仅供参考，不构成任何法律、税务、投资或商业合作建议。',
    subtext: '如发现虚假、违规或侵犯他人合法权益之内容，请向平台进行投诉举报。',
  },
};

const currentConfig = computed(() => {
  const key = (props.type || 'general').toLowerCase();
  return DISCLAIMER_MAP[key] || DISCLAIMER_MAP.general;
});

const displayTitle = computed(() => props.title || currentConfig.value.title);
const displayText = computed(() => props.text || currentConfig.value.text);
const displaySubtext = computed(() => props.subtext || currentConfig.value.subtext);
</script>

<style scoped>
.content-disclaimer-wrapper {
  box-sizing: border-box;
  font-family: inherit;
  transition: all 0.2s ease;
}

/* Banner Mode (详情页 / 展示正文下方嵌入) */
.content-disclaimer-wrapper.disclaimer-banner {
  margin: 22px 0 16px;
  padding: 14px 18px;
  border-radius: var(--radius-md, 12px);
  background: rgba(0, 113, 227, 0.035);
  border: 1px solid var(--glass-border-subtle, rgba(120, 130, 150, 0.2));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.5);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Card Mode (侧边栏卡片) */
.content-disclaimer-wrapper.disclaimer-card {
  margin: 0;
  padding: 16px 18px;
  border-radius: var(--radius-md, 12px);
  background: var(--glass-surface, rgba(255, 255, 255, 0.7));
  backdrop-filter: var(--blur-strength, blur(16px) saturate(160%));
  -webkit-backdrop-filter: var(--blur-strength, blur(16px) saturate(160%));
  border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.85));
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Header */
.disclaimer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.disclaimer-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 9px;
  border-radius: 999px;
  background: rgba(0, 113, 227, 0.09);
  color: var(--accent, #0071e3);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.03em;
  line-height: 1.5;
}

.disclaimer-ugc-hint {
  font-size: 11px;
  color: var(--text-tertiary, #7d828d);
  letter-spacing: 0.02em;
}

/* Text */
.disclaimer-text {
  margin: 0;
  color: var(--text-secondary, #4b4e56);
  font-size: 12px;
  line-height: 1.65;
  text-align: justify;
}

/* Footer */
.disclaimer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 6px;
  border-top: 1px dashed var(--glass-border-subtle, rgba(120, 130, 150, 0.15));
  font-size: 11px;
}

.disclaimer-tip {
  color: var(--text-tertiary, #7d828d);
  line-height: 1.4;
}

.disclaimer-tag {
  flex-shrink: 0;
  color: var(--text-tertiary, #7d828d);
  font-size: 10.5px;
}

/* Compact mode */
.content-disclaimer-wrapper.disclaimer-compact {
  padding: 8px 12px;
  gap: 4px;
}

.content-disclaimer-wrapper.disclaimer-compact .disclaimer-text {
  font-size: 11.5px;
}

/* Dark theme */
[data-theme='dark'] .content-disclaimer-wrapper.disclaimer-banner {
  background: rgba(41, 151, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.1);
  box-shadow: none;
}

[data-theme='dark'] .content-disclaimer-wrapper.disclaimer-card {
  background: rgba(26, 29, 36, 0.7);
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

[data-theme='dark'] .disclaimer-badge {
  background: rgba(41, 151, 255, 0.15);
  color: var(--accent, #2997ff);
}

[data-theme='dark'] .disclaimer-text {
  color: var(--text-secondary, #a6acba);
}

[data-theme='dark'] .disclaimer-ugc-hint,
[data-theme='dark'] .disclaimer-tip,
[data-theme='dark'] .disclaimer-tag {
  color: var(--text-tertiary, #757c8a);
}

[data-theme='dark'] .disclaimer-footer {
  border-top-color: rgba(255, 255, 255, 0.08);
}
</style>
