<template>
  <div>
    <div style="margin-bottom: 24px;">
      <h1 style="font-size: 26px; font-weight: 800; color: var(--text-primary); margin-bottom: 6px;">
        创客商用档案与独立工作台
      </h1>
      <p style="font-size: 14px; color: var(--text-secondary);">
        PostgreSQL 18 实体数据落盘、合规法定义务存证及创客身份标识
      </p>
    </div>

    <div v-if="profile" style="display: grid; grid-template-columns: 1fr 2fr; gap: 24px;">
      <!-- Identity Card -->
      <div class="glass-panel" style="padding: 24px; text-align: center;">
        <div style="width: 72px; height: 72px; border-radius: 50%; background: var(--accent); margin: 0 auto 16px; display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: 800; color: #fff;">
          {{ (profile.nickname || profile.email || 'M')[0].toUpperCase() }}
        </div>
        <div style="font-size: 18px; font-weight: 700; margin-bottom: 4px;">
          {{ profile.nickname || '未设置昵称' }}
        </div>
        <div style="font-size: 13px; color: var(--text-tertiary); margin-bottom: 12px;">
          {{ profile.email }}
        </div>
        <div style="display: inline-block; padding: 4px 12px; border-radius: 12px; background: rgba(0, 113, 227, 0.15); color: #0071E3; font-size: 12px; font-weight: 600;">
          {{ profile.tier_name || '标准创客' }} · {{ profile.account_type || 'MAKER' }}
        </div>
      </div>

      <!-- Commercial Credentials -->
      <div class="glass-panel" style="padding: 24px;">
        <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 18px; border-bottom: 1px solid var(--glass-border-subtle); padding-bottom: 10px;">
          商业资质与合规存证 (PostgreSQL 18 ACID)
        </h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; font-size: 13px;">
          <div>
            <span style="color: var(--text-tertiary);">企业/工作室主体:</span>
            <div style="font-weight: 600; color: var(--text-primary); margin-top: 2px;">
              {{ profile.company_name || '独立创客自然人主体' }}
            </div>
          </div>
          <div>
            <span style="color: var(--text-tertiary);">统一社会信用代码:</span>
            <div style="font-weight: 600; color: var(--text-primary); margin-top: 2px;">
              {{ profile.credit_code || '未登记 (个人创客)' }}
            </div>
          </div>
          <div>
            <span style="color: var(--text-tertiary);">主营业务赛道:</span>
            <div style="font-weight: 600; color: var(--text-primary); margin-top: 2px;">
              {{ profile.industry_track || '独立软件全栈开发' }}
            </div>
          </div>
          <div>
            <span style="color: var(--text-tertiary);">法定义务协议存证:</span>
            <div style="font-weight: 600; color: #30d158; margin-top: 2px;">
              ✓ 已签署合规协议 (v1.2.0)
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else style="text-align: center; padding: 60px 0; color: var(--text-tertiary);">
      加载创客档案中...
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const profile = ref(null);

async function loadProfile() {
  try {
    const res = await dispatchGateway('user.profile', {});
    if (res.ok && res.data) {
      profile.value = res.data;
    }
  } catch (e) {
    console.error(e);
  }
}

onMounted(() => {
  loadProfile();
});
</script>
