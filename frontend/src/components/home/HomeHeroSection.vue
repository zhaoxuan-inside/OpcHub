<template>
  <section class="hero-section">
    <div class="hero-grid">
      <div class="hero-copy">
        <div class="hero-badge">
          <span class="mono-code">OPC_COMMERCIAL_OS // 2026</span>
          <span class="badge-separator">/</span>
          <span>一人公司 · 商业全周期赋能</span>
        </div>

        <h1 class="hero-headline">
          <span class="headline-line">一人公司，</span>
          <span class="headline-line headline-accent">千军万马。</span>
          <span class="headline-sub">超级个体的下一代商业操作系统</span>
        </h1>

        <p class="hero-subtitle">
          把政策检索、申报文书、产品曝光与需求撮合收进同一张工作台。
          不再在十几个网站之间来回切换，让一个人也能拥有集团级的商业底座。
        </p>

        <div class="hero-actions">
          <template v-if="!userSession">
            <button class="btn-liquid hero-btn-primary" @click="$emit('open-register')">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="8.5" cy="7" r="4"/>
                <line x1="20" y1="8" x2="20" y2="14"/>
                <line x1="23" y1="11" x2="17" y2="11"/>
              </svg>
              <span>立即入驻 · 开启一人公司</span>
            </button>
            <button class="btn-liquid-outline hero-btn-secondary" @click="$emit('open-login')">
              <span>创客登录</span>
            </button>
          </template>
          <template v-else>
            <button class="btn-liquid hero-btn-primary" @click="$emit('switch-tab', 'policy')">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="7"/><line x1="16.5" y1="16.5" x2="21" y2="21"/>
              </svg>
              <span>进入工作台 · 查政策</span>
            </button>
            <button class="btn-liquid-outline hero-btn-secondary" @click="$emit('switch-tab', 'sop')">
              <span>生成申报文书</span>
            </button>
          </template>

          <a href="#showcaseBento" class="scroll-explore-link">
            <span>浏览平台能力</span>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 5v14M19 12l-7 7-7-7"/>
            </svg>
          </a>
        </div>

        <div class="hero-proof">
          <div class="proof-item">
            <strong>{{ overview?.active_makers_count ?? 0 }}<small class="proof-unit">位</small></strong>
            <span>创客的共同选择</span>
          </div>
          <div class="proof-item">
            <strong>{{ overview?.products_count ?? 0 }}<small class="proof-unit">款</small></strong>
            <span>在展独立作品</span>
          </div>
          <div class="proof-item">
            <strong>{{ overview?.matched_policies_count ?? 0 }}<small class="proof-unit">项</small></strong>
            <span>收录扶持政策</span>
          </div>
          <div class="proof-item">
            <strong>¥{{ perkValueText }}</strong>
            <span>生态特权价值</span>
          </div>
        </div>
      </div>

      <aside class="hero-console" aria-label="平台能力快捷入口">
        <div class="console-head">
          <span class="console-dot"></span>
          <span class="console-title">OPC / OPERATING SYSTEM</span>
          <span class="console-live">LIVE</span>
        </div>

        <div class="console-rows">
          <button
            v-for="row in consoleRows"
            :key="row.tab"
            type="button"
            class="console-row"
            @click="$emit('switch-tab', row.tab)"
          >
            <span class="console-index">{{ row.index }}</span>
            <span class="console-main">
              <strong>{{ row.title }}</strong>
              <em>{{ row.desc }}</em>
            </span>
            <span class="console-value">{{ row.value }}</span>
            <span class="console-arrow">↗</span>
          </button>
        </div>

        <div class="console-foot">
          <span>从找政策到签下第一单</span>
          <span class="console-foot-mono">ONE PERSON / FULL STACK</span>
        </div>
      </aside>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  userSession: {
    type: Object,
    default: null,
  },
  overview: {
    type: Object,
    default: null,
  },
});

defineEmits(['open-login', 'open-register', 'switch-tab']);

const perkValueText = computed(() => {
  const total = Number(props.overview?.perks_saved_cny) || 0;
  if (total >= 10000) return `${(total / 10000).toFixed(1)}万`;
  return total.toLocaleString();
});

const consoleRows = computed(() => [
  {
    index: '01',
    title: '政策雷达',
    desc: '省市扶持 · 资格自测',
    value: `${props.overview?.matched_policies_count ?? 0} 项`,
    tab: 'policy',
  },
  {
    index: '02',
    title: '文书工坊',
    desc: '引导填写 · 一键成稿',
    value: 'SOP',
    tab: 'sop',
  },
  {
    index: '03',
    title: '产品橱窗',
    desc: '独立作品 · 打榜曝光',
    value: `${props.overview?.products_count ?? 0} 款`,
    tab: 'product',
  },
  {
    index: '04',
    title: '需求集市',
    desc: '发布委托 · 撮合接单',
    value: '撮合',
    tab: 'demand',
  },
]);
</script>

<style scoped>
.hero-section {
  position: relative;
  overflow: hidden;
  margin-bottom: 56px;
  padding: 56px 56px 48px;
  border-radius: 24px;
  background: var(--glass-surface);
  border: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
  text-align: left;
}

