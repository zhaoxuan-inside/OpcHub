import { ref } from 'vue';

/**
 * Global reactive notification state for VisionOS liquid glass toast capsules.
 */
export const activeNotice = ref(null);
let noticeTimer = null;

/**
 * Trigger a user-friendly UI toast notification.
 * @param {Object} options
 * @param {string} [options.title] - Notification headline
 * @param {string} [options.message] - Descriptive message
 * @param {'SUCCESS'|'ERROR'|'WARN'|'INFO'} [options.type='INFO'] - Visual semantic type
 * @param {number} [options.duration=4500] - Auto-dismiss timeout (ms). Pass 0 to persist.
 */
export function notify({ title, message, type = 'INFO', duration = 4500 }) {
  const normalizedType = (type || 'INFO').toUpperCase();
  const defaultTitle = {
    SUCCESS: '操作成功',
    ERROR: '服务请求受阻',
    WARN: '注意事项',
    INFO: '系统提示',
  }[normalizedType] || '系统提示';

  activeNotice.value = {
    id: Date.now(),
    title: title || defaultTitle,
    message: message || '',
    type: normalizedType,
  };

  if (noticeTimer) {
    clearTimeout(noticeTimer);
    noticeTimer = null;
  }

  if (duration > 0) {
    noticeTimer = setTimeout(() => {
      activeNotice.value = null;
    }, duration);
  }
}

/**
 * Immediately dismiss the currently active notification.
 */
export function dismissNotice() {
  if (noticeTimer) {
    clearTimeout(noticeTimer);
    noticeTimer = null;
  }
  activeNotice.value = null;
}
