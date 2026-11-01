/** 图类资产（子图/场景）共享页面骨架：列表 → 详情（锁横幅 + 画布编辑 + 版本历史）→ 生命周期。
 *
 * 子图与场景的差异仅在：调色板内容（场景额外引入已发布子图）、图节点字段
 * （kind）、场景的 saga 开关与执行面板。生命周期/锁/版本语义完全共用。
 */
import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import {
  AssetLockBanner,
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
  Textarea,
  useAssetLock,
  useScope,
  useToast,
} from "@opchub/console-ui";
import { AssetVersions } from "./AssetVersions";
import { GraphEditor, type EditorGraph, type PaletteItem } from "./GraphEditor";
import { catalogWrite, type AssetKind, type CatalogAsset } from "./catalog";

type LockState = {
  entity_type: string;
  entity_key: string;
  holder_id: string;
  holder_name?: string;
  expires_at?: string;
} | null;

const LIST_SCENARIO = { subgraph: "orchestration.catalog.subgraphs", scenario: "orchestration.catalog.scenarios" };
const DETAIL_SCENARIO = { subgraph: "orchestration.catalog.subgraph", scenario: "orchestration.catalog.scenario" };
const KIND_LABEL = { subgraph: "子图", scenario: "场景" };

function emptyGraph(): EditorGraph {
  return { entry_node: "", exit_node: "", nodes: [], edges: [] };
}

