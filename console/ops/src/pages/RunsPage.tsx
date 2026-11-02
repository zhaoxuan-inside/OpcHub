/** 运行记录（SigNoz/jaeger 模式）：过滤清单 → 详情节点瀑布（真实 durationMs）。 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Field,
  Input,
  PageHeader,
  PermissionGate,
  Select,
  Spinner,
} from "@opchub/console-ui";

interface RunRow {
  trace_id: string;
  scenario_code: string;
  status: string;
  execution_time_ms: number;
  user_id: string;
  env_key?: string;
  started_at: string;
  error_message: string;
  node_count: number;
  failed_nodes: string[];
}
interface RunDetail extends RunRow {
  node_traces: Array<{ node_id: string; action_handler: string; status: string; duration_ms: number; error?: string; output?: unknown }>;
}

const statusTone: Record<string, "success" | "warning" | "destructive" | "neutral"> = {
  SUCCESS: "success",
  GUARD_REJECTED: "warning",
  FAILED: "destructive",
};

export function RunsPage() {
  const [scenario, setScenario] = useState("");
  const [status, setStatus] = useState("");
  const [envKey, setEnvKey] = useState("");
  const [selected, setSelected] = useState("");

  const list = useQuery({
    queryKey: ["ops", "runs", scenario, status, envKey],
    queryFn: () =>
      dispatch<{ runs: RunRow[]; total: number }>("ops.runs.list", {
        scenario_code: scenario || undefined,
        status: status || undefined,
        env_key: envKey || undefined,
        limit: 200,
      }),
  });
  const detail = useQuery({
    queryKey: ["ops", "run-detail", selected],
    queryFn: () => dispatch<RunDetail>("ops.runs.detail", { trace_id: selected }),
    enabled: Boolean(selected),
  });

  const rows = list.data?.runs || [];
  const maxDuration = Math.max(1, ...(detail.data?.node_traces || []).map((t) => t.duration_ms || 0));

  return (
    <div>
      <PageHeader title="运行记录" description="每次场景执行一条：状态 / 耗时 / 节点瀑布（真实框架计时）" />
      <PermissionGate
        permission="platform:audit_read"
        fallback={<Card className="p-6 text-sm text-muted-foreground">需要运维可观测读权限（platform:audit_read）。</Card>}
      >
        <Card className="mb-4">
          <CardContent className="flex flex-wrap items-end gap-3 px-4 py-3">
            <Field label="场景">
              <Input className="h-8 w-64 text-xs" value={scenario} onChange={(e) => setScenario(e.target.value)}
                placeholder="如 OPC_EXPERIMENT_PIPELINE" />
            </Field>
            <Field label="状态">
              <Select className="h-8 w-32 text-xs" value={status} onChange={(e) => setStatus(e.target.value)}>
                <option value="">全部</option>
                <option value="SUCCESS">SUCCESS</option>
                <option value="FAILED">FAILED</option>
                <option value="GUARD_REJECTED">GUARD_REJECTED</option>
              </Select>
            </Field>
            <Field label="环境">
              <Select className="h-8 w-32 text-xs" value={envKey} onChange={(e) => setEnvKey(e.target.value)}>
                <option value="">全部</option>
                <option value="dev">开发</option>
                <option value="test">测试</option>
                <option value="staging">预上线</option>
                <option value="online">线上</option>
              </Select>
            </Field>
          </CardContent>
        </Card>

        <Card className="mb-4">
          {list.isPending ? (
            <div className="flex justify-center py-16"><Spinner /></div>
          ) : !rows.length ? (
            <div className="p-5"><EmptyState title="没有匹配的运行记录" hint="记录随场景执行实时产生，保留期默认 14 天。" /></div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="px-4 py-2.5 font-medium">时间</th>
                  <th className="px-4 py-2.5 font-medium">场景</th>
                  <th className="px-4 py-2.5 font-medium">状态</th>
                  <th className="px-4 py-2.5 font-medium">耗时</th>
                  <th className="px-4 py-2.5 font-medium">节点</th>
                  <th className="px-4 py-2.5 font-medium">操作者</th>
                  <th className="px-4 py-2.5 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.trace_id} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">{r.started_at?.slice(11, 19)}</td>
                    <td className="px-4 py-2.5 text-xs font-medium">
                      {r.scenario_code}
                      {r.env_key ? <Badge className="ml-1">{r.env_key}</Badge> : null}
                    </td>
                    <td className="px-4 py-2.5"><Badge tone={statusTone[r.status] || "neutral"}>{r.status}</Badge></td>
                    <td className="px-4 py-2.5 text-xs">{r.execution_time_ms}ms</td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">
                      {r.node_count}
                      {r.failed_nodes?.length ? <span className="text-destructive">（失败 {r.failed_nodes.length}）</span> : null}
                    </td>
                    <td className="px-4 py-2.5 text-xs text-muted-foreground">{r.user_id || "—"}</td>
                    <td className="px-4 py-2.5">
                      <Button variant="secondary" className="h-7 text-xs" onClick={() => setSelected(r.trace_id)}>
                        瀑布
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        {selected && detail.data && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">
                  节点瀑布 · {detail.data.scenario_code}
                  <Badge tone={statusTone[detail.data.status] || "neutral"} className="ml-2">{detail.data.status}</Badge>
                </CardTitle>
                <Button variant="secondary" className="h-7 text-xs" onClick={() => setSelected("")}>收起</Button>
              </div>
              <p className="text-xs text-muted-foreground">
                trace {detail.data.trace_id} · 总耗时 {detail.data.execution_time_ms}ms
                {detail.data.error_message ? ` · ${detail.data.error_message}` : ""}
              </p>
            </CardHeader>
            <CardContent className="space-y-1.5">
              {(detail.data.node_traces || []).map((t) => (
                <div key={t.node_id} className="flex items-center gap-2 text-xs">
                  <span className="w-40 shrink-0 truncate font-medium">{t.node_id}</span>
                  <span className="w-56 shrink-0 truncate text-muted-foreground">{t.action_handler}</span>
                  <div className="h-4 min-w-0 flex-1 rounded-sm bg-muted/60">
                    <div
                      className={`h-4 rounded-sm ${t.status === "SUCCESS" ? "bg-primary/60" : t.status === "SKIPPED" ? "bg-muted-foreground/40" : "bg-destructive/70"}`}
                      style={{ width: `${Math.max(3, ((t.duration_ms || 0) / maxDuration) * 100)}%` }}
                      title={`${t.duration_ms}ms`}
                    />
                  </div>
                  <span className="w-20 shrink-0 text-right text-muted-foreground">{t.duration_ms}ms</span>
                  <Badge tone={t.status === "SUCCESS" ? "success" : t.status === "SKIPPED" ? "neutral" : "destructive"}>
                    {t.status}
                  </Badge>
                  {t.error && <span className="w-64 truncate text-destructive">{t.error}</span>}
                </div>
              ))}
              <div className="pt-2">
                <div className="mb-1 text-xs font-medium text-muted-foreground">最终输出（截断展示）</div>
                <pre className="max-h-40 overflow-auto rounded-md border border-border bg-muted/30 p-2.5 font-mono text-[11px]">
                  {JSON.stringify(detail.data.node_traces?.find((t) => t.output)?.output ?? "—", null, 2)}
                </pre>
              </div>
            </CardContent>
          </Card>
        )}
      </PermissionGate>
    </div>
  );
}
