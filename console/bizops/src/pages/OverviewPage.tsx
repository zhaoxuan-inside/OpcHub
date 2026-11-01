/** 运营总览：真实 KPI（实体在册量/近 24h 场景运行）+ 按日趋势（审计足迹 + 运行记录）。 */
import { useQuery } from "@tanstack/react-query";
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { dispatch } from "@opchub/console-api";
import { Card, CardContent, CardHeader, CardTitle, PageHeader, PermissionGate, Spinner } from "@opchub/console-ui";

interface Overview {
  entities: Record<string, number>;
  runs_24h: number;
}
interface Trend {
  series: Array<{ day: string; events: number; denied: number; active_actors: number; scenario_runs: number }>;
  sample_size: number;
  note: string;
}

const ENTITY_LABELS: Record<string, string> = {
  "user.account": "在册用户",
  "forum.thread": "论坛主题",
  "product.item": "产品橱窗",
  "demands.item": "需求",
  "policy.item": "政策",
  "perk.item": "权益",
  "sop.template": "SOP 模板",
  "interaction.record": "互动记录",
};

export function OverviewPage() {
  const overview = useQuery({
    queryKey: ["bizops", "overview"],
    queryFn: () => dispatch<Overview>("bizops.overview", {}),
  });
  const trend = useQuery({
    queryKey: ["bizops", "trend"],
    queryFn: () => dispatch<Trend>("bizops.trend", { days: 14 }),
  });

  const entities = Object.entries(overview.data?.entities || {});
  const series = trend.data?.series || [];

  return (
    <div>
      <PageHeader title="总览" description="全量真实数据：实体在册量、审计足迹与场景运行（无埋点依赖）" />
      <PermissionGate
        permission="page:bizops_console"
        fallback={<Card className="p-6 text-sm text-muted-foreground">需要运营平台入口权限（page:bizops_console）。</Card>}
      >
        {overview.isPending ? (
          <Card><CardContent className="flex justify-center py-16"><Spinner /></CardContent></Card>
        ) : (
          <div className="mb-4 grid gap-4 sm:grid-cols-4">
            {entities.map(([name, count]) => (
              <Card key={name}>
                <CardHeader><CardTitle className="text-muted-foreground">{ENTITY_LABELS[name] || name}</CardTitle></CardHeader>
                <CardContent>
                  <div className="text-3xl font-semibold tracking-tight">{count}</div>
                </CardContent>
              </Card>
            ))}
            <Card>
              <CardHeader><CardTitle className="text-muted-foreground">近 24h 场景运行</CardTitle></CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold tracking-tight">{overview.data?.runs_24h ?? 0}</div>
              </CardContent>
            </Card>
          </div>
        )}

        <Card>
          <CardHeader>
            <CardTitle>按日趋势（14 天）</CardTitle>
            {trend.data && (
              <p className="text-xs text-muted-foreground">
                {trend.data.note} · 当前样本 {trend.data.sample_size} 条
              </p>
            )}
          </CardHeader>
          <CardContent>
            {trend.isPending ? (
              <div className="flex justify-center py-16"><Spinner /></div>
            ) : (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={series}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border, #e5e7eb)" />
                    <XAxis dataKey="day" tick={{ fontSize: 10 }} tickFormatter={(d: string) => d.slice(5)} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="events" name="审计事件" stroke="#6366f1" dot={false} />
                    <Line type="monotone" dataKey="active_actors" name="活跃操作者" stroke="#22c55e" dot={false} />
                    <Line type="monotone" dataKey="scenario_runs" name="场景运行" stroke="#f59e0b" dot={false} />
                    <Line type="monotone" dataKey="denied" name="拒绝" stroke="#ef4444" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </PermissionGate>
    </div>
  );
}
