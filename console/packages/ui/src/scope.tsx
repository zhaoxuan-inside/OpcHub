/** Scope context: 我的身份、可操作的租户/项目、生效权限（分租户·分权限前端镜像）。
 *
 * 数据源是后端 platform.scope.my；活动选择持久化在 console-api 的 scope 存储，
 * dispatch 自动注入 context。权限判定与后端同构：平台超管通配，PLATFORM ∪
 * 活动租户 ∪ 活动项目 的角色权限并集。
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  dispatch,
  getScope,
  onScopeChange,
  setScope as persistScope,
  type ConsoleScope,
} from "@opchub/console-api";
import { Badge, Button, Card, CardContent, cn } from "./primitives";

interface RoleSummary {
  role_id: string;
  name: string;
  code: string;
  permissions: string[];
}

interface MyScope {
  user_id: string;
  is_platform_super: boolean;
  tenants: Array<{
    tenant_id: string;
    code: string;
    name: string;
    status: string;
    role: RoleSummary;
  }>;
  projects: Array<{
    project_id: string;
    tenant_id: string;
    tenant_name: string;
    key: string;
    name: string;
    status: string;
    role: RoleSummary;
  }>;
  platform_roles: RoleSummary[];
}

interface ScopeContextValue {
  myScope: MyScope | undefined;
  loading: boolean;
  scope: ConsoleScope;
  activeTenant: MyScope["tenants"][number] | undefined;
  activeProject: MyScope["projects"][number] | undefined;
  selectTenant: (tenantId: string) => void;
  selectProject: (projectId: string) => void;
  hasPermission: (permission: string) => boolean;
  refresh: () => void;
}

const ScopeContext = createContext<ScopeContextValue | null>(null);

export function ScopeProvider({ children }: { children: ReactNode }) {
  const [scope, setLocalScope] = useState<ConsoleScope>(() => getScope());

  useEffect(() => {
    return onScopeChange((next) => setLocalScope(next));
  }, []);

  const q = useQuery({
    queryKey: ["platform", "my-scope"],
    queryFn: () => dispatch<MyScope>("platform.scope.my", {}),
    retry: false,
  });

  const myScope = q.data;

  // 活动项目决定活动租户（项目挂在租户下）；悬空选择自动回落
  const activeProject = useMemo(
    () => myScope?.projects.find((p) => p.project_id === scope.projectId),
    [myScope, scope.projectId],
  );
  const effectiveTenantId = activeProject?.tenant_id || scope.tenantId;
  const activeTenant = useMemo(
    () => myScope?.tenants.find((t) => t.tenant_id === effectiveTenantId),
    [myScope, effectiveTenantId],
  );

  const selectTenant = useCallback(
    (tenantId: string) => {
      const next = { tenantId, projectId: "" };
      persistScope(next);
      setLocalScope(next);
    },
    [],
  );

  const selectProject = useCallback(
    (projectId: string) => {
      const project = myScope?.projects.find((p) => p.project_id === projectId);
      const next = { tenantId: project?.tenant_id || "", projectId };
      persistScope(next);
      setLocalScope(next);
    },
    [myScope],
  );

  const hasPermission = useCallback(
    (permission: string) => {
      if (!myScope) return false;
      if (myScope.is_platform_super) return true;
      const granted = new Set<string>();
      for (const role of myScope.platform_roles || []) {
        for (const p of role.permissions || []) granted.add(p);
      }
      if (activeTenant?.role) {
        for (const p of activeTenant.role.permissions || []) granted.add(p);
      }
      if (activeProject?.role) {
        for (const p of activeProject.role.permissions || []) granted.add(p);
      }
      return granted.has(permission) || granted.has("*");
    },
    [myScope, activeTenant, activeProject],
  );

  const refresh = useCallback(() => {
    q.refetch();
  }, [q]);

  const value: ScopeContextValue = {
    myScope,
    loading: q.isPending,
    scope: { tenantId: effectiveTenantId || "", projectId: activeProject?.project_id || "" },
    activeTenant,
    activeProject,
    selectTenant,
    selectProject,
    hasPermission,
    refresh,
  };

  return <ScopeContext.Provider value={value}>{children}</ScopeContext.Provider>;
}

export function useScope(): ScopeContextValue {
  const ctx = useContext(ScopeContext);
  if (!ctx) throw new Error("useScope 必须在 ScopeProvider 内使用");
  return ctx;
}

/** 条件渲染：仅在持有指定权限点（或任一权限点）时渲染 children。 */
export function PermissionGate({
  permission,
  anyOf,
  children,
  fallback = null,
}: {
  permission?: string;
  anyOf?: string[];
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { hasPermission, loading } = useScope();
  if (loading) return null;
  const granted = permission ? hasPermission(permission) : false;
  const grantedAny = (anyOf || []).some((p) => hasPermission(p));
  return <>{granted || grantedAny ? children : fallback}</>;
}

/** 租户 → 项目级联切换器（支撑平台头部）。 */
export function ScopeSwitcher({ className }: { className?: string }) {
  const { myScope, activeTenant, activeProject, selectTenant, selectProject } = useScope();

  if (!myScope) return null;
  const projects = myScope.projects.filter(
    (p) => !activeTenant || p.tenant_id === activeTenant.tenant_id,
  );

  return (
    <Card className={cn("border-border/60", className)}>
      <CardContent className="flex flex-wrap items-center gap-2 px-3 py-2">
        <span className="text-xs font-medium text-muted-foreground">范围</span>
        <select
          aria-label="选择租户"
          className="h-8 rounded-md border border-border bg-background px-2 text-xs"
          value={activeTenant?.tenant_id || ""}
          onChange={(e) => selectTenant(e.target.value)}
        >
          <option value="">未选租户</option>
          {myScope.tenants.map((t) => (
            <option key={t.tenant_id} value={t.tenant_id}>
              {t.name}
            </option>
          ))}
        </select>
        <select
          aria-label="选择项目"
          className="h-8 rounded-md border border-border bg-background px-2 text-xs"
          value={activeProject?.project_id || ""}
          onChange={(e) => selectProject(e.target.value)}
        >
          <option value="">未选项目</option>
          {projects.map((p) => (
            <option key={p.project_id} value={p.project_id}>
              {p.name}
            </option>
          ))}
        </select>
        {activeProject?.role?.name ? (
          <Badge tone="primary">{activeProject.role.name}</Badge>
        ) : activeTenant?.role?.name ? (
          <Badge>{activeTenant.role.name}</Badge>
        ) : null}
      </CardContent>
    </Card>
  );
}

/** 无任何租户/项目授权时的空态引导。 */
export function ScopeEmptyHint({ hint }: { hint?: string }) {
  const { myScope, loading } = useScope();
  if (loading || !myScope) return null;
  if (myScope.is_platform_super || myScope.tenants.length > 0) return null;
  return (
    <Card className="border-dashed">
      <CardContent className="flex flex-col items-start gap-2 px-5 py-4">
        <div className="text-sm font-medium">尚未加入任何租户</div>
        <div className="text-xs text-muted-foreground">
          {hint || "请联系平台管理员将你加入租户与项目，或申请相应权限。"}
        </div>
        <Button variant="secondary" className="h-7 text-xs" onClick={() => window.location.reload()}>
          刷新授权
        </Button>
      </CardContent>
    </Card>
  );
}
