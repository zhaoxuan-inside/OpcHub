<template>
  <div v-if="visible" class="sheet-modal" @click.self="$emit('close')">
    <div class="sheet-body" style="max-width: 680px;">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
        <div style="display: flex; gap: 8px;">
          <button
            type="button"
            :class="activeTab === 'terms' ? 'btn-liquid' : 'btn-liquid-outline'"
            @click="activeTab = 'terms'"
            style="font-size: 13px;"
          >
            用户服务协议
          </button>
          <button
            type="button"
            :class="activeTab === 'privacy' ? 'btn-liquid' : 'btn-liquid-outline'"
            @click="activeTab = 'privacy'"
            style="font-size: 13px;"
          >
            隐私保护与个人信息安全指引
          </button>
        </div>
        <button class="btn-liquid-outline" style="padding: 4px 8px;" @click="$emit('close')">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <div style="font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 12px;">
        {{ activeTab === 'terms' ? 'OpcHub 平台用户服务协议 (v1.2.0)' : 'OpcHub 隐私政策与个人信息安全指引 (v1.2.0)' }}
      </div>

      <div
        style="height: 380px; overflow-y: auto; background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle); border-radius: var(--radius-sm); padding: 18px; font-size: 13px; line-height: 1.8; color: var(--text-secondary); white-space: pre-wrap;"
      >
        {{ activeContent }}
      </div>

      <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 18px;">
        <button type="button" class="btn-liquid-outline" @click="$emit('close')">
          关闭阅读
        </button>
        <button type="button" class="btn-liquid" @click="handleAgree">
          我已阅读并同意本协议
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const props = defineProps({
  visible: Boolean,
  initialTab: {
    type: String,
    default: 'terms',
  },
});

const emit = defineEmits(['close', 'agree']);

const activeTab = ref(props.initialTab || 'terms');
const agreementsData = ref(null);

const activeContent = computed(() => {
  if (!agreementsData.value) {
    return `【OpcHub 平台法定协议与个人信息保护条款】
一、 服务范围与一人公司商用准入
OpcHub 商业操作系统致力于为独立开发者、超级个体及一人公司（One-Person Company）提供合规设立、政策申报、商机外包撮合及分布式微内核业务编排。用户入驻须承诺所提供的经营资质信息真实、合法、有效。

二、 数据安全与最小必要原则
根据《中华人民共和国个人信息保护法》与《网络安全法》，平台严格秉持最小化数据收集原则。所有商用认证凭据与网络安全日志均加密留痕至少180天。

三、 支付结算与反二清防线
平台全面对接持牌金融机构，绝不归集客户沉淀资金，不从事任何形式的无牌支付结算或资金池二次清算业务。`;
  }
  if (activeTab.value === 'terms') {
    return agreementsData.value.terms_of_service?.content || agreementsData.value.terms_of_service?.summary;
  }
  return agreementsData.value.privacy_policy?.content || agreementsData.value.privacy_policy?.summary;
});

async function loadAgreements() {
  try {
    const res = await dispatchGateway('auth.legal-agreements', {});
    if (res.ok && res.data) {
      agreementsData.value = res.data;
    }
  } catch (e) {
    console.warn('Load agreements fallback', e);
  }
}

function handleAgree() {
  emit('agree');
  emit('close');
}

onMounted(() => {
  loadAgreements();
});
</script>
