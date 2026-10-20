<template>
  <div class="view-panel active">
    <!-- Header -->
    <div class="glass-box" style="padding: 24px 32px 16px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <h1 class="page-title" style="font-size: 26px; margin-bottom: 4px;">创客生态特权与权益中心</h1>
          <p style="font-size: 13px; color: var(--text-secondary);">
            云厂商算力扶持、海外合规收款绿通、AI 自动化文书高阶配额与企业外包优先派单。
          </p>
        </div>
        <span class="mono-tag" style="background: var(--accent-glass); color: var(--accent);">
          INFRASTRUCTURE & ENTITLEMENTS
        </span>
      </div>
    </div>

    <!-- 3-Tier VIP Entitlement Cards -->
    <div class="grid-3" style="margin-bottom: 24px;">
      <!-- Tier 1: Free -->
      <div class="glass-card" @mousemove="handleMouseMove">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span class="mono-tag">STANDARD</span>
            <span style="font-size: 12px; color: #34C759; font-weight: 600;">已默认开通</span>
          </div>
          <h3 style="font-size: 20px; font-weight: 700; margin-bottom: 6px;">标准创客</h3>
          <div style="font-size: 28px; font-weight: 700; font-family: var(--font-display); margin-bottom: 14px;">
            ¥ 0 <span style="font-size: 13px; font-weight: 400; color: var(--text-tertiary);">/ 终身免费</span>
          </div>
          <div style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.8; margin-bottom: 20px;">
            <div>✔ 头脑风暴社区自由互动发帖</div>
            <div>✔ 独立商业作品橱窗展示与打榜</div>
            <div>✔ 全网政策白话库无限制检索</div>
            <div>✔ 基础需求集市浏览与竞标</div>
          </div>
        </div>
        <button class="btn-liquid-outline" style="width: 100%; justify-content: center;" disabled>
          当前级别
        </button>
      </div>

      <!-- Tier 2: Pro -->
      <div class="glass-card" style="border-color: rgba(0, 113, 227, 0.4);" @mousemove="handleMouseMove">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span class="mono-tag" style="background: var(--accent-glass); color: var(--accent);">RECOMMENDED</span>
            <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(0,113,227,0.15); color: var(--accent);">热度最高</span>
          </div>
          <h3 style="font-size: 20px; font-weight: 700; margin-bottom: 6px;">超级个体 OPC Pro</h3>
          <div style="font-size: 28px; font-weight: 700; font-family: var(--font-display); margin-bottom: 14px; color: var(--accent);">
            ¥ 299 <span style="font-size: 13px; font-weight: 400; color: var(--text-tertiary);">/ 年度</span>
          </div>
          <div style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.8; margin-bottom: 20px;">
            <div>✔ 包含标准创客所有功能权益</div>
            <div>✔ AI 政务标准文书无限次生成导出</div>
            <div>✔ 小微增值税与算力补贴智能测算引擎</div>
            <div>✔ 专属出海 Stripe 0.4% 结汇绿色通道</div>
          </div>
        </div>
        <button class="btn-liquid" style="width: 100%; justify-content: center;" @click="handleUpgrade('OPC Pro', 299)">
          立即升级 Pro
        </button>
      </div>

      <!-- Tier 3: Black Diamond VIP -->
      <div class="glass-card" style="border-color: rgba(255, 149, 0, 0.4);" @mousemove="handleMouseMove">
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span class="mono-tag" style="background: rgba(255,149,0,0.15); color: #FF9500;">ENTERPRISE VIP</span>
            <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background: rgba(255,149,0,0.15); color: #FF9500;">黑钻尊享</span>
          </div>
          <h3 style="font-size: 20px; font-weight: 700; margin-bottom: 6px;">黑钻创客合伙人 VIP</h3>
          <div style="font-size: 28px; font-weight: 700; font-family: var(--font-display); margin-bottom: 14px; color: #FF9500;">
            ¥ 899 <span style="font-size: 13px; font-weight: 400; color: var(--text-tertiary);">/ 永久授权</span>
          </div>
          <div style="font-size: 12.5px; color: var(--text-secondary); line-height: 1.8; margin-bottom: 20px;">
            <div>✔ 包含 Pro 版所有高级权益</div>
            <div>✔ 企业高额委托需求顶格优先派单推荐</div>
            <div>✔ 平台技术与法务担保履约背书</div>
            <div>✔ 1对1 资深出海与企业架构师顾问支持</div>
          </div>
        </div>
        <button class="btn-liquid" style="width: 100%; justify-content: center; background: #FF9500;" @click="handleUpgrade('黑钻创客合伙人 VIP', 899)">
          晋升黑钻合伙人
        </button>
      </div>
    </div>

    <!-- Infrastructure Cloud Partners Strip -->
    <div class="glass-box" style="padding: 24px 32px;">
      <h3 style="font-size: 17px; font-weight: 600; margin-bottom: 16px;">生态基础设施特权资源</h3>
      <div class="grid-3">
        <div class="glass-card" @mousemove="handleMouseMove">
          <div>
            <span class="mono-tag" style="margin-bottom: 8px;">AWS ACTIVATE</span>
            <h4 style="font-size: 15px; margin-bottom: 6px;">$5,000 云服务算力代金券</h4>
            <p style="font-size: 12px; color: var(--text-secondary);">为一人公司初创团队提供 2 年期云算力免单支持。</p>
          </div>
          <button class="btn-liquid-outline" style="margin-top: 14px; font-size: 11.5px; padding: 4px 10px;" @click="claimPerk('AWS Activate $5,000')">
            领取特权
          </button>
        </div>
        <div class="glass-card" @mousemove="handleMouseMove">
          <div>
            <span class="mono-tag" style="margin-bottom: 8px;">STRIPE PAY</span>
            <h4 style="font-size: 15px; margin-bottom: 6px;">0.4% 全球合规结汇通道</h4>
            <p style="font-size: 12px; color: var(--text-secondary);">无须离岸实体，协助对接香港及新加坡虚拟对公户。</p>
          </div>
          <button class="btn-liquid-outline" style="margin-top: 14px; font-size: 11.5px; padding: 4px 10px;" @click="claimPerk('Stripe 0.4% 结汇通道')">
            开通权限
          </button>
        </div>
        <div class="glass-card" @mousemove="handleMouseMove">
          <div>
            <span class="mono-tag" style="margin-bottom: 8px;">TAX REDUCTION</span>
            <h4 style="font-size: 15px; margin-bottom: 6px;">研发费用加计扣除申报直通车</h4>
            <p style="font-size: 12px; color: var(--text-secondary);">100% 比例税前研发费用加计扣除备查材料一键齐备。</p>
          </div>
          <button class="btn-liquid-outline" style="margin-top: 14px; font-size: 11.5px; padding: 4px 10px;" @click="claimPerk('加计扣除申报直通车')">
            立即接入
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const emit = defineEmits(['open-register', 'toast']);

function handleMouseMove(e) {
  const card = e.currentTarget;
  const rect = card.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  card.style.setProperty('--mouse-x', `${x}px`);
  card.style.setProperty('--mouse-y', `${y}px`);
}

function handleUpgrade(tier, price) {
  const token = localStorage.getItem('opchub_session_token');
  if (!token) {
    emit('toast', {
      title: '需创客准入',
      message: '请先完成商用入驻注册或登录后再升级权益！',
      type: 'INFO',
    });
    emit('open-register');
    return;
  }
  emit('toast', {
    title: '权益激活',
    message: `已向安全支付网关提交【${tier}】开通请求（¥${price}），权益凭据已绑定您的创客主体！`,
    type: 'SUCCESS',
  });
}

function claimPerk(perkName) {
  emit('toast', {
    title: '特权领取成功',
    message: `【${perkName}】的激活兑换码与配置指引已送达您的创客专属邮箱！`,
    type: 'SUCCESS',
  });
}
</script>
