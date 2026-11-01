/** 调试工作台：选择场景 → 入参 JSON → 执行 → 结果与节点迹（平台管理员视角）。 */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import {
  Badge, Button, Card, CardContent, CardHeader, CardTitle, EmptyState, Field,
  PageHeader, PermissionGate, Select, Spinner, Textarea, useToast,
} from "@opchub/console-ui";

interface ExecuteResult {
  status: string;
  execution_time_ms: number;
  node_traces: Array<{ node_id: string; action_handler: string; status: string; duration_ms: number; error?: string }>;
  final_output: Record<string, unknown>;
  error_message?: string;
}

export function DebugPage() {
  const { toast } = useToast();
  const flows = useQuery({
    queryKey: ["ops", "dag-list"],
    queryFn: () => dispatch<{ configs: Array<{ scenario_code: string; version: string; status: string }> }>("orchestration.dag.list", {}),
  });
  const [scenario, setScenario] = useState("");
  const [inputs, setInputs] = useState("{}");
  const [result, setResult] = useState<ExecuteResult | null>(null);
  const [running, setRunning] = useState(false);

  const options = (flows.data?.configs || []).filter((cfg) => cfg.status === "ACTIVE");
  const codes = Array.from(new Set(options.map((c) => c.scenario_code)));

  const inputsError = useMemo(() => {
    try {
      const parsed = JSON.parse(inputs);
      if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) return "入参必须为 JSON 对象";
      return "";
    } catch (e) {
      return `JSON 格式错误：${(e as Error).message}`;
    }
  }, [inputs]);

  const run = async () => {
    setRunning(true);
    setResult(null);
    try {
      const res = await dispatch<ExecuteResult>("orchestration.scenarios.execute", {
        scenario_code: scenario, inputs: JSON.parse(inputs),
      });
      setResult(res);
      toast({ title: `执行结束：${res.status}`, tone: res.status === "SUCCESS" ? "success" : "warning" });
    } catch (err) {
      toast({ title: "执行失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <PageHeader title="调试工作台" description="执行任一运行时场景并检视节点迹与输出（page:orchestrate 把守）" />
      <PermissionGate
        permission="page:orchestrate"
        fallback={<Card className="p-6 text-sm text-muted-foreground">场景执行入口由平台管理员把守（page:orchestrate）。</Card>}
      >
        <Card className="mb-4">
          <CardHeader><CardTitle>执行</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {flows.isPending ? (
              <div className="flex justify-center py-8"><Spinner /></div>
            ) : !codes.length ? (
              <EmptyState title="暂无 ACTIVE 运行时场景" />
            ) : (
              <>
                <Field label="场景">
                  <Select value={scenario} onChange={(e) => setScenario(e.target.value)}>
                    <option value="">选择场景</option>
                    {codes.map((c) => <option key={c} value={c}>{c}</option>)}
                  </Select>
                </Field>
                <Field label="入参 JSON" hint={inputsError || "必须是 JSON 对象"}>
                  <Textarea rows={5} className="font-mono text-xs" value={inputs} onChange={(e) => setInputs(e.target.value)} />
                </Field>
                <Button disabled={running || !scenario || Boolean(inputsError)} onClick={run}>
                  {running ? "执行中…" : "执行场景"}
                </Button>
              </>
            )}
          </CardContent>
        </Card>

        {result && (
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <CardTitle className="text-base">执行结果</CardTitle>
                <Badge tone={result.status === "SUCCESS" ? "success" : "destructive"}>{result.status}</Badge>
                <span className="text-xs text-muted-foreground">{result.execution_time_ms}ms</span>
                {result.error_message && <span className="text-xs text-destructive">{result.error_message}</span>}
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border text-left text-muted-foreground">
                    <th className="py-1.5 font-medium">节点</th>
                    <th className="py-1.5 font-medium">处理器</th>
                    <th className="py-1.5 font-medium">状态</th>
                    <th className="py-1.5 font-medium">耗时</th>
                  </tr>
                </thead>
                <tbody>
                  {(result.node_traces || []).map((t) => (
                    <tr key={t.node_id} className="border-b border-border/50 last:border-0">
                      <td className="py-1.5 font-medium">{t.node_id}</td>
                      <td className="py-1.5 text-muted-foreground">{t.action_handler}</td>
                      <td className="py-1.5">{t.status}</td>
                      <td className="py-1.5 text-muted-foreground">{t.duration_ms}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div>
                <div className="mb-1 text-xs font-medium text-muted-foreground">最终输出</div>
                <Textarea readOnly rows={8} className="font-mono text-xs"
                  value={JSON.stringify(result.final_output ?? {}, null, 2)} />
              </div>
            </CardContent>
          </Card>
        )}
      </PermissionGate>
    </div>
  );
}
