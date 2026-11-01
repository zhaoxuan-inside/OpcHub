/** 业务漏斗：步骤动作 × 去重操作者（口径如实披露：非严格时序）。 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { dispatch } from "@opchub/console-api";
import {
  Button, Card, CardContent, CardHeader, CardTitle, EmptyState, Field,
  PageHeader, PermissionGate, Select, useToast,
} from "@opchub/console-ui";

interface FunnelStep {
  step: string;
  actors: number;
  conversion_from_first: number;
}

export function FunnelPage() {
  const { toast } = useToast();
  const actions = useQuery({
    queryKey: ["bizops", "actions"],
    queryFn: () => dispatch<{ actions: Array<{ action: string; count: number }>; sample_size: number; note: string }>("bizops.actions", {}),
  });
  const [steps, setSteps] = useState<string[]>(["auth.login"]);
  const [result, setResult] = useState<{ steps: FunnelStep[]; sample_size: number; note: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const topActions = (actions.data?.actions || []).filter((a) => !steps.includes(a.action));

  const run = async () => {
    setBusy(true);
    try {
      const res = await dispatch<{ steps: FunnelStep[]; sample_size: number; note: string }>(
        "bizops.funnel", { steps },
      );
      setResult(res);
    } catch (err) {
      toast({ title: "漏斗计算失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <PageHeader title="业务漏斗" description="按步骤动作统计去重操作者与首步转化（口径：足迹去重，非严格时序）" />
      <PermissionGate
        permission="page:bizops_console"
        fallback={<Card className="p-6 text-sm text-muted-foreground">需要运营平台入口权限（page:bizops_console）。</Card>}
      >
        <Card className="mb-4">
          <CardHeader>
            <CardTitle>漏斗步骤</CardTitle>
            {actions.data && (
              <p className="text-xs text-muted-foreground">
                {actions.data.note} · 样本 {actions.data.sample_size} 条
              </p>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            {steps.map((step, i) => (
              <div key={i} className="flex items-center gap-2">
                <Badge>{i + 1}</Badge>
                <Select
                  className="h-8 max-w-md text-xs"
                  value={step}
                  onChange={(e) => setSteps(steps.map((s, j) => (j === i ? e.target.value : s)))}
                >
                  <option value={step}>{step}</option>
                  {(actions.data?.actions || []).map((a) => (
                    <option key={a.action} value={a.action}>{a.action}（{a.count}）</option>
                  ))}
                </Select>
                {steps.length > 1 && (
                  <Button variant="ghost" className="h-8 px-2 text-xs text-destructive"
                    onClick={() => setSteps(steps.filter((_, j) => j !== i))}>×</Button>
                )}
              </div>
            ))}
            <div className="flex gap-2">
              <Button variant="secondary" className="h-8 text-xs"
                onClick={() => setSteps([...steps, topActions[0]?.action || ""])} disabled={!topActions.length}>
                添加步骤
              </Button>
              <Button className="h-8 text-xs" disabled={busy || steps.some((s) => !s)} onClick={run}>
                {busy ? "计算中…" : "计算漏斗"}
              </Button>
            </div>
          </CardContent>
        </Card>

        {result && (
          <Card>
            <CardHeader>
              <CardTitle>转化结果</CardTitle>
              <p className="text-xs text-muted-foreground">{result.note} · 样本 {result.sample_size} 条</p>
            </CardHeader>
            <CardContent>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={result.steps}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border, #e5e7eb)" />
                    <XAxis dataKey="step" tick={{ fontSize: 10 }} interval={0} angle={-15} height={50} textAnchor="end" />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="actors" name="去重操作者" fill="var(--color-primary, #6366f1)" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <table className="mt-3 w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-muted-foreground">
                    <th className="py-2 font-medium">步骤</th>
                    <th className="py-2 font-medium">去重操作者</th>
                    <th className="py-2 font-medium">首步转化</th>
                  </tr>
                </thead>
                <tbody>
                  {result.steps.map((s) => (
                    <tr key={s.step} className="border-b border-border/50 last:border-0">
                      <td className="py-2 text-xs font-medium">{s.step}</td>
                      <td className="py-2">{s.actors}</td>
                      <td className="py-2 text-muted-foreground">{(s.conversion_from_first * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}
      </PermissionGate>
    </div>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
      {children}
    </span>
  );
}
