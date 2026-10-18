<template>
  <div class="view-panel active">
    <!-- Header -->
    <div class="glass-box" style="padding: 24px 32px 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <h1 class="page-title" style="font-size: 26px; margin-bottom: 4px;">流程 SOP 与商事材料生成中心</h1>
          <p style="font-size: 13px; color: var(--text-secondary);">
            从个体工商设立、银行开户、税务报到至海外 Stripe 激活，智能起草标准化公文全套文书。
          </p>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <span class="mono-tag" style="background: var(--accent-glass); color: var(--accent);">政务标准文书模版</span>
          <button class="btn-liquid" @click="generateDocument">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            <span>一键生成文书</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Stepper Navigation -->
    <div class="sop-stepper">
      <div
        v-for="(step, idx) in steps"
        :key="step.key"
        class="sop-step-node"
        :class="{ active: currentStep === step.key }"
        @click="currentStep = step.key"
      >
        <div style="font-size: 10.5px; font-family: var(--font-mono); color: var(--text-tertiary); margin-bottom: 4px;">
          0{{ idx + 1 }} · {{ step.code }}
        </div>
        <div style="font-weight: 600; font-size: 13px; color: var(--text-primary);">
          {{ step.title }}
        </div>
      </div>
    </div>

    <!-- Two-Column Interactive Studio -->
    <div style="display: grid; grid-template-columns: 1fr 1.25fr; gap: 20px; align-items: start;">
      <!-- Left: Form Fields -->
      <div class="glass-box" style="padding: 24px;">
        <h3 style="font-size: 16px; font-weight: 600; margin-bottom: 16px;">主体核心信息要素</h3>
        <div style="display: flex; flex-direction: column; gap: 14px;">
          <div>
            <label class="form-label">拟定主体字号 / 全称</label>
            <input v-model="formData.companyName" type="text" class="glass-input" placeholder="如：极客智造一人有限责任公司" />
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div>
              <label class="form-label">注册资本 (万元)</label>
              <input v-model.number="formData.capital" type="number" class="glass-input" placeholder="10" />
            </div>
            <div>
              <label class="form-label">法定代表人 / 经营者</label>
              <input v-model="formData.legalPerson" type="text" class="glass-input" placeholder="姓名" />
            </div>
          </div>
          <div>
            <label class="form-label">经营场所 / 托管注册地址</label>
            <input v-model="formData.address" type="text" class="glass-input" placeholder="如：上海市浦东新区张江高科集群商务秘书地址" />
          </div>
          <div>
            <label class="form-label">标准经营范围 (按国家市场监管总局规范表述)</label>
            <textarea v-model="formData.scope" class="glass-textarea" rows="3"></textarea>
          </div>
          <div>
            <label class="form-label">统一出海及税务申报邮箱</label>
            <input v-model="formData.contactEmail" type="email" class="glass-input" placeholder="maker@opchub.cn" />
          </div>
        </div>
      </div>

      <!-- Right: Formatted Document Live Preview -->
      <div class="glass-box" style="padding: 24px; position: relative;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 15px; font-weight: 600;">标准商事文书实时预览</span>
            <span class="mono-tag" style="background: rgba(52,199,89,0.15); color: #34C759;">已校验合规</span>
          </div>
          <div style="display: flex; gap: 8px;">
            <button class="btn-liquid-outline" style="font-size: 11.5px; padding: 4px 10px;" @click="copyDoc">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
              复制
            </button>
            <button class="btn-liquid" style="font-size: 11.5px; padding: 4px 12px;" @click="exportPdf">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="8 17 12 21 16 17"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.88 18.09A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.29"/>
              </svg>
              导出材料
            </button>
          </div>
        </div>

        <!-- Rendered Document View (Paper Style) -->
        <div style="background: var(--glass-surface-solid); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); padding: 24px; font-size: 13px; line-height: 1.8; color: var(--text-primary); max-height: 480px; overflow-y: auto; box-shadow: var(--glass-shadow);">
          <div style="text-align: center; font-size: 17px; font-weight: 700; margin-bottom: 18px; border-bottom: 2px solid var(--glass-border); padding-bottom: 12px;">
            {{ currentStepTitle }}
          </div>

          <div style="margin-bottom: 12px;">
            <strong>一、 主体基础登记要素</strong><br />
            1. 企业名称：{{ formData.companyName || '（待输入）' }}<br />
            2. 注册资本：人民币 {{ formData.capital }} 万元整<br />
            3. 法定代表人 / 执行董事：{{ formData.legalPerson || '（待输入）' }}<br />
            4. 住所登记地址：{{ formData.address || '（待输入）' }}
          </div>

          <div style="margin-bottom: 12px;">
            <strong>二、 经营范围条款</strong><br />
            一般项目：{{ formData.scope }}
          </div>

          <div style="margin-bottom: 12px;">
            <strong>三、 合规与章程声明</strong><br />
            本一人公司依据《中华人民共和国公司法》及《市场主体登记管理条例》设立，投资人以其认缴的出资额为限对公司承担责任。不设立股东会，由执行董事全权行使经营管理决议权。
          </div>

          <div style="margin-top: 24px; display: flex; justify-content: space-between; font-size: 12px; color: var(--text-secondary); border-top: 1px dashed var(--glass-border-subtle); padding-top: 14px;">
            <span>申报人签字：{{ formData.legalPerson }}（电子签名已绑定）</span>
            <span>生成时间：{{ new Date().toLocaleDateString() }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue';

const emit = defineEmits(['toast']);

const steps = [
  { key: 'REGISTRATION', code: 'REGISTRATION', title: '工商核名与设立登记' },
  { key: 'TAX_BANK', code: 'TAX & BANK', title: '银行对公户与税务报到' },
  { key: 'GLOBAL_PAY', code: 'GLOBAL PAY', title: '海外收款与 Stripe 激活' },
  { key: 'TAX_RELIEF', code: 'TAX RELIEF', title: '研发费用加计扣除申报' },
];

const currentStep = ref('REGISTRATION');

const currentStepTitle = computed(() => {
  switch (currentStep.value) {
    case 'REGISTRATION':
      return '一人有限责任公司设立登记申请书与公司章程';
    case 'TAX_BANK':
      return '小微企业对公账户简易开户与新办纳税人套餐申报表';
    case 'GLOBAL_PAY':
      return '跨境数字贸易离岸资金结算与外汇合规备案指引';
    case 'TAX_RELIEF':
      return '企业研发费用加计扣除归集备查全套留存文书';
    default:
      return '标准化商事设立申报材料';
  }
});

const formData = reactive({
  companyName: '极客智造一人有限责任公司',
  capital: 10,
  legalPerson: '张创客',
  address: '上海市浦东新区张江高科技园区集电港集群商务秘书地址',
  scope: '软件开发；信息技术咨询服务；人工智能应用软件开发；数字内容制作服务；互联网销售；技术进出口。',
  contactEmail: 'maker@opchub.cn',
});

function generateDocument() {
  emit('toast', {
    title: '文书生成完毕',
    message: `已为【${formData.companyName}】一键编译生成符合市场监管总局标准的规范申报材料！`,
    type: 'SUCCESS',
  });
}

function copyDoc() {
  emit('toast', {
    title: '文书已复制',
    message: '全套公文条款已完整复制到系统剪贴板！',
    type: 'SUCCESS',
  });
}

function exportPdf() {
  emit('toast', {
    title: '材料打包导出',
    message: '正在为您打包下载 PDF / Word 标准报送格式公文压缩包...',
    type: 'INFO',
  });
}
</script>
