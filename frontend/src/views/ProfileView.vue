<template>
  <div class="view-panel active" style="width: 100%;">
    <div style="margin-bottom: 24px;">
      <h1 style="font-size: 26px; font-weight: 800; color: var(--text-primary); margin-bottom: 6px;">
        创客商用档案与独立工作台
      </h1>
      <p style="font-size: 14px; color: var(--text-secondary);">
        创客商用档案、资质合规存证与平台身份标识
      </p>
    </div>

    <!-- 画像头像更换面板 -->
    <div v-if="avatarPickerOpen" class="glass-panel" style="padding: 22px; margin-bottom: 24px;">
      <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 4px;">选择画像头像</h3>
      <p style="font-size: 12px; color: var(--text-tertiary); margin-bottom: 14px;">
        从 20 种内置用户画像中选择你的平台形象；未选择时展示昵称首字头像。
      </p>
      <div class="avatar-picker-grid">
        <button
          v-for="p in PERSONA_AVATARS"
          :key="p.id"
          type="button"
          class="avatar-picker-cell"
          :class="{ active: p.id === avatarDraft }"
          :title="p.label"
          @click="avatarDraft = p.id"
        >
          <PersonaAvatar :id="p.id" :name="p.label" :size="46" />
          <span class="avatar-picker-label">{{ p.label }}</span>
        </button>
      </div>
      <div style="display: flex; gap: 10px; margin-top: 16px;">
        <button
          class="btn-liquid"
          style="font-size: 12.5px; padding: 7px 18px;"
          :disabled="avatarDraft === (profile?.avatar_id || '') || isSavingAvatar"
          @click="saveAvatar"
        >
          {{ isSavingAvatar ? '保存中...' : '保存头像' }}
        </button>
        <button
          class="btn-liquid-outline"
          style="font-size: 12.5px; padding: 7px 18px;"
          @click="closeAvatarPicker"
        >
          取消
        </button>
      </div>
    </div>

    <div v-if="profile" style="display: grid; grid-template-columns: 1fr 2fr; gap: 24px;">
      <!-- Identity Card -->
      <div class="glass-panel" style="padding: 24px; text-align: center;">
        <div style="width: 72px; height: 72px; margin: 0 auto 16px;">
          <PersonaAvatar :id="profile.avatar_id || ''" :name="profile.nickname || profile.email || 'M'" :size="72" />
        </div>
        <div style="font-size: 18px; font-weight: 700; margin-bottom: 4px;">
          {{ profile.nickname || '未设置昵称' }}
        </div>
        <div style="font-size: 13px; color: var(--text-tertiary); margin-bottom: 12px;">
          {{ profile.email }}
        </div>
        <div style="display: inline-block; padding: 4px 12px; border-radius: 12px; background: var(--accent-glass); color: var(--accent); font-size: 12px; font-weight: 600;">
          {{ profile.tier_name || '标准创客' }} · {{ profile.account_type || 'MAKER' }}
        </div>
        <div style="margin-top: 14px;">
          <button
            class="btn-liquid-outline"
            style="width: 100%; font-size: 12px;"
            @click="openAvatarPicker"
          >
            更换画像头像
          </button>
        </div>
        <div style="margin-top: 10px;">
          <button
            class="btn-liquid-outline"
            style="width: 100%; font-size: 12px;"
            @click="navigateToTab('change-password')"
          >
            修改登录密码
          </button>
        </div>
        <div style="margin-top: 10px;">
          <button
            class="btn-liquid-outline"
            style="width: 100%; font-size: 12px; color: var(--status-danger); border-color: var(--status-danger-soft);"
            @click="$emit('logout')"
          >
            退出创客登录
          </button>
        </div>
      </div>

      <!-- Commercial Credentials -->
      <div class="glass-panel" style="padding: 24px;">
        <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 18px; border-bottom: 1px solid var(--glass-border-subtle); padding-bottom: 10px;">
          商业资质与合规存证
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
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="color: var(--text-tertiary);">主营业务赛道:</span>
              <button
                class="btn-liquid-outline"
                style="padding: 2px 8px; font-size: 11px; height: 22px;"
                @click="toggleEditTrack"
              >
                {{ isEditingTrack ? '取消' : '修改赛道' }}
              </button>
            </div>

            <div v-if="!isEditingTrack" style="font-weight: 600; color: var(--text-primary); margin-top: 4px;">
              {{ profile.industry_track || '未设置 (默认: 独立软件全栈开发)' }}
            </div>

            <div v-else style="margin-top: 8px; padding: 10px; border-radius: 8px; background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle);">
              <div style="font-size: 11px; color: var(--text-secondary); margin-bottom: 6px;">选择预设或输入自定义赛道：</div>
              <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px;">
                <span
                  v-for="t in presetTracks"
                  :key="t"
                  class="track-pill"
                  :style="editTrack === t && !editIsCustom ? { background: 'var(--accent-glass)', border: '1px solid var(--accent)', color: 'var(--text-primary)' } : { background: 'var(--glass-surface-subtle)', border: '1px solid var(--glass-border-subtle)', color: 'var(--text-secondary)' }"
                  style="font-size: 10.5px; padding: 2px 7px; border-radius: 10px; cursor: pointer; transition: all 0.2s;"
                  @click="selectEditPreset(t)"
                >
                  {{ t }}
                </span>
                <span
                  class="track-pill"
                  :style="editIsCustom ? { background: 'var(--accent-glass)', border: '1px solid var(--accent)', color: 'var(--text-primary)' } : { background: 'var(--glass-surface-subtle)', border: '1px solid var(--glass-border-subtle)', color: 'var(--text-secondary)' }"
                  style="font-size: 10.5px; padding: 2px 7px; border-radius: 10px; cursor: pointer; transition: all 0.2s;"
                  @click="enableEditCustom"
                >
                  + 自定义
                </span>
              </div>
              <div v-if="editIsCustom" style="margin-bottom: 8px;">
                <input
                  v-model="editCustomInput"
                  type="text"
                  class="glass-input"
                  placeholder="请输入您的自定义赛道名称"
                  maxlength="40"
                  style="width: 100%; box-sizing: border-box; font-size: 11.5px; padding: 4px 8px;"
                  @input="editTrack = editCustomInput.trim()"
                />
              </div>
              <div v-if="trackSaveMsg" :style="{ color: trackSaveError ? 'var(--status-danger)' : 'var(--status-success)' }" style="font-size: 11px; margin-bottom: 6px;">
                {{ trackSaveMsg }}
              </div>
              <div style="display: flex; gap: 6px;">
                <button
                  class="btn-liquid"
                  style="padding: 3px 10px; font-size: 11px;"
                  :disabled="savingTrack"
                  @click="saveProfileTrack"
                >
                  {{ savingTrack ? '保存中...' : '保存赛道' }}
                </button>
              </div>
            </div>
          </div>
          <div v-if="profile?.agreement_version">
            <span style="color: var(--text-tertiary);">法定义务协议存证:</span>
            <div style="font-weight: 600; color: var(--status-success); margin-top: 2px;">
              <OpcIcon name="check" :size="13" /> 已签署合规协议 ({{ profile.agreement_version }})
            </div>
          </div>
        </div>
      </div>
    </div>
    <div v-else style="text-align: center; padding: 60px 0; color: var(--text-tertiary);">
      加载创客档案中...
    </div>

    <!-- Loyalty & Membership Quick Card -->
    <div
      v-if="profile"
      class="glass-panel"
      style="margin-top: 24px; padding: 20px 24px; display: flex; align-items: center; justify-content: space-between; gap: 20px;"
    >
      <div>
        <div style="font-size: 11px; letter-spacing: 0.08em; color: var(--text-tertiary); text-transform: uppercase;">
          晨光积分 · 会员
        </div>
        <div style="display: flex; align-items: baseline; gap: 10px; margin-top: 6px;">
          <span style="font-family: var(--font-mono, 'SF Mono', Menlo, monospace); font-size: 24px; font-weight: 600; color: var(--text-primary);">
            {{ loyaltyAccount ? formatPoints(loyaltyAccount.balance) : '—' }}
          </span>
          <span style="font-size: 12px; color: var(--text-secondary);">
            {{ loyaltyAccount?.level_name || '微光' }} V{{ loyaltyAccount?.level || 1 }}
            · {{ loyaltyAccount?.membership_tier_name || profile.tier_name || '标准创客' }}
          </span>
        </div>
        <div style="font-size: 11.5px; color: var(--text-tertiary); margin-top: 4px;">
          今日 +{{ formatPoints(loyaltyAccount?.today_earned) }} · 本月 +{{ formatPoints(loyaltyAccount?.month_earned) }}
          · 积分可兑换会员时长与产品周边
        </div>
      </div>
      <button
        class="btn-liquid"
        style="font-size: 12.5px; padding: 7px 18px; flex-shrink: 0;"
        @click="navigateToTab('membership')"
      >
        会员与积分中心
      </button>
    </div>

    <!-- My Interactions (我的互动) -->
    <div v-if="profile" class="glass-panel" style="margin-top: 24px; padding: 24px;">
      <h3 style="font-size: 16px; font-weight: 700; margin-bottom: 16px; border-bottom: 1px solid var(--glass-border-subtle); padding-bottom: 10px;">
        我的互动足迹
      </h3>
      <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 18px;">
        <span class="track-pill" style="font-size: 11.5px; padding: 4px 12px; border-radius: 12px; background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle); color: var(--text-secondary);">
          <OpcIcon name="like" :size="12" /> 点赞 {{ mineCounts.like || 0 }}
        </span>
        <span class="track-pill" style="font-size: 11.5px; padding: 4px 12px; border-radius: 12px; background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle); color: var(--text-secondary);">
          <OpcIcon name="star-filled" :size="12" /> 收藏 {{ mineCounts.favorite || 0 }}
        </span>
        <span class="track-pill" style="font-size: 11.5px; padding: 4px 12px; border-radius: 12px; background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle); color: var(--text-secondary);">
          <OpcIcon name="heart" :size="12" /> 喜欢 {{ mineCounts.love || 0 }}
        </span>
        <span class="track-pill" style="font-size: 11.5px; padding: 4px 12px; border-radius: 12px; background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle); color: var(--text-secondary);">
          <OpcIcon name="comment" :size="12" /> 评论 {{ mineCounts.comment || 0 }}
        </span>
        <span class="track-pill" style="font-size: 11.5px; padding: 4px 12px; border-radius: 12px; background: var(--glass-surface-subtle); border: 1px solid var(--glass-border-subtle); color: var(--text-secondary);">
          <OpcIcon name="dislike" :size="12" /> 踩 {{ mineCounts.dislike || 0 }}
        </span>
      </div>

      <div v-if="mineItems.length === 0" style="color: var(--text-tertiary); font-size: 13px; padding: 20px 0; text-align: center;">
        还没有互动足迹，去广场点赞、收藏、喜欢或在政策/需求/文书中发表评论吧。
      </div>
      <div v-else style="display: flex; flex-direction: column; gap: 8px; max-height: 320px; overflow-y: auto;">
        <button
          v-for="item in mineItems"
          :key="`${item.kind}-${item.target_id}-${item.created_at}`"
          type="button"
          style="display: flex; align-items: center; gap: 10px; width: 100%; text-align: left; padding: 10px 14px; border-radius: 12px; border: 1px solid var(--glass-border-subtle); background: var(--glass-surface-subtle); cursor: pointer; transition: all 0.18s;"
          @click="navigateToTab(item.tab)"
        >
          <span style="font-size: 15px;"><OpcIcon :name="kindIcon(item.kind)" :size="15" /></span>
          <div style="flex: 1; min-width: 0;">
            <div style="font-size: 13px; font-weight: 600; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
              {{ item.title || '未命名内容' }}
            </div>
            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 2px;">
              {{ item.subtitle || '' }} · {{ formatMineTime(item.created_at) }}
            </div>
          </div>
          <span style="font-size: 12px; color: var(--accent); flex-shrink: 0;">查看 →</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { dispatchGateway } from '@/api/gateway';
