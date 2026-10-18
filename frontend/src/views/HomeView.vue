<template>
  <div class="view-panel active">
    <div class="glass-box">
      <span class="mono-tag" id="homeOverviewBadge">超级个体创客服务平台</span>
      <h1 class="page-title" style="margin-top: 12px;">超级个体一站式赋能服务平台</h1>
      <p class="page-desc">
        为一人公司（One-Person Company）构建全生命周期操作系统。以微内核流程编排与充血领域模型为基石，打通合规SOP、政策申报、算力折扣、产品打榜与商机外包。
      </p>

      <div style="display: flex; gap: 12px; margin-bottom: 36px; flex-wrap: wrap;">
        <button class="btn-liquid" @click="$emit('switch-tab', 'sop')">
          <svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path></svg>
          <span>开始体验</span>
        </button>
        <button class="btn-liquid-outline" @click="$emit('switch-tab', 'policy')">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><path d="M12 2a10 10 0 0 1 10 10"></path><line x1="12" y1="12" x2="19" y2="5"></line></svg>
          <span>政策雷达</span>
        </button>
        <button class="btn-liquid-outline" @click="$emit('switch-tab', 'product')">
          <svg viewBox="0 0 24 24"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          <span>商用橱窗</span>
        </button>
      </div>

      <div class="section-divider" style="border-top: 1px solid var(--glass-border-subtle); padding-top: 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h2 style="font-size: 19px; font-weight: 600; margin: 0;">功能全景地图 (Capability Matrix)</h2>
          <span class="mono-tag" style="background: var(--accent-glass); color: var(--accent);">功能空间矩阵</span>
        </div>
        <div class="grid-3" id="homeCapabilityGrid">
          <div class="sitemap-card" @click="$emit('switch-tab', 'forum')">
            <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary);">01 · COMMUNITY</div>
            <h3 style="font-size: 16px; margin: 8px 0 6px;">头脑风暴社区</h3>
            <p style="font-size: 13px; color: var(--text-secondary);">灵感碰撞交流、出海实战答疑、经验置顶与干货讨论区。</p>
          </div>
          <div class="sitemap-card" @click="$emit('switch-tab', 'product')">
            <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary);">02 · SHOWCASE</div>
            <h3 style="font-size: 16px; margin: 8px 0 6px;">产品展示橱窗</h3>
            <p style="font-size: 13px; color: var(--text-secondary);">独立创客产品画廊，支持点赞打榜、产品收录与出海获客。</p>
          </div>
          <div class="sitemap-card" @click="$emit('switch-tab', 'policy')">
            <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary);">03 · INTELLIGENCE</div>
            <h3 style="font-size: 16px; margin: 8px 0 6px;">政策雷达内参</h3>
            <p style="font-size: 13px; color: var(--text-secondary);">全网政策白话提炼，税收减免、算力返还与地方补贴精准匹配。</p>
          </div>
          <div class="sitemap-card" @click="$emit('switch-tab', 'demand')">
            <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary);">04 · MARKETPLACE</div>
            <h3 style="font-size: 16px; margin: 8px 0 6px;">需求外包池</h3>
            <p style="font-size: 13px; color: var(--text-secondary);">真实企业寻源商机、AI Agent 外包撮合与资金托管担保。</p>
          </div>
          <div class="sitemap-card" @click="$emit('switch-tab', 'sop')">
            <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary);">05 · WORKFLOW</div>
            <h3 style="font-size: 16px; margin: 8px 0 6px;">流程 SOP 与材料生成</h3>
            <p style="font-size: 13px; color: var(--text-secondary);">工商设立到离岸资金流全阶段表单收集，一键导出标准申报材料。</p>
          </div>
          <div class="sitemap-card" @click="$emit('switch-tab', 'perks')">
            <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary);">06 · INFRASTRUCTURE</div>
            <h3 style="font-size: 16px; margin: 8px 0 6px;">支持与基础设施</h3>
            <p style="font-size: 13px; color: var(--text-secondary);">云厂商激活特权、Token 优惠券、Stripe 结汇通道及工具折扣。</p>
          </div>
          <div class="sitemap-card" @click="$emit('switch-tab', 'compliance')">
            <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary);">07 · COMPLIANCE</div>
            <h3 style="font-size: 16px; margin: 8px 0 6px;">产品合规指南</h3>
            <p style="font-size: 13px; color: var(--text-secondary);">六维合规防线、典型避坑案例库与上线前自检雷达。</p>
          </div>
          <div class="sitemap-card" @click="$emit('open-profile')">
            <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary);">08 · ENTITLEMENT</div>
            <h3 style="font-size: 16px; margin: 8px 0 6px;">用户管理与权益开通</h3>
            <p style="font-size: 13px; color: var(--text-secondary);">多级会员凭证强绑定、按量功能开关与支付鉴权控制中心。</p>
          </div>
          <div class="sitemap-card" @click="$emit('switch-tab', 'backend-orch')">
            <div style="font-family: var(--font-mono); font-size: 11px; color: var(--text-tertiary);">09 · MICROKERNEL</div>
            <h3 style="font-size: 16px; margin: 8px 0 6px;">后端编排与业务上传</h3>
            <p style="font-size: 13px; color: var(--text-secondary);">Python 脚本热上传、AST 安全沙箱验证与微内核 Scenario 路由编排。</p>
          </div>
          <div class="sitemap-card" @click="$emit('switch-tab', 'ops')">
            <div style="font-family: var(--font-mono); font-size: 11px; color: var(--accent);">10 · TELEMETRY</div>
            <h3 style="font-size: 16px; margin: 8px 0 6px;">运营数据大盘</h3>
            <p style="font-size: 13px; color: var(--text-secondary);">实时监测 DAU、UV、PV 与留存转化，支持 Web、Android、iOS 三端一致性展示。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineEmits(['switch-tab', 'open-profile']);
</script>
