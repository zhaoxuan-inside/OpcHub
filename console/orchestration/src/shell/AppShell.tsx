import { NavLink, Outlet, useNavigate } from "react-router";
import { clearToken, getToken, dispatch } from "@opchub/console-api";
import { Button, useTheme } from "@opchub/console-ui";
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

const NAV = [
  { to: "/overview", label: "总览", icon: "◎" },
  { to: "/operators", label: "算子", icon: "⚙" },
  { to: "/scenarios", label: "场景", icon: "⎇" },
  { to: "/releases", label: "版本与发布", icon: "⎋" },
  { to: "/experiments", label: "实验", icon: "⚗" },
  { to: "/configs", label: "配置管理", icon: "▤" },
];

export function AppShell() {
  const navigate = useNavigate();
  const { theme, toggle } = useTheme();

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
          <span className="text-sm font-semibold tracking-tight">OpcHub 编排管理</span>
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
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-end gap-2 border-b border-border bg-card px-5">
          <Button variant="ghost" onClick={toggle} aria-label="切换主题">
            {theme === "dark" ? "☀" : "☾"}
          </Button>
          <span className="text-sm text-muted-foreground">
            {(session.data as any)?.nickname || (session.data as any)?.email || "…"}
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
        <main className="min-w-0 flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
