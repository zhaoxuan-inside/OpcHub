<template>
  <Teleport to="body">
    <transition name="modal-fade">
      <div v-if="visible" class="post-modal-backdrop" @click="handleBackdropClick">
        <div class="post-modal-container glass-box" @click.stop>
          <!-- Modal Header -->
          <div class="modal-head">
            <div class="head-left">
              <div class="icon-orb">
                <ForumIcon name="spark" size="20" />
              </div>
              <div>
                <h2 class="modal-title">发起创客头脑风暴</h2>
                <p class="modal-subtitle">分享出海实战、架构避坑或提出待验证的商业假设</p>
              </div>
            </div>
            <button class="btn-close-modal" @click="$emit('close')">
              <ForumIcon name="close" size="18" />
            </button>
          </div>

          <!-- Form Area -->
          <div class="modal-body">
            <!-- Category Selection -->
            <div class="form-group">
              <label class="form-label">
                <span>风暴主题分类</span>
                <span class="required-star">*</span>
              </label>
              <div class="category-radio-group">
                <button
                  v-for="cat in categoryOptions"
                  :key="cat.code"
                  type="button"
                  class="cat-chip"
                  :class="{ active: selectedCategory === cat.code }"
                  @click="selectedCategory = cat.code"
                >
                  <span class="chip-dot" :style="{ background: cat.color }"></span>
                  <span>{{ cat.label }}</span>
                </button>
              </div>
            </div>

            <!-- Title -->
            <div class="form-group">
              <label class="form-label">
                <span>风暴帖标题</span>
                <span class="required-star">*</span>
              </label>
              <input
                v-model="title"
                type="text"
                class="glass-input input-liquid"
                placeholder="一句话清晰描述您的实战主题或核心痛点（如：独立开发者 Stripe 绑定香港银行结汇合规避坑）"
                maxlength="100"
              />
            </div>

            <!-- Content -->
            <div class="form-group">
              <div class="form-label-row">
                <label class="form-label">
                  <span>实战复盘 / 经验正文</span>
                  <span class="required-star">*</span>
                </label>
                <span class="mono-counter">{{ content.length }} 字</span>
              </div>
              <textarea
                v-model="content"
                class="glass-input input-liquid content-textarea"
                rows="7"
                placeholder="在此详细展开您的思考、实践过程、踩坑经验与解决方案。支持 Markdown 语法与代码块排版..."
              ></textarea>
            </div>

            <!-- Tags -->
            <div class="form-group">
              <label class="form-label">
                <span>话题关键词 (可选，用逗号或空格隔开)</span>
              </label>
              <input
                v-model="rawTags"
                type="text"
                class="glass-input input-liquid"
                placeholder="如: Stripe, 香港公司, 结汇合规"
              />
            </div>

            <!-- Compliance Tip -->
            <div class="compliance-note">
              <ForumIcon name="shield" size="14" />
              <span>发帖将遵循《创客社区自律公约》，自动附带真实 IP 属地展示并经过敏感词与安全审查。</span>
            </div>
          </div>

          <!-- Modal Footer -->
          <div class="modal-footer">
            <button class="btn-secondary" @click="$emit('close')">
              取消
            </button>
            <button
              class="btn-liquid btn-primary-submit"
              :disabled="!isFormValid || isSubmitting"
              @click="handleSubmit"
            >
              <ForumIcon name="send" size="13" />
              <span>{{ isSubmitting ? '正在发布...' : '立即发布风暴帖' }}</span>
            </button>
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue';
import ForumIcon from '@/components/ForumIcon.vue';
import { dispatchGateway } from '@/api/gateway';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false,
  },
  userSession: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(['close', 'toast', 'success']);

const categoryOptions = [
  { code: 'DEV', label: '技术踩坑', color: '#0071E3' },
  { code: 'BIZ', label: '独立出海', color: '#00c6ff' },
  { code: 'TAX', label: '工商财税', color: '#e67e22' },
  { code: 'AGENTS', label: 'AI智能体', color: '#a855f7' },
  { code: 'POLICY', label: '政策申报', color: '#10b981' },
];

const selectedCategory = ref('DEV');
const title = ref('');
const content = ref('');
const rawTags = ref('');
const isSubmitting = ref(false);

const isFormValid = computed(() => {
  return title.value.trim().length >= 4 && content.value.trim().length >= 10;
});

function handleBackdropClick() {
  emit('close');
}

