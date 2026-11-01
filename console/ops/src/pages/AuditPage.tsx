import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import { PermissionGate } from "@opchub/console-ui";
import { Card, EmptyState, Input, PageHeader, Spinner } from "@opchub/console-ui";

interface AuditRow {
  id?: string;
  action: string;
  actor_id: string;
  actor_role?: string;
  result?: string;
  ip_address?: string;
  created_at: string;
  permission?: string;
}

export function AuditPage() {
  const [q, setQ] = useState("");
  const list = useQuery({
    queryKey: ["platform", "audit", q],
    queryFn: () => dispatch<{ logs: AuditRow[]; total: number }>("platform.audit.list", { limit: 200, action: q || undefined }),
  });

  return (
    <div>
      <PageHeader title="审计与日志" description="平台操作留痕检索（RBAC/ABAC 拒绝、场景执行、账号变更）" />
      <PermissionGate
        anyOf={["platform:audit_read", "page:ops_console"]}
        fallback={<Card className="p-6 text-sm text-muted-foreground">需要审计读取权限（platform:audit_read）。</Card>}
      >
        <Card className="mb-4 p-3">
          <Input
            placeholder="按动作过滤（如 rbac.denied / scenario: / auth.）"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="h-8 max-w-sm text-xs"
          />
        </Card>
        <Card>
          {list.isPending ? (
            <div className="flex justify-center py-16"><Spinner /></div>
          ) : !list.data?.logs?.length ? (
            <div className="p-5"><EmptyState title="没有匹配的审计记录" /></div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="px-4 py-2.5 font-medium">时间</th>
                  <th className="px-4 py-2.5 font-medium">动作</th>
                  <th className="px-4 py-2.5 font-medium">操作者</th>
                  <th className="px-4 py-2.5 font-medium">结果</th>
                  <th className="px-4 py-2.5 font-medium">来源 IP</th>
                </tr>
              </thead>
              <tbody>
                {list.data.logs.map((row, idx) => (
                  <tr key={row.id || idx} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">{row.created_at?.slice(0, 19).replace("T", " ")}</td>
                    <td className="px-4 py-2.5">
                      <div className="font-medium">{row.action}</div>
                      {row.permission && <div className="text-xs text-muted-foreground">{row.permission}</div>}
                    </td>
                    <td className="px-4 py-2.5 text-xs">
                      {row.actor_id || "—"}
                      {row.actor_role ? ` · ${row.actor_role}` : ""}
                    </td>
                    <td className="px-4 py-2.5 text-xs">{row.result || "—"}</td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">{row.ip_address || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </PermissionGate>
    </div>
  );
}
