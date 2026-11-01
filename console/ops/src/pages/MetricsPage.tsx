/** 指标看板：窗口内按场景聚合调用量/成功率/P95（读时计算自运行记录）+ 实体计数。 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { dispatch } from "@opchub/console-api";
import {
  Card, CardContent, CardHeader, CardTitle, EmptyState, Field, PageHeader,
  PermissionGate, Select, Spinner,
} from "@opchub/console-ui";

interface ScenarioMetric {
  scenario_code: string;
  count: number;
  errors: number;
  error_rate: number;
  avg_ms: number;
  p95_ms: number;
}

export function MetricsPage() {
  const [window, setWindow] = useState(60);
  const metrics = useQuery({
    queryKey: ["ops", "metrics", window],
    queryFn: () => dispatch<{ window_minutes: number; scenarios: ScenarioMetric[] }>("ops.runs.metrics", { window_minutes: window }),
  });
  const rows = metrics.data?.scenarios || [];

  return (
    <div>
      <PageHeader title="指标看板" description="调用量 / 成功率 / 平均与 P95 耗时（读时聚合自运行记录，不预存时序）" />
      <PermissionGate
        permission="platform:audit_read"
        fallback={<Card className="p-6 text-sm text-muted-foreground">需要运维可观测读权限（platform:audit_read）。</Card>}
      >
        <Card className="mb-4">
          <CardContent className="flex items-end gap-3 px-4 py-3">
            <Field label="统计窗口">
              <Select className="h-8 w-36 text-xs" value={window} onChange={(e) => setWindow(Number(e.target.value))}>
                <option value={60}>最近 1 小时</option>
                <option value={360}>最近 6 小时</option>
                <option value={1440}>最近 24 小时</option>
              </Select>
            </Field>
          </CardContent>
        </Card>

        {metrics.isPending ? (
          <Card><CardContent className="flex justify-center py-16"><Spinner /></CardContent></Card>
        ) : !rows.length ? (
          <Card><div className="p-5"><EmptyState title="窗口内暂无运行记录" hint="场景执行后指标即时可见。" /></div></Card>
        ) : (
          <>
            <div className="mb-4 grid gap-4 sm:grid-cols-3">
              <Card>
                <CardHeader><CardTitle className="text-muted-foreground">总调用</CardTitle></CardHeader>
                <CardContent>
                  <div className="text-3xl font-semibold tracking-tight">{rows.reduce((s, r) => s + r.count, 0)}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle className="text-muted-foreground">总错误</CardTitle></CardHeader>
                <CardContent>
                  <div className="text-3xl font-semibold tracking-tight">{rows.reduce((s, r) => s + r.errors, 0)}</div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle className="text-muted-foreground">最慢 P95</CardTitle></CardHeader>
                <CardContent>
                  <div className="text-3xl font-semibold tracking-tight">
                    {Math.max(...rows.map((r) => r.p95_ms))}ms
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card className="mb-4">
              <CardHeader><CardTitle>调用量 × P95（按场景）</CardTitle></CardHeader>
              <CardContent>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={rows}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border, #e5e7eb)" />
                      <XAxis dataKey="scenario_code" tick={{ fontSize: 10 }} interval={0} angle={-20} height={60} textAnchor="end" />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="count" name="调用量" fill="var(--color-primary, #6366f1)" radius={[3, 3, 0, 0]} />
                      <Bar dataKey="errors" name="错误数" fill="var(--color-destructive, #ef4444)" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            <Card>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-muted-foreground">
                    <th className="px-4 py-2.5 font-medium">场景</th>
                    <th className="px-4 py-2.5 font-medium">调用量</th>
                    <th className="px-4 py-2.5 font-medium">错误率</th>
                    <th className="px-4 py-2.5 font-medium">平均</th>
                    <th className="px-4 py-2.5 font-medium">P95</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.scenario_code} className="border-b border-border/60 last:border-0">
                      <td className="px-4 py-2.5 text-xs font-medium">{r.scenario_code}</td>
                      <td className="px-4 py-2.5">{r.count}</td>
                      <td className="px-4 py-2.5">{(r.error_rate * 100).toFixed(1)}%</td>
                      <td className="px-4 py-2.5 text-muted-foreground">{r.avg_ms}ms</td>
                      <td className="px-4 py-2.5 text-muted-foreground">{r.p95_ms}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </>
        )}
      </PermissionGate>
    </div>
  );
}
