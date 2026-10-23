<template>
  <Teleport to="body">
    <Transition name="ccd-fade">
      <div v-if="visible" class="ccd-backdrop" @click.self="$emit('close')">
        <aside class="ccd-panel glass-box" role="dialog" aria-label="评论">
          <header class="ccd-header">
            <div class="ccd-heading">
              <div class="ccd-title-row">
                <span class="ccd-title-dot"></span>
                <h3 class="ccd-title">评论交流</h3>
                <span class="ccd-count">{{ total }} 条</span>
              </div>
              <p class="ccd-subtitle">{{ title || '公开内容' }}</p>
            </div>
            <button type="button" class="ccd-close" @click="$emit('close')" aria-label="关闭评论"><OpcIcon name="close" :size="16" /></button>
          </header>

          <div class="ccd-body">
            <div v-if="loading" class="ccd-empty">
              <span class="ccd-spinner"></span>
              <span>正在加载评论...</span>
            </div>
            <div v-else-if="comments.length === 0" class="ccd-empty">
              <span class="ccd-empty-icon"><OpcIcon name="comment" :size="40" /></span>
              <strong>还没有评论</strong>
              <span>成为第一个分享观点的人。</span>
            </div>
            <ul v-else class="ccd-list">
              <li v-for="comment in comments" :key="comment.id" class="ccd-item">
                <div class="ccd-avatar">{{ initialOf(comment.author_name) }}</div>
                <div class="ccd-item-main">
                  <div class="ccd-item-head">
                    <span class="ccd-author">{{ comment.author_name || '创客' }}</span>
                    <span class="ccd-time">{{ formatTime(comment.created_at) }}</span>
                    <button
                      v-if="canDelete(comment)"
                      type="button"
                      class="ccd-delete"
                      :disabled="deletingId === comment.id"
                      @click="removeComment(comment)"
                      title="删除这条评论"
                    >
                      删除
                    </button>
                  </div>
                  <p class="ccd-text">{{ comment.content }}</p>
                </div>
              </li>
            </ul>
          </div>

          <footer class="ccd-footer">
            <div v-if="!authenticated" class="ccd-login-hint">
              <span>登录后即可参与评论交流</span>
              <button type="button" class="ccd-login-btn" @click="$emit('require-login')">去登录</button>
            </div>
            <form v-else class="ccd-form" @submit.prevent="submitComment">
              <textarea
                v-model="draft"
                class="ccd-input"
                rows="3"
                maxlength="4000"
                placeholder="写下你的观点、补充或问题..."
              ></textarea>
              <div class="ccd-form-actions">
                <span class="ccd-hint">{{ draft.length }}/4000</span>
                <button type="submit" class="ccd-submit" :disabled="submitting || !draft.trim()">
                  <span v-if="submitting">发送中...</span>
                  <span v-else>发表评论</span>
                </button>
              </div>
            </form>
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const props = defineProps({
  visible: { type: Boolean, default: false },
  targetType: { type: String, required: true },
  targetId: { type: [String, Number], required: true },
  title: { type: String, default: '' },
  authenticated: { type: Boolean, default: false },
});

const emit = defineEmits(['close', 'count-change', 'require-login', 'toast']);

const comments = ref([]);
const total = ref(0);
const loading = ref(false);
const submitting = ref(false);
const deletingId = ref('');
const draft = ref('');

const currentUserId = computed(() => {
  const session = safeSession();
  return String(session?.uid || session?.id || session?.user?.uid || session?.user?.id || '');
});

const currentUserName = computed(() => {
  const session = safeSession();
  return session?.nickname || session?.username || session?.user?.nickname || '创客';
});