.hero-section::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(17, 18, 20, 0.18), transparent);
  opacity: 0.7;
  pointer-events: none;
}

.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
  gap: 56px;
  align-items: center;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  padding: 5px 10px;
  border-radius: 6px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
  letter-spacing: 0.02em;
}

.badge-separator {
  opacity: 0.35;
}

.mono-code {
  font-family: var(--font-mono);
  color: var(--accent);
  letter-spacing: 0.05em;
}

.hero-headline {
  display: flex;
  flex-direction: column;
  margin: 22px 0 20px;
  font-family: var(--font-display);
  font-size: clamp(44px, 5.4vw, 72px);
  font-weight: 700;
  line-height: 0.98;
  letter-spacing: -0.062em;
  color: var(--text-primary);
}

.headline-accent {
  color: var(--accent);
}

.headline-sub {
  margin-top: 18px;
  font-size: clamp(16px, 1.6vw, 20px);
  font-weight: 500;
  line-height: 1.35;
  letter-spacing: -0.03em;
  color: var(--text-secondary);
}

.hero-subtitle {
  max-width: 600px;
  margin-bottom: 30px;
  font-size: 14.5px;
  line-height: 1.75;
  color: var(--text-secondary);
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-bottom: 34px;
}

.hero-btn-primary {
  padding: 12px 24px;
  font-size: 14px;
  font-weight: 600;
}

.hero-btn-secondary {
  padding: 12px 20px;
  font-size: 14px;
}

.scroll-explore-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 4px;
  font-size: 12.5px;
  color: var(--text-tertiary);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: color 0.18s ease, border-color 0.18s ease;
}

.scroll-explore-link:hover {
  color: var(--text-primary);
  border-bottom-color: var(--text-primary);
}

.hero-proof {
  display: flex;
  flex-wrap: wrap;
  gap: 30px;
  padding-top: 22px;
  border-top: 1px solid var(--glass-border-subtle);
}

.proof-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 84px;
}

.proof-item strong {
  font-family: var(--font-mono);
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.04em;
  color: var(--text-primary);
}

.proof-item span {
  font-size: 10.5px;
  letter-spacing: 0.02em;
  color: var(--text-tertiary);
}

.proof-unit {
  margin-left: 1px;
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 500;
  color: var(--text-tertiary);
}

/* ---- Right console ---- */
.hero-console {
  display: flex;
  flex-direction: column;
  border-radius: 18px;
  background: var(--glass-surface-solid);
  border: 1px solid var(--glass-border);
  box-shadow: var(--glass-shadow);
  overflow: hidden;
}

.console-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 13px 16px;
  border-bottom: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface-subtle);
}

.console-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--status-success);
  box-shadow: 0 0 0 3px var(--status-success-soft);
}

.console-title {
  font-family: var(--font-mono);
  font-size: 9.5px;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
}

.console-live {
  margin-left: auto;
  font-family: var(--font-mono);
  font-size: 8.5px;
  letter-spacing: 0.08em;
  color: var(--status-success);
}

.console-rows {
  display: flex;
  flex-direction: column;
}

.console-row {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr) auto 16px;
  align-items: center;
  gap: 12px;
  padding: 15px 16px;
  border: none;
  border-bottom: 1px solid var(--glass-border-subtle);
  background: transparent;
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
  transition: background 0.18s ease;
}

.console-row:last-child {
  border-bottom: none;
}

.console-row:hover {
  background: var(--glass-surface-subtle);
}

.console-index {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--text-tertiary);
}

.console-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.console-main strong {
  font-size: 13px;
  font-weight: 650;
  letter-spacing: -0.015em;
}

.console-main em {
  font-style: normal;
  font-size: 10.5px;
  color: var(--text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.console-value {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--accent);
  white-space: nowrap;
}

.console-arrow {
  font-size: 12px;
  color: var(--text-tertiary);
  transition: transform 0.18s ease, color 0.18s ease;
}

.console-row:hover .console-arrow {
  color: var(--accent);
  transform: translate(1px, -1px);
}

.console-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 11px 16px;
  border-top: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface-subtle);
  font-size: 9.5px;
  color: var(--text-tertiary);
}

.console-foot-mono {
  font-family: var(--font-mono);
  font-size: 8.5px;
  letter-spacing: 0.06em;
}

@media (max-width: 980px) {
  .hero-grid {
    grid-template-columns: 1fr;
    gap: 32px;
  }

  .hero-section {
    padding: 40px 28px 34px;
  }

  .hero-console {
    max-width: 560px;
  }
}

@media (max-width: 640px) {
  .hero-section {
    padding: 32px 20px 28px;
    border-radius: 18px;
  }

  .hero-headline {
    font-size: 40px;
    letter-spacing: -0.05em;
  }

  .headline-sub {
    font-size: 16px;
  }

  .hero-proof {
    gap: 20px;
  }

  .proof-item strong {
    font-size: 20px;
  }

  .hero-actions {
    align-items: stretch;
  }

  .hero-btn-primary,
  .hero-btn-secondary {
    width: 100%;
    justify-content: center;
  }
}
</style>