import PersonaAvatar from '@/components/PersonaAvatar.vue';
import { PERSONA_AVATARS } from '@/components/personaAvatarCatalog';
import { formatPoints } from '@/utils/loyalty';

const emit = defineEmits(['toast', 'logout', 'navigate', 'session-updated']);

const profile = ref(null);
const isEditingTrack = ref(false);
const editTrack = ref('');
const editIsCustom = ref(false);
const editCustomInput = ref('');
const savingTrack = ref(false);
const trackSaveMsg = ref('');
const trackSaveError = ref(false);

const mineItems = ref([]);
const mineCounts = ref({ like: 0, favorite: 0, love: 0, comment: 0, dislike: 0 });
const loyaltyAccount = ref(null);

async function loadLoyaltyAccount() {
  try {
    const res = await dispatchGateway('loyalty.account', {}, { silent: true });
    if (res.ok) loyaltyAccount.value = res.data;
  } catch (e) {
    loyaltyAccount.value = null;
  }
}

async function loadMyInteractions() {
  try {
    const res = await dispatchGateway('content.interactions.mine', {}, { silent: true });
    if (res.ok && res.data) {
      mineItems.value = Array.isArray(res.data.items) ? res.data.items : [];
      mineCounts.value = { ...(res.data.counts || {}) };
    }
  } catch (e) {
    mineItems.value = [];
  }
}

