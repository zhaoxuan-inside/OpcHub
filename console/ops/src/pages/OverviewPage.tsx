import { useQuery } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import { PermissionGate, useScope } from "@opchub/console-ui";
import { Card, CardContent, CardHeader, CardTitle, PageHeader, Spinner } from "@opchub/console-ui";

interface MyScopeResp {
  is_platform_super: boolean;
  tenants: unknown[];
  projects: unknown[];
}

export function OverviewPage() {
  const { hasPermission } = useScope();
  const scope = useQuery({
    queryKey: ["platform", "my-scope"],
    queryFn: () => dispatch<MyScopeResp>("platform.scope.my", {}),
  });
  const audit = useQuery({
    queryKey: ["platform", "audit-count"],
    queryFn: () => dispatch<{ logs: unknown[]; total: number }>("platform.audit.list", { limit: 1 }),
    enabled: hasPermission("platform:audit_read") || hasPermission("page:ops_console"),
  });

  const cards = [
    { label: "我的租户", value: scope.data?.tenants?.length ?? 0, hint: "在册的组织实体" },
    { label: "我的项目", value: scope.data?.projects?.length ?? 0, hint: "可操作的项目范围" },
    { label: "平台管理员", value: scope.data?.is_platform_super ? "是" : "否", hint: "平台级通配权限" },
  ];

  return (
    <div>
      <PageHeader title="总览" description="运维平台：治理范围与平台事件一览" />
      <div className="grid gap-4 sm:grid-cols-3">
        {cards.map((c) => (
          <Card key={c.label}>
            <CardHeader>
              <CardTitle className="text-muted-foreground">{c.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-semibold tracking-tight">
                {scope.isPending ? <Spinner /> : (c.value ?? 0)}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{c.hint}</p>
            </CardContent>
          </Card>
        ))}
        <PermissionGate anyOf={["platform:audit_read", "page:ops_console"]}>
          <Card>
            <CardHeader>
              <CardTitle className="text-muted-foreground">审计事件（近期）</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-semibold tracking-tight">
                {audit.isPending ? <Spinner /> : (audit.data?.total ?? 0)}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">审计与日志页可按条件检索</p>
            </CardContent>
          </Card>
        </PermissionGate>
      </div>
    </div>
  );
}
