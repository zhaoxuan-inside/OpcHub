import { NavLink, Outlet, useNavigate } from "react-router";
import { clearToken, getToken, dispatch } from "@opchub/console-api";
import { Button, PermissionGate, ScopeEmptyHint, ScopeSwitcher, useTheme, useScope } from "@opchub/console-ui";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

const NAV = [
  { to: "/overview", label: "总览", icon: "◎" },
  { to: "/audit", label: "审计与日志", icon: "▤" },
];

const PLATFORM_NAV = [
  { to: "/platform/tenants", label: "租户", icon: "🗄", anyOf: ["platform:tenant_manage", "tenant:member_manage", "tenant:project_create"] },
  { to: "/platform/projects", label: "项目", icon: "🗂", anyOf: ["tenant:project_create", "project:member_manage", "tenant:member_manage"] },
  { to: "/platform/roles", label: "角色与权限", icon: "🔏", anyOf: ["platform:role_manage", "tenant:role_manage"] },
  { to: "/platform/users", label: "用户", icon: "👥", anyOf: ["platform:user_manage"] },
];

export function AppShell() {
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();
  const { myScope } = useScope();

  useEffect(() => {
    if (!getToken()) navigate("/login");
  }, [navigate]);

  const session = useQuery({
    queryKey: ["session"],
    queryFn: () => dispatch("auth.session", {}),
    retry: false,
  });

  useEffect(() => {
    if (session.isError) {
      clearToken();
      navigate("/login");
    }
  }, [session.isError, navigate]);

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-sidebar text-sidebar-foreground">
        <div className="flex h-14 items-center gap-2 border-b border-border px-5">
          <span className="text-sm font-semibold tracking-tight">OpcHub 运维平台</span>
        </div>
        <nav className="flex-1 space-y-0.5 p-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                [
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-primary/10 font-medium text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground",
                ].join(" ")
              }
            >
              <span aria-hidden className="w-4 text-center opacity-80">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
          <div className="mt-4 flex items-center gap-2 px-3 pb-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground/70">
            平台管理
          </div>
          {PLATFORM_NAV.map((item) => (
            <PermissionGate key={item.to} anyOf={item.anyOf}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  [
                    "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                    isActive
                      ? "bg-primary/10 font-medium text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground",
                  ].join(" ")
                }
              >
                <span aria-hidden className="w-4 text-center opacity-80">{item.icon}</span>
                {item.label}
              </NavLink>
            </PermissionGate>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-end gap-3 border-b border-border bg-card px-5">
          <ScopeSwitcher />
          <Button variant="ghost" onClick={toggle} aria-label="切换主题">
            {theme === "dark" ? "☀" : "☾"}
          </Button>
          <span className="text-sm text-muted-foreground">
            {(session.data as any)?.nickname || (session.data as any)?.email || myScope?.user_id || "…"}
          </span>
          <Button
            variant="secondary"
            onClick={async () => {
              try {
                await dispatch("auth.logout", {});
              } catch { /* session may already be gone */ }
              clearToken();
              navigate("/login");
            }}
          >
            退出
          </Button>
        </header>
        <main className="min-w-0 flex-1 space-y-4 p-6">
          <ScopeEmptyHint hint="支撑平台按租户与项目组织操作范围；加入后即可在此切换。" />
          <Outlet />
        </main>
      </div>
    </div>
  );
}
