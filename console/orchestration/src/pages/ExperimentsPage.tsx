/** 实验管理（A/B）：创建（变体+权重+流量）→ 状态机（启动/停止/归档）→ 分流试算 → 读出。
 *
 * 分流/上报走 OPC_EXPERIMENT_PIPELINE（{action,payload} 信封）；读直连。
 * 模型借鉴 GrowthBook，代码自研。
 */
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
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
  Modal,
  ModalActions,
  PageHeader,
  PermissionGate,
  Spinner,
  useScope,
  useToast,
} from "@opchub/console-ui";

const statusTone: Record<string, "neutral" | "success" | "warning" | "destructive" | "primary"> = {
  DRAFT: "warning",
  RUNNING: "success",
  STOPPED: "neutral",
  ARCHIVED: "neutral",
};

interface Variant {
  key: string;
  name?: string;
  weight: number;
}

interface Experiment {
  key: string;
  name: string;
  description: string;
  status: string;
  variants: Variant[];
  traffic_percent: number;
}

interface Readout {
  total_assignments: number;
  variants: Array<{
    variant: string;
    name: string;
    assignments: number;
    metrics: Record<string, { count: number; sum: number; avg?: number }>;
  }>;
}

export function ExperimentsPage() {
  const { hasPermission } = useScope();
  const { toast } = useToast();
  const qc = useQueryClient();
  const canManage = hasPermission("experiment:manage");

  const list = useQuery({
    queryKey: ["experiments"],
    queryFn: () => dispatch<{ experiments: Experiment[]; total: number }>("experiment.list", {}),
  });
  const [selected, setSelected] = useState("");
  const [creating, setCreating] = useState(false);

  const detail = useQuery({
    queryKey: ["experiment", selected],
    queryFn: () => dispatch<Experiment>("experiment.detail", { experiment_key: selected }),
    enabled: Boolean(selected),
  });
  const readout = useQuery({
    queryKey: ["experiment-readout", selected],
    queryFn: () => dispatch<Readout>("experiment.readout", { experiment_key: selected }),
    enabled: Boolean(selected),
  });

  const setStatus = async (key: string, status: string) => {
    try {
      await dispatch(`experiment.status`, { action: "experiments.status", payload: { experiment_key: key, status } });
      toast({ title: `实验已${status === "RUNNING" ? "启动" : status === "STOPPED" ? "停止" : "归档"}`, tone: "success" });
      qc.invalidateQueries({ queryKey: ["experiments"] });
      qc.invalidateQueries({ queryKey: ["experiment"] });
      qc.invalidateQueries({ queryKey: ["experiment-readout"] });
    } catch (err) {
      toast({ title: "状态变更失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
    }
  };

  const rows = list.data?.experiments || [];

  return (
    <div>
      <PageHeader
        title="实验管理"
        description="A/B 实验：确定性分桶 × 流量门控，粘性分配与真实结果读出"
        actions={
          <PermissionGate permission="experiment:manage">
            <Button className="h-8 text-xs" onClick={() => setCreating(true)}>
              新建实验
            </Button>
          </PermissionGate>
        }
      />

      <Card className="mb-4">
        {list.isPending ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : !rows.length ? (
          <div className="p-5">
            <EmptyState title="暂无实验" hint="创建实验后配置变体与流量，启动即对宿主客户端生效。" />
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-5 py-3 font-medium">实验</th>
                <th className="px-5 py-3 font-medium">状态</th>
                <th className="px-5 py-3 font-medium">流量</th>
                <th className="px-5 py-3 font-medium">变体</th>
                <th className="px-5 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.key} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                  <td className="px-5 py-3">
                    <div className="font-medium">{e.name}</div>
                    <div className="text-xs text-muted-foreground">{e.key}{e.description ? ` · ${e.description}` : ""}</div>
                  </td>
                  <td className="px-5 py-3"><Badge tone={statusTone[e.status] || "neutral"}>{e.status}</Badge></td>
                  <td className="px-5 py-3 text-muted-foreground">{e.traffic_percent}%</td>
                  <td className="px-5 py-3 text-muted-foreground">
                    {e.variants.map((v) => `${v.key}(${v.weight})`).join(" / ")}
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex gap-2">
                      <Button variant="secondary" className="h-7 text-xs" onClick={() => setSelected(e.key)}>
                        详情
                      </Button>
                      <PermissionGate permission="experiment:manage">
                        {e.status === "DRAFT" && (
                          <Button className="h-7 text-xs" onClick={() => setStatus(e.key, "RUNNING")}>
                            启动
                          </Button>
                        )}
                        {e.status === "RUNNING" && (
                          <Button variant="secondary" className="h-7 text-xs" onClick={() => setStatus(e.key, "STOPPED")}>
                            停止
                          </Button>
                        )}
                        {e.status === "STOPPED" && (
                          <>
                            <Button className="h-7 text-xs" onClick={() => setStatus(e.key, "RUNNING")}>
                              恢复
                            </Button>
                            <Button variant="secondary" className="h-7 text-xs" onClick={() => setStatus(e.key, "ARCHIVED")}>
                              归档
                            </Button>
                          </>
                        )}
                      </PermissionGate>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {selected && detail.data && (
        <ExperimentDetail
          experiment={detail.data}
          readout={readout.data}
          canManage={canManage}
          onChanged={() => {
            qc.invalidateQueries({ queryKey: ["experiments"] });
            qc.invalidateQueries({ queryKey: ["experiment"] });
            qc.invalidateQueries({ queryKey: ["experiment-readout"] });
          }}
          onClose={() => setSelected("")}
        />
      )}

      <CreateExperimentModal
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={(key) => {
          setCreating(false);
          setSelected(key);
          qc.invalidateQueries({ queryKey: ["experiments"] });
        }}
      />
    </div>
  );
}

function ExperimentDetail({
  experiment,
  readout,
  canManage,
  onChanged,
  onClose,
}: {
  experiment: Experiment;
  readout?: Readout;
  canManage: boolean;
  onChanged: () => void;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const [tryUid, setTryUid] = useState("");
  const [tryResult, setTryResult] = useState<{ variant: string; in_experiment: boolean; reason?: string } | null>(null);
  const [weights, setWeights] = useState<Record<string, number>>(
    () => Object.fromEntries(experiment.variants.map((v) => [v.key, v.weight])),
  );
  const [traffic, setTraffic] = useState(experiment.traffic_percent);
  const [saving, setSaving] = useState(false);

  const totalWeight = experiment.variants.reduce((s, v) => s + (weights[v.key] ?? v.weight), 0) || 1;

  const saveTuning = async () => {
    setSaving(true);
    try {
      await dispatch("experiment.update", {
        action: "experiments.update",
        payload: {
          experiment_key: experiment.key,
          traffic_percent: traffic,
          variants: experiment.variants.map((v) => ({ ...v, weight: weights[v.key] ?? v.weight })),
        },
      });
      toast({ title: "变体权重与流量已更新", tone: "success" });
      onChanged();
    } catch (err) {
      toast({ title: "更新失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const tryAssign = async () => {
    try {
      const res = await dispatch<{ variant: string; in_experiment: boolean; reason?: string }>(
        "experiment.assign",
        { experiment_key: experiment.key, user_id: tryUid },
      );
      setTryResult(res);
    } catch (err) {
      toast({ title: "试算失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">{experiment.name}</CardTitle>
            <div className="flex items-center gap-2">
              <Badge tone={statusTone[experiment.status] || "neutral"}>{experiment.status}</Badge>
              <Button variant="secondary" className="h-7 text-xs" onClick={onClose}>收起</Button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            {experiment.key}{experiment.description ? ` · ${experiment.description}` : ""}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <PermissionGate permission="experiment:manage">
            <div className="space-y-2 rounded-md border border-border p-3">
              <div className="text-xs font-medium text-muted-foreground">
                变体权重与流量{experiment.status === "RUNNING" ? "（运行中可调）" : ""}
              </div>
              {experiment.variants.map((v) => (
                <div key={v.key} className="flex items-center gap-3">
                  <Badge tone="primary">{v.key}</Badge>
                  <Input
                    type="number"
                    min={0}
                    step="0.1"
                    className="h-8 w-28 text-xs"
                    value={weights[v.key] ?? v.weight}
                    onChange={(e) => setWeights({ ...weights, [v.key]: Number(e.target.value) })}
                  />
                  <span className="text-xs text-muted-foreground">
                    归一化 {Math.round(((weights[v.key] ?? v.weight) / totalWeight) * 100)}%
                  </span>
                </div>
              ))}
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground">流量门控</span>
                <Input
                  type="number"
                  min={0}
                  max={100}
                  className="h-8 w-24 text-xs"
                  value={traffic}
                  onChange={(e) => setTraffic(Number(e.target.value))}
                />
                <span className="text-xs text-muted-foreground">%</span>
                <Button className="h-8 text-xs" disabled={saving} onClick={saveTuning}>
                  {saving ? "保存中…" : "保存调优"}
                </Button>
              </div>
            </div>
          </PermissionGate>

          <div className="space-y-2 rounded-md border border-border p-3">
            <div className="text-xs font-medium text-muted-foreground">分流试算（sha256 稳定分桶，真实调用分配接口）</div>
            <div className="flex items-center gap-2">
              <Input
                className="h-8 max-w-xs text-xs"
                placeholder="用户 uid"
                value={tryUid}
                onChange={(e) => setTryUid(e.target.value)}
              />
              <Button variant="secondary" className="h-8 text-xs" disabled={!tryUid} onClick={tryAssign}>
                试算
              </Button>
              {tryResult && (
                <span className="text-xs">
                  {tryResult.in_experiment ? (
                    <>命中变体 <Badge tone="primary">{tryResult.variant}</Badge></>
                  ) : (
                    <span className="text-muted-foreground">未入实验（{tryResult.reason || "TRAFFIC"}）</span>
                  )}
                </span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>读出</CardTitle>
          <p className="text-xs text-muted-foreground">
            累计分配 {readout?.total_assignments ?? 0} 人；结果指标由宿主客户端经 outcome.report 上报
          </p>
        </CardHeader>
        <CardContent>
          {!readout || !readout.variants.length ? (
            <EmptyState title="尚无分配记录" hint="实验启动后，宿主客户端的分流调用会在此聚合。" />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="py-2 font-medium">变体</th>
                  <th className="py-2 font-medium">分配数</th>
                  <th className="py-2 font-medium">占比</th>
                  <th className="py-2 font-medium">结果指标</th>
                </tr>
              </thead>
              <tbody>
                {readout.variants.map((v) => (
                  <tr key={v.variant} className="border-b border-border/50 last:border-0">
                    <td className="py-2 font-medium">{v.variant}</td>
                    <td className="py-2">{v.assignments}</td>
                    <td className="py-2 text-muted-foreground">
                      {readout.total_assignments ? Math.round((v.assignments / readout.total_assignments) * 100) : 0}%
                    </td>
                    <td className="py-2 text-xs text-muted-foreground">
                      {Object.entries(v.metrics).length
                        ? Object.entries(v.metrics)
                            .map(([m, s]) => `${m}: n=${s.count} avg=${s.avg ?? 0}`)
                            .join(" · ")
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function CreateExperimentModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (key: string) => void;
}) {
  const { toast } = useToast();
  const { activeEnvironments } = useScope();
  const [form, setForm] = useState({ key: "", name: "", description: "", traffic_percent: 100, env_key: "" });
  const [variants, setVariants] = useState<Variant[]>([
    { key: "control", name: "对照组", weight: 1 },
    { key: "treatment", name: "实验组", weight: 1 },
  ]);
  const [busy, setBusy] = useState(false);

  const create = async () => {
    setBusy(true);
    try {
      await dispatch("experiment.create", {
        action: "experiments.create",
        payload: { ...form, variants },
      });
      toast({ title: "实验已创建（草稿）", description: "启动后对宿主客户端生效", tone: "success" });
      onCreated(form.key);
    } catch (err) {
      toast({ title: "创建失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="新建实验"
      description="草稿态不参与分流；启动（RUNNING）后按流量门控对宿主客户端生效"
      footer={
        <ModalActions onCancel={onClose} busy={busy}>
          <Button disabled={busy || !form.key || variants.length < 1} onClick={create}>
            {busy ? "创建中…" : "创建"}
          </Button>
        </ModalActions>
      }
    >
      <div className="grid gap-3">
        <Field label="实验标识" hint="2-48 位小写字母/数字/下划线/横线，字母开头">
          <Input value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} placeholder="cta_color" />
        </Field>
        <Field label="名称">
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="描述">
          <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <div>
          <div className="mb-1.5 text-xs font-medium text-muted-foreground">变体（权重为相对值）</div>
          <div className="space-y-2">
            {variants.map((v, i) => (
              <div key={i} className="flex items-center gap-2">
                <Input
                  className="h-8 w-32 text-xs"
                  placeholder="变体键"
                  value={v.key}
                  onChange={(e) => setVariants(variants.map((x, j) => (j === i ? { ...x, key: e.target.value } : x)))}
                />
                <Input
                  className="h-8 w-32 text-xs"
                  placeholder="名称"
                  value={v.name}
                  onChange={(e) => setVariants(variants.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))}
                />
                <Input
                  type="number"
                  className="h-8 w-24 text-xs"
                  placeholder="权重"
                  value={v.weight}
                  onChange={(e) => setVariants(variants.map((x, j) => (j === i ? { ...x, weight: Number(e.target.value) } : x)))}
                />
                {variants.length > 1 && (
                  <Button variant="ghost" className="h-8 px-2 text-xs text-destructive"
                    onClick={() => setVariants(variants.filter((_, j) => j !== i))}>
                    ×
                  </Button>
                )}
              </div>
            ))}
          </div>
          <Button variant="secondary" className="mt-2 h-7 text-xs"
            onClick={() => setVariants([...variants, { key: `variant_${variants.length + 1}`, name: "", weight: 1 }])}>
            添加变体
          </Button>
        </div>
        <Field label="流量门控（%）" hint="命中桶 %100 < 流量百分比的用户进入实验">
          <Input type="number" min={0} max={100} value={form.traffic_percent}
            onChange={(e) => setForm({ ...form, traffic_percent: Number(e.target.value) })} />
        </Field>
        <Field label="生效环境" hint="留空 = 全环境生效；指定环境后宿主仅在匹配环境分流">
          <select
            aria-label="选择生效环境"
            className="h-9 rounded-md border border-input bg-card px-2.5 text-sm"
            value={form.env_key}
            onChange={(e) => setForm({ ...form, env_key: e.target.value })}
          >
            <option value="">全环境</option>
            {activeEnvironments.map((env) => (
              <option key={env.key} value={env.key}>{env.name}{env.protected ? " 🔒" : ""}</option>
            ))}
          </select>
        </Field>
      </div>
    </Modal>
  );
}
