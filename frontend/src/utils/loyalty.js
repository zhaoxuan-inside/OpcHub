/**
 * 积分阅读埋点与通用格式化。
 *
 * 阅读积分由后端 `loyalty.content.read` 场景结算：同一读者 + 同一内容 + 同一天
 * 只计一次，因此前端只需在打开详情时上报一次，重复上报由后端幂等键兜底。
 */
import { dispatchGateway } from '@/api/gateway';

const READ_CACHE_KEY = 'opchub_loyalty_read_cache';

function todayKey() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

function loadReadCache() {
  try {
    const raw = localStorage.getItem(READ_CACHE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (e) {
    return {};
  }
}

function saveReadCache(cache) {
  try {
    localStorage.setItem(READ_CACHE_KEY, JSON.stringify(cache));
  } catch (e) {
    // 本地缓存不可用时不影响阅读
  }
}

/**
 * 上报一次内容阅读（作者获得小额积分，读者不扣分）。
 * @param {string} targetType POLICY / PRODUCT / DEMAND / FORUM_THREAD / PERK
 * @param {string} targetId
 */
export function trackContentRead(targetType, targetId) {
  const token = localStorage.getItem('opchub_session_token');
  if (!token || !targetType || !targetId) return;
  const key = `${todayKey()}|${targetType}|${targetId}`;
  const cache = loadReadCache();
  if (cache[key]) return;
  cache[key] = 1;
  // 只保留当天，避免 localStorage 无限增长
  const prefix = `${todayKey()}|`;
  Object.keys(cache).forEach((item) => {
    if (!item.startsWith(prefix)) delete cache[item];
  });
  saveReadCache(cache);
  dispatchGateway(
    'loyalty.content.read',
    { target_type: targetType, target_id: String(targetId) },
    { silent: true }
  ).catch(() => {});
}

/** 千分位积分格式，例：12,480 */
export function formatPoints(value) {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) return '0';
  return num.toLocaleString('zh-CN');
}

/** 积分收支带符号格式 */
export function formatPointsDelta(value) {
  const num = Number(value || 0);
  if (num > 0) return `+${formatPoints(num)}`;
  if (num < 0) return `-${formatPoints(Math.abs(num))}`;
  return '0';
}

export function formatDate(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

export function formatDateTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return `${formatDate(value)} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}