function safeSession() {
  try {
    const raw = localStorage.getItem('opchub_user_session');
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function initialOf(name) {
  return String(name || '创').trim().charAt(0).toUpperCase() || '创';
}

function formatTime(value) {
  if (!value) return '刚刚';
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '刚刚';
    const diff = Date.now() - date.getTime();
    if (diff < 60 * 1000) return '刚刚';
    if (diff < 60 * 60 * 1000) return `${Math.floor(diff / 60000)} 分钟前`;
    if (diff < 24 * 60 * 60 * 1000) return `${Math.floor(diff / 3600000)} 小时前`;
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
  } catch (e) {
    return '刚刚';
  }
}

function canDelete(comment) {
  return Boolean(currentUserId.value) && String(comment.author_id) === currentUserId.value;
}

async function loadComments() {
  if (!props.targetId) return;
  loading.value = true;
  try {
    const res = await dispatchGateway(
      'content.comments.list',
      { target_type: props.targetType, target_id: String(props.targetId) },
      { silent: true }
    );
    if (res.ok && res.data) {
      comments.value = Array.isArray(res.data.items) ? res.data.items : [];
      total.value = Number(res.data.total ?? comments.value.length) || 0;
      emit('count-change', total.value);
    }
  } catch (e) {
    comments.value = [];
  } finally {
    loading.value = false;
  }
}

async function submitComment() {
  if (!props.authenticated) {
    emit('require-login');
    return;
  }
  const content = draft.value.trim();
  if (!content || submitting.value) return;
  submitting.value = true;
  try {
    const res = await dispatchGateway('content.comments.create', {
      target_type: props.targetType,
      target_id: String(props.targetId),
      content,
      author_name: currentUserName.value,
    });
    if (res.ok && res.data) {
      comments.value.push(res.data);
      total.value += 1;
      draft.value = '';
      emit('count-change', total.value);
      emit('toast', { title: '评论已发表', message: '你的观点已加入讨论。', type: 'SUCCESS' });
    } else {
      emit('toast', { title: '评论未发表', message: res.error || '请稍后重试。', type: 'ERROR' });
    }
  } catch (e) {
    emit('toast', { title: '评论异常', message: '评论服务暂时不可用，请稍后重试。', type: 'ERROR' });
  } finally {
    submitting.value = false;
  }
}

async function removeComment(comment) {
  if (!comment || deletingId.value) return;
  deletingId.value = comment.id;
  try {
    const res = await dispatchGateway('content.comments.delete', { comment_id: comment.id });
    if (res.ok) {
      comments.value = comments.value.filter((c) => c.id !== comment.id);
      total.value = Math.max(0, total.value - 1);
      emit('count-change', total.value);
      emit('toast', { title: '评论已删除', message: '该评论已从讨论中移除。', type: 'INFO' });
    } else {
      emit('toast', { title: '删除未完成', message: res.error || '请稍后重试。', type: 'ERROR' });
    }
  } catch (e) {
    emit('toast', { title: '删除异常', message: '评论服务暂时不可用，请稍后重试。', type: 'ERROR' });
  } finally {
    deletingId.value = '';
  }
}

function onKeydown(event) {
  if (event.key === 'Escape' && props.visible) {
    emit('close');
  }
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      loadComments();
    }
  }
);

watch(
  () => [props.targetType, props.targetId],
  () => {
    if (props.visible) loadComments();
  }
);

if (typeof window !== 'undefined') {
  window.addEventListener('keydown', onKeydown);
}
</script>

<style scoped>
.ccd-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  background: rgba(10, 14, 22, 0.42);
  backdrop-filter: blur(6px);
  display: flex;
  justify-content: flex-end;
}

.ccd-panel {
  width: min(560px, 94vw);
  height: 100%;
  display: flex;
  flex-direction: column;
  border-radius: 0;
  border-left: 1px solid var(--glass-border, rgba(255, 255, 255, 0.22));
  background: var(--glass-surface, rgba(255, 255, 255, 0.9));
  box-shadow: -24px 0 60px rgba(0, 0, 0, 0.18);
  overflow: hidden;
}

.ccd-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 20px 22px 16px;
  border-bottom: 1px solid var(--glass-border, rgba(120, 130, 150, 0.18));
}

.ccd-heading {
  min-width: 0;
}

.ccd-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ccd-title-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--status-success);
  box-shadow: 0 0 0 4px var(--status-success-soft);
}

