/** OpcHub unified-gateway client shared by all console SPAs.
 *
 * Every call goes through the single dispatch endpoint with the standard
 * envelope {code, data, message}; the session token rides both the
 * Authorization header and the context payload, mirroring the main app.
 */
const TOKEN_KEY = "opchub_session_token";

export class ApiError extends Error {
  constructor(
    public code: number,
    message: string,
    public traceId?: string,
  ) {
    super(message);
  }
}

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function dispatch<T = any>(
  scenario: string,
  payload: Record<string, unknown> = {},
  version = "v1.0.0",
): Promise<T> {
  const token = getToken();
  const res = await fetch("/api/welcom/opc_world", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      scenario,
      version,
      payload,
      context: { client_timestamp: Date.now(), token },
    }),
  });
  if (!res.ok) {
    throw new ApiError(res.status, `HTTP ${res.status}`);
  }
  const body = await res.json();
  if (body.code !== 200 && body.code !== 201) {
    throw new ApiError(body.code, body.message || "请求失败", body.trace_id);
  }
  return body.data as T;
}
