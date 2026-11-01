/** Active tenant/project scope shared by all console SPAs.
 *
 * 分租户·分项目操作的活动上下文：持久化在 localStorage（每个 SPA 同源共享），
 * dispatch() 自动把 tenant_id/project_id 注入请求 context，后端网关据此做
 * scope 隔离授权。切换时广播 window 事件，便于 React Query 重新拉取。
 */
const SCOPE_KEY = "opchub_console_scope";

export interface ConsoleScope {
  tenantId: string;
  projectId: string;
}

const EMPTY_SCOPE: ConsoleScope = { tenantId: "", projectId: "" };

export function getScope(): ConsoleScope {
  try {
    const raw = localStorage.getItem(SCOPE_KEY);
    if (!raw) return { ...EMPTY_SCOPE };
    const parsed = JSON.parse(raw) as Partial<ConsoleScope>;
    return {
      tenantId: String(parsed.tenantId || ""),
      projectId: String(parsed.projectId || ""),
    };
  } catch {
    return { ...EMPTY_SCOPE };
  }
}

export function setScope(scope: ConsoleScope) {
  localStorage.setItem(SCOPE_KEY, JSON.stringify(scope));
  window.dispatchEvent(new CustomEvent("opchub:scope-changed", { detail: scope }));
}

export function clearScope() {
  localStorage.removeItem(SCOPE_KEY);
  window.dispatchEvent(new CustomEvent("opchub:scope-changed", { detail: { ...EMPTY_SCOPE } }));
}

export function onScopeChange(cb: (scope: ConsoleScope) => void): () => void {
  const handler = (event: Event) => cb((event as CustomEvent<ConsoleScope>).detail || getScope());
  window.addEventListener("opchub:scope-changed", handler);
  return () => window.removeEventListener("opchub:scope-changed", handler);
}