.ccd-title {
  margin: 0;
  font-size: 16px;
  font-weight: 750;
  color: var(--text-primary, #1a1c1e);
}

.ccd-count {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  color: var(--status-success);
  background: var(--status-success-soft);
}

.ccd-subtitle {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.4;
  color: var(--text-secondary, #5b6472);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 420px;
}

.ccd-close {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--glass-border, rgba(120, 130, 150, 0.22));
  background: transparent;
  color: var(--text-secondary, #5b6472);
  cursor: pointer;
  font-size: 14px;
  flex-shrink: 0;
}

.ccd-close:hover {
  background: rgba(120, 130, 150, 0.12);
  color: var(--text-primary, #1a1c1e);
}

.ccd-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 22px;
}

.ccd-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ccd-item {
  display: flex;
  gap: 10px;
}

.ccd-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 750;
  color: #fff;
  background: var(--accent);
  flex-shrink: 0;
}

.ccd-item-main {
  flex: 1;
  min-width: 0;
}

.ccd-item-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.ccd-author {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text-primary, #1a1c1e);
}

.ccd-time {
  font-size: 10.5px;
  color: var(--text-tertiary, #8b93a1);
}

.ccd-delete {
  margin-left: auto;
  border: none;
  background: transparent;
  color: var(--status-danger);
  font-size: 10.5px;
  cursor: pointer;
  padding: 2px 4px;
  opacity: 0.7;
}

.ccd-delete:hover {
  opacity: 1;
}

.ccd-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--text-primary, #1a1c1e);
  white-space: pre-wrap;
  word-break: break-word;
}

.ccd-empty {
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  text-align: center;
  color: var(--text-secondary, #5b6472);
  font-size: 12.5px;
}

.ccd-empty-icon {
  font-size: 30px;
}

.ccd-spinner {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid rgba(0, 113, 227, 0.15);
  border-top-color: #0071e3;
  animation: ccd-spin 0.75s linear infinite;
}

.ccd-footer {
  border-top: 1px solid var(--glass-border, rgba(120, 130, 150, 0.18));
  padding: 14px 22px 18px;
  background: color-mix(in srgb, var(--glass-surface, #ffffff) 88%, transparent);
}

.ccd-form-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 8px;
}

.ccd-input {
  width: 100%;
  box-sizing: border-box;
  resize: vertical;
  min-height: 74px;
  max-height: 160px;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid var(--glass-border, rgba(120, 130, 150, 0.25));
  background: rgba(255, 255, 255, 0.55);
  color: var(--text-primary, #1a1c1e);
  font-size: 13px;
  line-height: 1.55;
  outline: none;
}

.ccd-input:focus {
  border-color: rgba(0, 113, 227, 0.55);
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.1);
}

.ccd-hint {
  font-size: 10.5px;
  color: var(--text-tertiary, #8b93a1);
}

.ccd-submit,
.ccd-login-btn {
  border: none;
  border-radius: 999px;
  padding: 8px 18px;
  font-size: 12px;
  font-weight: 700;
  color: #fff;
  background: var(--accent);
  cursor: pointer;
  transition: transform 0.18s ease, opacity 0.18s ease;
}

.ccd-submit:hover:not(:disabled),
.ccd-login-btn:hover {
  transform: translateY(-1px);
}

.ccd-submit:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.ccd-login-hint {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary, #5b6472);
}

.ccd-fade-enter-active,
.ccd-fade-leave-active {
  transition: opacity 0.22s ease;
}

.ccd-fade-enter-active .ccd-panel,
.ccd-fade-leave-active .ccd-panel {
  transition: transform 0.26s cubic-bezier(0.16, 1, 0.3, 1);
}

.ccd-fade-enter-from,
.ccd-fade-leave-to {
  opacity: 0;
}

.ccd-fade-enter-from .ccd-panel,
.ccd-fade-leave-to .ccd-panel {
  transform: translateX(32px);
}

@keyframes ccd-spin {
  to { transform: rotate(360deg); }
}
</style>
