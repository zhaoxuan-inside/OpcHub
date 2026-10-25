<template>
  <section class="hero-section glass-box">
    <div class="hero-content">
      <div class="hero-badge">
        <span class="mono-code">OPC_COMMERCIAL_OS // 2026</span>
        <span class="badge-separator">·</span>
        <span>一人公司 · 商业全周期赋能</span>
      </div>

      <h1 class="hero-headline">
        一人公司，<span class="text-gradient">千军万马</span>。<br />
        超级个体的下一代商业操作系统
      </h1>

      <p class="hero-subtitle">
        深度集成政策中心、智能申报文书、独立作品高光橱窗与超级个体需求集市。<br class="desktop-break" />
        告别繁杂孤立的工商、报税与流量焦虑，让单兵作战拥有集团级的商业势能与合规保障。
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
          <button class="btn-liquid hero-btn-primary" @click="$emit('switch-tab', 'forum')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            <span>进入创客工作台</span>
          </button>
          <button class="btn-liquid-outline hero-btn-secondary" @click="$emit('switch-tab', 'product')">
            <span>浏览产品橱窗</span>
          </button>
        </template>

        <a href="#showcaseBento" class="scroll-explore-link">
          <span>浏览平台宣传与精选成果</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 5v14M19 12l-7 7-7-7"/>
          </svg>
        </a>
      </div>

      <!-- Metrics Ticker (全部指标来自 home.overview 单次聚合，读取失败时整条隐藏) -->
      <div v-if="overview" class="hero-metrics-grid">
        <div class="metric-item">
          <div class="metric-value">{{ overview.active_makers_count ?? 0 }}<span class="metric-plus"> 位</span></div>
          <div class="metric-label">入驻认证创客</div>
        </div>
        <div class="metric-divider"></div>
        <div class="metric-item">
          <div class="metric-value">{{ overview.products_count ?? 0 }}<span class="metric-plus"> 款</span></div>
          <div class="metric-label">橱窗在展独立商业作品</div>
        </div>
        <div class="metric-divider"></div>
        <div class="metric-item">
          <div class="metric-value">{{ overview.matched_policies_count ?? 0 }}<span class="metric-plus"> 项</span></div>
          <div class="metric-label">政策库收录扶持政策</div>
        </div>
        <div class="metric-divider"></div>
        <div class="metric-item">
          <div class="metric-value">{{ overview.forum_threads_count ?? 0 }}<span class="metric-plus"> 篇</span></div>
          <div class="metric-label">头脑风暴实战议题</div>
        </div>
        <div class="metric-divider"></div>
        <div class="metric-item">
          <div class="metric-value">¥{{ perkValueText }}<span class="metric-plus"></span></div>
          <div class="metric-label">生态特权累计价值</div>
        </div>
      </div>
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
</script>

<style scoped>
.hero-section {
  padding: 64px 48px 52px;
  text-align: center;
  margin-bottom: 56px;
  position: relative;
  overflow: hidden;
}

.hero-content {
  max-width: 900px;
  margin: 0 auto;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-tertiary);
  margin-bottom: 20px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
}

.badge-separator {
  opacity: 0.4;
}

.mono-code {
  font-family: var(--font-mono);
  color: var(--accent);
  letter-spacing: 0.05em;
}

.hero-headline {
  font-family: var(--font-display);
  font-size: 48px;
  font-weight: 700;
  line-height: 1.18;
  letter-spacing: -0.04em;
  color: var(--text-primary);
  margin-bottom: 22px;
}

.text-gradient {
  color: var(--accent);
}

.hero-subtitle {
  font-size: 17px;
  line-height: 1.65;
  color: var(--text-secondary);
  margin-bottom: 38px;
  font-weight: 400;
}

.hero-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 52px;
}

.hero-btn-primary {
  padding: 12px 28px;
  font-size: 14.5px;
  font-weight: 600;
  box-shadow: 0 4px 20px rgba(0, 113, 227, 0.28);
}

.hero-btn-secondary {
  padding: 12px 24px;
  font-size: 14.5px;
}

.scroll-explore-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13.5px;
  color: var(--text-tertiary);
  text-decoration: none;
  padding: 8px 12px;
  border-radius: var(--radius-full);
  transition: var(--transition-liquid);
}

.scroll-explore-link:hover {
  color: var(--accent);
  transform: translateY(1px);
}

/* Metrics Grid */
.hero-metrics-grid {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 24px 0 0;
  border-top: 1px solid var(--glass-border-subtle);
  flex-wrap: wrap;
  gap: 16px;
}

.metric-item {
  text-align: center;
  flex: 1;
  min-width: 140px;
}

.metric-value {
  font-family: var(--font-display);
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text-primary);
  line-height: 1.1;
  margin-bottom: 4px;
}

.metric-plus, .metric-unit {
  color: var(--accent);
  font-weight: 600;
  font-size: 24px;
}

.metric-label {
  font-size: 12.5px;
  color: var(--text-tertiary);
  white-space: nowrap;
}

.metric-divider {
  width: 1px;
  height: 36px;
  background: var(--glass-border-subtle);
}

@media (max-width: 1024px) {
  .hero-headline {
    font-size: 38px;
  }
}

@media (max-width: 680px) {
  .hero-section {
    padding: 36px 20px 32px;
  }
  .hero-headline {
    font-size: 28px;
  }
  .hero-subtitle {
    font-size: 14px;
  }
  .desktop-break {
    display: none;
  }
  .hero-metrics-grid {
    gap: 20px;
  }
  .metric-divider {
    display: none;
  }
}
</style>