function kindIcon(kind) {
  const map = { LIKE: 'like', FAVORITE: 'star-filled', LOVE: 'heart', COMMENT: 'comment', DISLIKE: 'dislike' };
  return map[kind] || 'bookmark';
}

function formatMineTime(value) {
  if (!value) return '';
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  } catch (e) {
    return '';
  }
}

function navigateToTab(tab) {
  if (!tab) {
    emit('toast', { title: '无法跳转', message: '该内容所在频道暂不可用。', type: 'INFO' });
    return;
  }
  emit('navigate', tab);
}

const presetTracks = [
  'AI 原生应用与智能体',
  '出海 SaaS 与独立开发',
  '跨境电商与数字贸易',
  '智能软硬件与 IoT',
  '咨询与数字创意服务',
];

function toggleEditTrack() {
  isEditingTrack.value = !isEditingTrack.value;
  trackSaveMsg.value = '';
  if (isEditingTrack.value) {
    const current = profile.value?.industry_track || '';
    if (presetTracks.includes(current)) {
      editTrack.value = current;
      editIsCustom.value = false;
      editCustomInput.value = '';
    } else if (current) {
      editTrack.value = current;
      editIsCustom.value = true;
      editCustomInput.value = current;
    } else {
      editTrack.value = presetTracks[0];
      editIsCustom.value = false;
      editCustomInput.value = '';
    }
  }
}