export function GraphAssetPage({ assetKind }: { assetKind: "subgraph" | "scenario" }) {
  const { hasPermission, myScope } = useScope();
  const { toast } = useToast();
  const qc = useQueryClient();
  const canWrite = hasPermission("orchestration:write");
  const myUserId = myScope?.user_id;

  const list = useQuery({
    queryKey: ["catalog", assetKind],
    queryFn: () =>
      dispatch<{ [k: string]: CatalogAsset[] | number }>(LIST_SCENARIO[assetKind], { page: 1, page_size: 200 }),
  });
  const rows = ((list.data as Record<string, unknown>)?.[assetKind === "subgraph" ? "subgraphs" : "scenarios"] ||
    []) as CatalogAsset[];

  const [selected, setSelected] = useState("");
  const [creating, setCreating] = useState(false);

  const detail = useQuery({
    queryKey: ["catalog", assetKind, selected],
    queryFn: () => dispatch<CatalogAsset>(DETAIL_SCENARIO[assetKind], { code: selected }),
    enabled: Boolean(selected),
  });

  const lock = useAssetLock(assetKind, { myUserId });
  const detailAsset = detail.data;
  const isManaged = Boolean(detailAsset && detailAsset.source === "managed");

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["catalog"] });
  };

  const runWithLock = async (action: string, payload: Record<string, unknown>) => {
    await lock.acquire(selected);
    try {
      await catalogWrite(action, payload);
      toast({ title: "操作成功", tone: "success" });
    } finally {
      await lock.release();
    }
  };

  const remove = async () => {
    if (!selected) return;
    if (!window.confirm(`删除${KIND_LABEL[assetKind]}「${selected}」？场景将连同其运行时配置版本一起移除。`)) return;
    try {
      await runWithLock(`${assetKind}s.delete`, { code: selected });
      setSelected("");
      refresh();
    } catch (err) {
      toast({ title: "删除失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
    }
  };

  return (
    <div>
      <PageHeader
        title={assetKind === "subgraph" ? "子图目录" : "场景目录"}
        description={
          assetKind === "subgraph"
            ? "把已发布算子编排成可复用子流水线；发布时编译为算子级扁平图"
            : "算子与子图混合编排；发布时内联展开并物化为执行 DAG"
        }
        actions={
          <PermissionGate permission="orchestration:write">
            <Button className="h-8 text-xs" onClick={() => setCreating(true)}>
              新建{KIND_LABEL[assetKind]}
            </Button>
          </PermissionGate>
        }
      />

      <Card className="mb-4">
        {list.isPending ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : !rows.length ? (
          <div className="p-5"><EmptyState title={`暂无${KIND_LABEL[assetKind]}`} hint="创建后进入草稿态，画布编排并发布。" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-5 py-3 font-medium">编码</th>
                <th className="px-5 py-3 font-medium">当前版本</th>
                <th className="px-5 py-3 font-medium">状态</th>
                <th className="px-5 py-3 font-medium">版本数</th>
                <th className="px-5 py-3 font-medium">锁定</th>
                <th className="px-5 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.code} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                  <td className="px-5 py-3">
                    <div className="font-medium">{row.display_name || row.code}</div>
                    <div className="text-xs text-muted-foreground">{row.code}</div>
                  </td>
                  <td className="px-5 py-3 text-muted-foreground">{row.current_version || "—"}</td>
                  <td className="px-5 py-3">
                    {row.source === "runtime" ? (
                      <Badge>运行时内置</Badge>
                    ) : (
                      <Badge tone="primary">管理中</Badge>
                    )}
                  </td>
                  <td className="px-5 py-3 text-muted-foreground">{row.versions?.length ?? 0}</td>
                  <td className="px-5 py-3">
                    <span className="text-xs text-muted-foreground">
                      {row.lock_status?.holder_name ? `被 ${row.lock_status.holder_name} 锁定` : "空闲"}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <Button
                      variant="secondary"
                      className="h-7 text-xs"
                      onClick={() => {
                        if (row.source === "runtime") {
                          toast({ title: "运行时内置管线为只读展示", description: "如需管理请先创建管理版本。", tone: "warning" });
                          return;
                        }
                        setSelected(row.code!);
                      }}
                    >
                      详情
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {selected && detailAsset && (
        <GraphAssetDetail
          assetKind={assetKind}
          asset={detailAsset}
          isManaged={isManaged}
          canWrite={canWrite}
          lock={lock}
          runWithLock={runWithLock}
          paletteSource={rows.filter((r) => r.code !== selected)}
          onRemove={remove}
          onChanged={refresh}
          onClose={() => {
            lock.release();
            setSelected("");
          }}
        />
      )}
      {selected && detail.isFetching && !detailAsset && (
        <Card><CardContent className="flex justify-center py-10"><Spinner /></CardContent></Card>
      )}

      <CreateGraphAssetModal
        open={creating}
        assetKind={assetKind}
        onClose={() => setCreating(false)}
        onCreated={(code) => {
          setCreating(false);
          setSelected(code);
          refresh();
        }}
      />
    </div>
  );
}

function GraphAssetDetail({
  assetKind,
  asset,
  isManaged,
  canWrite,
  lock,
  runWithLock,
  paletteSource,
  onRemove,
  onChanged,
  onClose,
}: {
  assetKind: AssetKind;
  asset: CatalogAsset;
  isManaged: boolean;
  canWrite: boolean;
  lock: ReturnType<typeof useAssetLock>;
  runWithLock: (action: string, payload: Record<string, unknown>) => Promise<void>;
  paletteSource: CatalogAsset[];
  onRemove: () => void;
  onChanged: () => void;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const { hasPermission } = useScope();
  const code = asset.code!;
  const versions = asset.versions || [];

  const [displayName, setDisplayName] = useState(asset.display_name || code);
  const [description, setDescription] = useState(asset.description || "");
  const [changelog, setChangelog] = useState("");
  const [graph, setGraph] = useState<EditorGraph>(() => {
    const draft = [...versions].reverse().find((v) => v.status === "DRAFT");
    return draft?.graph ? { ...draft.graph } : emptyGraph();
  });
  const [saga, setSaga] = useState(
    () => [...versions].reverse().find((v) => v.status === "DRAFT")?.graph?.enable_saga_compensation ?? true,
  );
  const [saving, setSaving] = useState(false);

  const editable = isManaged && canWrite && lock.heldByMe;

  const operatorsQuery = useQuery({
    queryKey: ["catalog-operators-palette"],
    queryFn: () => dispatch<{ operators: CatalogAsset[] }>("orchestration.catalog.operators", { page: 1, page_size: 200 }),
  });

  const palette: PaletteItem[] = useMemo(() => {
    const items: PaletteItem[] = (operatorsQuery.data?.operators || [])
      .filter((op) => op.source === "builtin" || op.current_version)
      .map((op) => ({
        kind: "OPERATOR" as const,
        key: op.name!,
        label: op.display_name || op.name!,
        domain: op.domain,
        description: op.description,
      }));
    if (assetKind === "scenario") {
      for (const row of paletteSource) {
        if (row.current_version) {
          items.push({ kind: "SUBGRAPH", key: row.code!, label: row.display_name || row.code!, description: row.description });
        }
      }
    }
    return items;
  }, [operatorsQuery.data, assetKind, paletteSource]);

  const saveDraft = async () => {
    if (!graph.nodes.length) {
      toast({ title: "画布至少需要一个节点", tone: "warning" });
      return;
    }
    setSaving(true);
    try {
      const nodes = graph.nodes.map((n) => {
        const base: Record<string, unknown> = { id: n.id, type: n.type, timeout_ms: n.timeout_ms ?? 3000 };
        if (assetKind === "scenario") base.kind = n.kind || "OPERATOR";
        if (n.kind === "SUBGRAPH") base.subgraph = n.subgraph;
        else base.operator = n.operator;
        return base;
      });
      await catalogWrite(`${assetKind}s.version.save`, {
        code,
        display_name: displayName,
        description,
        changelog: changelog || undefined,
        graph: {
          entry_node: graph.entry_node,
          exit_node: graph.exit_node,
          nodes,
          edges: graph.edges,
          ...(assetKind === "scenario" ? { enable_saga_compensation: saga } : {}),
        },
      });
      toast({ title: "草稿已保存", tone: "success" });
      setChangelog("");
      onChanged();
    } catch (err) {
      toast({ title: "保存失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">{asset.display_name || code}</CardTitle>
            <div className="flex items-center gap-2">
              {isManaged && canWrite && (
                <Button variant="destructive" className="h-7 text-xs" onClick={onRemove}>
                  删除
                </Button>
              )}
              <Button variant="secondary" className="h-7 text-xs" onClick={onClose}>
                收起
              </Button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            {code}
            {asset.description ? ` · ${asset.description}` : ""}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {isManaged ? (
            <>
              <AssetLockBanner
                assetLabel={code}
                heldByMe={lock.heldByMe}
                heldByOther={lock.heldByOther}
                holderLabel={lock.holderLabel}
                remainingSeconds={lock.remainingSeconds}
                busy={lock.busy}
                onAcquire={() =>
                  lock.acquire(code).catch((err: Error) =>
                    toast({ title: "获取编辑锁失败", description: err.message, tone: "destructive" }),
                  )
                }
                onRelease={() => lock.release()}
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label="显示名">
                  <Input value={displayName} disabled={!editable} onChange={(e) => setDisplayName(e.target.value)} />
                </Field>
                <Field label="描述">
                  <Input value={description} disabled={!editable} onChange={(e) => setDescription(e.target.value)} />
                </Field>
              </div>
              <GraphEditor
                graph={graph}
                editable={editable}
                allowSubgraphs={assetKind === "scenario"}
                palette={palette}
                onChange={setGraph}
              />
              {assetKind === "scenario" && (
                <label className="flex items-center gap-2 text-sm text-muted-foreground">
                  <input type="checkbox" checked={saga} disabled={!editable} onChange={(e) => setSaga(e.target.checked)} />
                  启用 Saga 补偿（节点失败时按逆序触发补偿语义）
                </label>
              )}
              <div className="flex items-end gap-3">
                <Field label="变更说明" className="flex-1">
                  <Textarea
                    rows={2}
                    value={changelog}
                    disabled={!editable}
                    onChange={(e) => setChangelog(e.target.value)}
                    placeholder="留空则沿用默认说明"
                  />
                </Field>
                <Button disabled={!editable || saving} onClick={saveDraft}>
                  {saving ? "保存中…" : "保存草稿"}
                </Button>
              </div>
            </>
          ) : (
            <div className="text-sm text-muted-foreground">
              运行时内置管线为只读展示；如需纳管，请创建同名管理版本。
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>版本历史</CardTitle></CardHeader>
        <CardContent>
          <AssetVersions
            assetKind={assetKind}
            assetCode={code}
            versions={versions}
            currentVersion={asset.current_version}
            canWrite={isManaged && canWrite}
            runWithLock={runWithLock}
            onChanged={onChanged}
          />
        </CardContent>
      </Card>

      {assetKind === "scenario" && <ExecutePanel scenarioCode={code} />}
    </div>
  );
}

/** 场景执行面板（平台管理员视角：执行入口保持 page:orchestrate 把守）。 */
interface ExecuteResult {
  status: string;
  node_traces: Array<{ node_id: string; action_handler: string; status: string; duration_ms: number; error?: string }>;
  final_output: Record<string, unknown>;
  error_message?: string;
}

function ExecutePanel({ scenarioCode }: { scenarioCode: string }) {
  const { hasPermission } = useScope();
  const { toast } = useToast();
  const canExecute = hasPermission("page:orchestrate");
  const [inputs, setInputs] = useState("{}");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<ExecuteResult | null>(null);

  const inputsError = useMemo(() => {
    try {
      const parsed = JSON.parse(inputs);
      if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) return "入参必须为 JSON 对象";
      return "";
    } catch (e) {
      return `JSON 格式错误：${(e as Error).message}`;
    }
  }, [inputs]);

  if (!canExecute) {
    return (
      <Card>
        <CardHeader><CardTitle>执行调试</CardTitle></CardHeader>
        <CardContent>
          <div className="text-sm text-muted-foreground">
            场景执行入口由平台管理员把守（page:orchestrate）；项目成员的变更经发布审批进入运行时。
          </div>
        </CardContent>
      </Card>
    );
  }

  const run = async () => {
    setRunning(true);
    setResult(null);
    try {
      const res = await dispatch<ExecuteResult>("orchestration.scenarios.execute", {
        scenario_code: scenarioCode,
        inputs: JSON.parse(inputs),
      });
      setResult(res);
      if (res.status === "SUCCESS") toast({ title: "执行成功", tone: "success" });
      else toast({ title: `执行结束：${res.status}`, description: res.error_message, tone: "warning" });
    } catch (err) {
      toast({ title: "执行失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
    } finally {
      setRunning(false);
    }
  };

  return (
    <Card>
      <CardHeader><CardTitle>执行调试</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <Field label="入参 JSON" hint={inputsError || "必须是 JSON 对象，键值将作为场景入参"}>
          <Textarea rows={4} className="font-mono text-xs" value={inputs} onChange={(e) => setInputs(e.target.value)} />
        </Field>
        <Button disabled={running || Boolean(inputsError)} onClick={run}>
          {running ? "执行中…" : "执行场景"}
        </Button>
        {result && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Badge tone={result.status === "SUCCESS" ? "success" : "warning"}>{result.status}</Badge>
              {result.error_message && <span className="text-xs text-destructive">{result.error_message}</span>}
            </div>
            {result.node_traces?.length > 0 && (
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
                  {result.node_traces.map((t) => (
                    <tr key={t.node_id} className="border-b border-border/50 last:border-0">
                      <td className="py-1.5 font-medium">{t.node_id}</td>
                      <td className="py-1.5 text-muted-foreground">{t.action_handler}</td>
                      <td className="py-1.5">{t.status}</td>
                      <td className="py-1.5 text-muted-foreground">{t.duration_ms}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div>
              <div className="mb-1 text-xs font-medium text-muted-foreground">最终输出</div>
              <Textarea readOnly rows={6} className="font-mono text-xs" value={JSON.stringify(result.final_output ?? {}, null, 2)} />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CreateGraphAssetModal({
  open,
  assetKind,
  onClose,
  onCreated,
}: {
  open: boolean;
  assetKind: "subgraph" | "scenario";
  onClose: () => void;
  onCreated: (code: string) => void;
}) {
  const { toast } = useToast();
  const [form, setForm] = useState({ code: "", display_name: "", description: "" });
  const [busy, setBusy] = useState(false);

  const create = async () => {
    setBusy(true);
    try {
      await catalogWrite(`${assetKind}s.create`, { ...form });
      toast({ title: `${KIND_LABEL[assetKind]}已创建（草稿）`, description: "画布编排后保存草稿并发布。", tone: "success" });
      onCreated(form.code);
      setForm({ code: "", display_name: "", description: "" });
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
      title={`新建${KIND_LABEL[assetKind]}`}
      description="创建后处于草稿态，画布编排、保存草稿并发布（或提交发布审批）"
      footer={
        <ModalActions onCancel={onClose} busy={busy}>
          <Button disabled={busy || !form.code} onClick={create}>
            {busy ? "创建中…" : "创建"}
          </Button>
        </ModalActions>
      }
    >
      <div className="grid gap-3">
        <Field label="编码" hint="字母开头，仅字母/数字/下划线/点号/横线，长度 2-64">
          <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="MY_FLOW" />
        </Field>
        <Field label="显示名">
          <Input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
        </Field>
        <Field label="描述">
          <Textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
      </div>
    </Modal>
  );
}