async function handleSubmit() {
  if (!isFormValid.value || isSubmitting.value) return;

  isSubmitting.value = true;

  const parsedTags = rawTags.value
    .split(/[,，\s]+/)
    .map((t) => t.trim().replace(/^#/, ''))
    .filter(Boolean);

  const authorId = props.userSession?.id || 'maker-local';
  const authorName = props.userSession?.nickname || '认证创客';

  const threadPayload = {
    category_code: selectedCategory.value,
    author_id: authorId,
    title: title.value.trim(),
    content: content.value.trim(),
  };

  try {
    const res = await dispatchGateway('forum.threads.publish', {
      thread_payload: threadPayload,
    }, { silent: true });

    const newThread = {
      id: res.data?.id || `local-thread-${Date.now()}`,
      category_code: selectedCategory.value,
      category: categoryOptions.find((c) => c.code === selectedCategory.value)?.label || '实战风暴',
      title: title.value.trim(),
      snippet: content.value.trim().slice(0, 120) + (content.value.length > 120 ? '...' : ''),
      content: content.value.trim(),
      author: authorName,
      author_id: authorId,
      ip_location: '来自 浙江',
      replies: 0,
      upvotes: 1,
      is_upvoted: true,
      pinned: null,
      updated_at: '刚刚',
      tags: parsedTags,
    };

    emit('toast', {
      title: '风暴帖发布成功',
      message: `《${newThread.title}》已发布成功并在社区看板实时上架！`,
      type: 'SUCCESS',
    });

    emit('success', newThread);
    emit('close');

    // Reset form
    title.value = '';
    content.value = '';
    rawTags.value = '';
  } catch (err) {
    emit('toast', {
      title: '发布受阻',
      message: err.message || '网关处理异常，请检查输入或稍后重试',
      type: 'ERROR',
    });
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.post-modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  z-index: 1050;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.post-modal-container {
  width: 620px;
  max-width: 95vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: var(--radius-lg, 20px);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.25);
  background: var(--glass-surface-solid, #FFFFFF);
  border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.85));
}

[data-theme="dark"] .post-modal-container {
  background: var(--glass-surface-solid, #151720);
  border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.14));
}

/* Modal Head */
.modal-head {
  padding: 20px 24px;
  border-bottom: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.06));
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.head-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.icon-orb {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: var(--accent-glass, rgba(0, 113, 227, 0.08));
  color: var(--accent, #0071E3);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary, #121316);
  margin: 0 0 2px 0;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-tertiary, #7D828D);
  margin: 0;
}

.btn-close-modal {
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--text-tertiary, #7D828D);
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-close-modal:hover {
  background: var(--glass-surface-hover, rgba(0, 0, 0, 0.05));
  color: var(--text-primary, #121316);
}

/* Modal Body */
.modal-body {
  padding: 20px 24px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, #121316);
  display: flex;
  align-items: center;
  gap: 4px;
}

.required-star {
  color: #ff3b30;
}

.mono-counter {
  font-size: 11px;
  font-family: var(--font-mono, monospace);
  color: var(--text-tertiary, #7D828D);
}

/* Category Radios */
.category-radio-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.cat-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-sm, 8px);
  border: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.08));
  background: var(--glass-surface-subtle, rgba(245, 247, 252, 0.5));
  color: var(--text-secondary, #4B4E56);
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.cat-chip:hover {
  border-color: var(--accent, #0071E3);
  color: var(--accent, #0071E3);
}

.cat-chip.active {
  background: var(--accent-glass, rgba(0, 113, 227, 0.08));
  border-color: var(--accent, #0071E3);
  color: var(--accent, #0071E3);
  font-weight: 600;
}

.chip-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.content-textarea {
  resize: vertical;
  min-height: 120px;
  line-height: 1.6;
}

.compliance-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--radius-sm, 8px);
  background: rgba(0, 113, 227, 0.04);
  border: 1px solid rgba(0, 113, 227, 0.12);
  color: var(--text-secondary, #4B4E56);
  font-size: 11.5px;
  line-height: 1.5;
}

.compliance-note svg {
  color: var(--accent, #0071E3);
  flex-shrink: 0;
  margin-top: 1px;
}

/* Modal Footer */
.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--glass-border-subtle, rgba(0, 0, 0, 0.06));
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: var(--glass-surface, rgba(255, 255, 255, 0.65));
}

.btn-secondary {
  padding: 8px 18px;
  border-radius: var(--radius-sm, 8px);
  border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.12));
  background: transparent;
  color: var(--text-secondary, #4B4E56);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-secondary:hover {
  background: var(--glass-surface-hover, rgba(0, 0, 0, 0.05));
  color: var(--text-primary, #121316);
}

.btn-primary-submit {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 600;
}

.btn-primary-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Transitions */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}
</style>