function selectEditPreset(t) {
  editIsCustom.value = false;
  editTrack.value = t;
}

function enableEditCustom() {
  editIsCustom.value = true;
  editTrack.value = editCustomInput.value.trim();
}

async function saveProfileTrack() {
  trackSaveMsg.value = '';
  trackSaveError.value = false;
  const targetTrack = editIsCustom.value ? editCustomInput.value.trim() : editTrack.value.trim();
  if (!targetTrack) {
    trackSaveMsg.value = '赛道名称不能为空';
    trackSaveError.value = true;
    return;
  }

  savingTrack.value = true;
  try {
    const res = await dispatchGateway('user.profile.update', {
      industry_track: targetTrack,
    });
    if (res.ok && res.data) {
      if (profile.value) {
        profile.value.industry_track = res.data.industry_track || targetTrack;
      }
      trackSaveMsg.value = '业务赛道已更新成功！';
      setTimeout(() => {
        isEditingTrack.value = false;
        trackSaveMsg.value = '';
      }, 1200);
    } else {
      trackSaveMsg.value = res.error || '更新失败，请重试';
      trackSaveError.value = true;
    }
  } catch (err) {
    trackSaveMsg.value = '网络请求异常，保存失败';
    trackSaveError.value = true;
  } finally {
    savingTrack.value = false;
  }
}

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

// ---------------- 画像头像更换 ----------------
const avatarPickerOpen = ref(false);
const avatarDraft = ref('');
const isSavingAvatar = ref(false);

function openAvatarPicker() {
  avatarDraft.value = profile.value?.avatar_id || '';
  avatarPickerOpen.value = true;
}

function closeAvatarPicker() {
  avatarPickerOpen.value = false;
  avatarDraft.value = '';
}

async function saveAvatar() {
  const nextId = avatarDraft.value || '';
  if (isSavingAvatar.value || nextId === (profile.value?.avatar_id || '')) return;
  isSavingAvatar.value = true;
  try {
    const res = await dispatchGateway('user.profile.update', { avatar_id: nextId });
    if (res.ok && res.data) {
      profile.value = res.data;
      avatarPickerOpen.value = false;
      avatarDraft.value = '';
      // 刷新本地会话档案，导航栏等处的当前用户头像即时同步
      try {
        const s = await dispatchGateway('auth.session', {}, { silent: true });
        if (s.ok && s.data) {
          localStorage.setItem('opchub_user_session', JSON.stringify(s.data));
          emit('session-updated', s.data);
        }
      } catch (e) {}
      const picked = PERSONA_AVATARS.find((p) => p.id === nextId);
      emit('toast', {
        title: '头像已更新',
        message: picked ? `画像头像已切换为「${picked.label}」。` : '画像头像已更新。',
        type: 'SUCCESS',
      });
    } else {
      emit('toast', { title: '保存未完成', message: res.error || '请稍后重试。', type: 'ERROR' });
    }
  } catch (e) {
    emit('toast', { title: '保存异常', message: '账号服务暂时不可用，请稍后重试。', type: 'ERROR' });
  } finally {
    isSavingAvatar.value = false;
  }
}

onMounted(() => {
  loadProfile();
  loadMyInteractions();
  loadLoyaltyAccount();
});
</script>

<style scoped>
.avatar-picker-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
  gap: 10px;
}
.avatar-picker-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 6px 10px;
  border-radius: 12px;
  border: 1.5px solid transparent;
  background: transparent;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.avatar-picker-cell:hover {
  background: var(--accent-glass, rgba(94, 114, 235, 0.08));
}
.avatar-picker-cell.active {
  border-color: var(--accent, #5e72eb);
  background: var(--accent-glass, rgba(94, 114, 235, 0.10));
}
.avatar-picker-label {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.2;
  text-align: center;
}
.avatar-picker-cell.active .avatar-picker-label {
  color: var(--accent, #5e72eb);
  font-weight: 600;
}
</style>
