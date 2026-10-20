/**
 * OpcHub Unified Inbound Gateway Client
 * Calls /api/welcom/opc_world with version governance, authorization injection,
 * and unified error interception & user-friendly presentation.
 */
import { notify } from './notification';

/**
 * Field name translations for Pydantic / Schema validation messages
 */
const FIELD_NAMES_ZH = {
  email: '创客邮箱',
  account: '创客账号',
  password: '登录密码',
  old_password: '旧密码',
  new_password: '新密码',
  code: '验证码',
  verification_code: '邮箱验证码',
  captcha_code: '图形验证码',
  captcha_id: '验证码识别标',
  nickname: '创客昵称',
  company_name: '企业或工作室名称',
  credit_code: '统一社会信用代码',
  phone: '联系手机号',
  token: '登录鉴权凭证',
  scenario: '网关调用场景',
  product_id: '作品标识',
  amount: '充值金额',
};

/**
 * Humanize raw backend error response into a friendly Chinese message
 */
export function humanizeError(rawError, statusCode = 0) {
  if (!rawError && !statusCode) {
    return '请求执行异常，请稍后再试';
  }

  // 1. If rawError is a string
  if (typeof rawError === 'string') {
    const trimmed = rawError.trim();

    // Check if it's a Pydantic string representation (e.g., "1 validation error for...")
    if (trimmed.includes('validation error for') || trimmed.includes('[type=')) {
      const fieldMatches = trimmed.match(/([a-zA-Z0-9_]+)\s+Field required/);
      if (fieldMatches && fieldMatches[1]) {
        const fieldName = FIELD_NAMES_ZH[fieldMatches[1]] || fieldMatches[1];
        return `请填写必填项：${fieldName}`;
      }
      if (trimmed.includes('String should have at least')) {
        return '输入字符长度不足，请按规范补充完整';
      }
      return '提交的信息不完整或格式有误，请核验后重新提交';
    }

    // Check common English network / server errors
    const lower = trimmed.toLowerCase();
    if (lower.includes('failed to fetch') || lower.includes('networkerror')) {
      return '网络通信异常，请检查网络连接或确认后台网关服务已启动';
    }
    if (lower.includes('internal server error')) {
      return '服务暂时响应异常，系统正在恢复中，请稍候再试';
    }
    if (lower.includes('bad gateway') || lower.includes('gateway timeout')) {
      return '网关节点正在热重载或服务连接中断，请稍后刷新重试';
    }

    // If it contains Chinese characters and is reasonable length, keep it
    if (/[\u4e00-\u9fa5]/.test(trimmed)) {
      return trimmed;
    }
  }

  // 2. If it's a Pydantic array of errors (e.g. HTTP 422)
  if (Array.isArray(rawError)) {
    const missingFields = [];
    const generalIssues = [];
    for (const item of rawError) {
      const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : '';
      const fieldZh = FIELD_NAMES_ZH[field] || field;
      if (item.type === 'missing' || (item.msg && item.msg.includes('Field required'))) {
        if (fieldZh) missingFields.push(fieldZh);
      } else if (item.msg) {
        generalIssues.push(fieldZh ? `${fieldZh}格式不合规` : item.msg);
      }
    }
    if (missingFields.length > 0) {
      return `请填写必填项：${missingFields.join('、')}`;
    }
    if (generalIssues.length > 0) {
      return generalIssues.join('；');
    }
    return '提交的数据校验未通过，请检查所填内容';
  }

  // 3. If rawError is an object
  if (typeof rawError === 'object' && rawError !== null) {
    if (rawError.detail) {
      return humanizeError(rawError.detail, statusCode);
    }
    if (rawError.message) {
      return humanizeError(rawError.message, statusCode);
    }
    if (rawError.error) {
      return humanizeError(rawError.error, statusCode);
    }
  }

  // 4. HTTP Status Code fallbacks
  switch (statusCode) {
    case 400:
      return '请求参数或格式有误，请核实后重试';
    case 401:
      return '登录凭据已失效或未登录，请重新登录创客账号';
    case 403:
      return '权限受限，您当前的角色无法执行该操作';
    case 404:
      return '所请求的服务场景或业务资源未就绪 (404)';
    case 422:
      return '数据校验未通过，请检查表单字段是否合规';
    case 429:
      return '操作过于频繁，触发系统防刷保护，请稍候再试';
    case 500:
      return '服务器响应异常，已记录错误日志，请稍候重试';
    case 502:
    case 503:
    case 504:
      return '网关服务暂时不可用或正在热重载，请稍候再试';
    default:
      return '系统网络请求异常，请稍后重试';
  }
}

/**
 * Dispatch an inbound scenario to OpcHub Gateway.
 *
 * @param {string} scenario - Gateway scenario identifier (e.g. 'auth.login')
 * @param {Object} [payload={}] - Request payload
 * @param {Object} [context={}] - Metadata & interceptor options
 * @param {boolean} [context.silent=false] - If true, do not pop a global error toast on failure
 * @param {string} [context.errorTitle] - Custom title for the error toast
 */
export async function dispatchGateway(scenario, payload = {}, context = {}) {
  const token = localStorage.getItem('opchub_session_token') || '';
  const { silent = false, errorTitle, ...restContext } = context;

  const body = {
    scenario,
    version: 'v1.0.0',
    payload,
    context: {
      client_timestamp: new Date().toISOString(),
      token,
      ...restContext,
    },
  };

  try {
    const res = await fetch('/api/welcom/opc_world', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    });

    const data = await res.json().catch(() => ({}));

    // Success response: HTTP 200/201 and payload code 200/201
    if (res.ok && data && (data.code === 200 || data.code === 201)) {
      return { ok: true, data: data.data, raw: data };
    }

    // Intercept error and humanize into user-friendly message
    const rawError = data?.message || data?.detail || data?.error || (res.statusText !== 'OK' ? res.statusText : null);
    const friendlyError = humanizeError(rawError, res.status);

    // Pop user-friendly toast unless explicitly silenced
    if (!silent) {
      notify({
        title: errorTitle || (res.status >= 500 ? '服务处理受阻' : '操作未完成'),
        message: friendlyError,
        type: 'ERROR',
      });
    }

    return {
      ok: false,
      error: friendlyError,
      statusCode: res.status,
      raw: data,
    };
  } catch (err) {
    console.error(`[Gateway Error] scenario ${scenario}:`, err);
    const friendlyError = humanizeError(err.message, 0);

    if (!silent) {
      notify({
        title: errorTitle || '网络连接异常',
        message: friendlyError,
        type: 'ERROR',
      });
    }

    return {
      ok: false,
      error: friendlyError,
      statusCode: 0,
      raw: err,
    };
  }
}
