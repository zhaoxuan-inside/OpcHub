/**
 * OpcHub Unified Inbound Gateway Client
 * Calls /api/welcom/opc_world with version governance and authorization injection.
 */

export async function dispatchGateway(scenario, payload = {}, context = {}) {
  const token = localStorage.getItem('opchub_session_token') || '';
  const body = {
    scenario,
    version: 'v1.0.0',
    payload,
    context: {
      client_timestamp: new Date().toISOString(),
      token,
      ...context,
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

    if (res.ok && data && (data.code === 200 || data.code === 201)) {
      return { ok: true, data: data.data, raw: data };
    }

    return {
      ok: false,
      error: data.message || (data.detail && typeof data.detail === 'string' ? data.detail : '网关请求失败'),
      raw: data,
    };
  } catch (err) {
    console.error(`[Gateway Error] scenario ${scenario}:`, err);
    return {
      ok: false,
      error: err.message || '网络连接异常，请检查服务状态',
    };
  }
}
