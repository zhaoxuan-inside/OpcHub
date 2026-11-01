/** 留存：操作者×日活跃矩阵（真实审计足迹）+ D1/D7 复访率。 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import {
  Badge, Card, CardContent, CardHeader, CardTitle, EmptyState, Field,
  PageHeader, PermissionGate, Select, Spinner,
} from "@opchub/console-ui";

interface Retention {
  days: string[];
  cohort_size: number;
  d1_rate: number;
  d7_rate: number;
  actors: Array<{ actor_id: string; first_day: string; active_days: number[]; d1: boolean; d7: boolean }>;
  sample_size: number;
  note: string;
}

export function RetentionPage() {
  const [days, setDays] = useState(14);
  const query = useQuery({
    queryKey: ["bizops", "retention", days],
    queryFn: () => dispatch<Retention>("bizops.retention", { days }),
  });
  const data = query.data;
  const activeSet = useMemoSet(data);

  return (
    <div>
      <PageHeader title="留存" description="操作者 × 日活跃矩阵（真实审计足迹判定活跃）" />
      <PermissionGate
        permission="page:bizops_console"
        fallback={<Card className="p-6 text-sm text-muted-foreground">需要运营平台入口权限（page:bizops_console）。</Card>}
      >
        <Card className="mb-4">
          <CardContent className="flex items-end gap-3 px-4 py-3">
            <Field label="窗口">
              <Select className="h-8 w-36 text-xs" value={days} onChange={(e) => setDays(Number(e.target.value))}>
                <option value={7}>最近 7 天</option>
                <option value={14}>最近 14 天</option>
              </Select>
            </Field>
          </CardContent>
        </Card>

        {query.isPending ? (
          <Card><CardContent className="flex justify-center py-16"><Spinner /></CardContent></Card>
        ) : !data || !data.cohort_size ? (
          <Card><div className="p-5"><EmptyState title="窗口内暂无操作者足迹" /></div></Card>
        ) : (
          <>
            <div className="mb-4 grid gap-4 sm:grid-cols-3">
              <Card>
                <CardHeader><CardTitle className="text-muted-foreground">Cohort（足迹操作者）</CardTitle></CardHeader>
                <CardContent><div className="text-3xl font-semibold tracking-tight">{data.cohort_size}</div></CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle className="text-muted-foreground">D1 复访率</CardTitle></CardHeader>
                <CardContent><div className="text-3xl font-semibold tracking-tight">{(data.d1_rate * 100).toFixed(1)}%</div></CardContent>
              </Card>
              <Card>
                <CardHeader><CardTitle className="text-muted-foreground">D7 复访率</CardTitle></CardHeader>
                <CardContent><div className="text-3xl font-semibold tracking-tight">{(data.d7_rate * 100).toFixed(1)}%</div></CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>活跃矩阵</CardTitle>
                <p className="text-xs text-muted-foreground">{data.note} · 样本 {data.sample_size} 条（明细截断 200）</p>
              </CardHeader>
              <CardContent className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-border text-left text-muted-foreground">
                      <th className="py-2 pr-3 font-medium">操作者</th>
                      {data.days.map((d) => (
                        <th key={d} className="py-2 px-1 font-medium">{d.slice(5)}</th>
                      ))}
                      <th className="py-2 font-medium">D1</th>
                      <th className="py-2 font-medium">D7</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.actors.map((a) => (
                      <tr key={a.actor_id} className="border-b border-border/50 last:border-0">
                        <td className="py-1.5 pr-3 font-medium">{a.actor_id}</td>
                        {data.days.map((d, i) => (
                          <td key={d} className="py-1.5 px-1">
                            <span
                              className={`inline-block size-3 rounded-sm ${activeSet.has(`${a.actor_id}:${i}`) ? "bg-primary/70" : "bg-muted"}`}
                              title={d}
                            />
                          </td>
                        ))}
                        <td className="py-1.5">{a.d1 ? <Badge tone="success">✓</Badge> : <span className="text-muted-foreground">—</span>}</td>
                        <td className="py-1.5">{a.d7 ? <Badge tone="success">✓</Badge> : <span className="text-muted-foreground">—</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          </>
        )}
      </PermissionGate>
    </div>
  );
}

function useMemoSet(data: Retention | undefined): Set<string> {
  // 活跃格子键集合（actor:dayIndex）
  const set = new Set<string>();
  for (const a of data?.actors || []) for (const i of a.active_days) set.add(`${a.actor_id}:${i}`);
  return set;
}
