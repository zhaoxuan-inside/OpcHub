/** 配置中心（Nacos 模式）：命名空间 → 配置项 → 版本历史 → 灰度发布（百分比分桶 + 白名单）。
 *
 * 写操作经 OPC_CONFIGCENTER_PIPELINE（{action,payload} 信封）；读/resolve 直连。
 */
import { useMemo, useState } from "react";
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
  Select,
  Spinner,
  Textarea,
  diffLines,
  useScope,
  useToast,
} from "@opchub/console-ui";

interface Namespace {
  key: string;
  name: string;
  description: string;
}
interface ConfigVersion {
  version: string;
  status: "DRAFT" | "PUBLISHED" | "SUPERSEDED";
  content: string;
  changelog: string;
  published_by?: string;
}
interface ConfigItem {
  namespace: string;
  key: string;
  name: string;
  value_type: string;
  description: string;
  versions: ConfigVersion[];
  stable_version: string;
  gray: { version: string; percent: number; whitelist: string[] } | null;
}

const write = (action: string, payload: Record<string, unknown>) =>
  dispatch(`configcenter.${action.split(".")[0] === "items" ? "items" : "namespaces"}.${action.split(".").slice(1).join(".")}`, {
    action,
    payload,
  });

export function ConfigsPage() {
  const { hasPermission } = useScope();
  const { toast } = useToast();
  const qc = useQueryClient();
  const canWrite = hasPermission("configcenter:write");

  const namespaces = useQuery({
    queryKey: ["config-namespaces"],
    queryFn: () => dispatch<{ namespaces: Namespace[] }>("configcenter.namespaces.list", {}),
  });
  const [activeNs, setActiveNs] = useState("");
  const items = useQuery({
    queryKey: ["config-items", activeNs],
    queryFn: () => dispatch<{ items: ConfigItem[] }>("configcenter.items.list", { namespace: activeNs || undefined }),
  });
  const [creatingNs, setCreatingNs] = useState(false);
  const [creatingItem, setCreatingItem] = useState(false);
  const [editingItem, setEditingItem] = useState<ConfigItem | null>(null);
  const [publishingItem, setPublishingItem] = useState<ConfigItem | null>(null);
  const [historyItem, setHistoryItem] = useState<ConfigItem | null>(null);

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["config-namespaces"] });
    qc.invalidateQueries({ queryKey: ["config-items"] });
  };

  const nsRows = namespaces.data?.namespaces || [];
  const itemRows = (items.data?.items || []).filter((i) => !activeNs || i.namespace === activeNs);

  return (
    <div>
      <PageHeader
        title="配置中心"
        description="命名空间 → 配置项 → 版本历史 → 灰度发布（百分比分桶 + 白名单直通）"
        actions={
          <PermissionGate permission="configcenter:write">
            <Button className="h-8 text-xs" onClick={() => setCreatingNs(true)}>新建命名空间</Button>
            <Button variant="secondary" className="h-8 text-xs" onClick={() => setCreatingItem(true)} disabled={!nsRows.length}>
              新建配置项
            </Button>
          </PermissionGate>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[240px_1fr]">
        <Card className="h-fit">
          <CardHeader><CardTitle>命名空间</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {namespaces.isPending ? (
              <div className="flex justify-center py-8"><Spinner /></div>
            ) : !nsRows.length ? (
              <EmptyState title="暂无命名空间" />
            ) : (
              nsRows.map((ns) => (
                <button
                  key={ns.key}
                  type="button"
                  className={`w-full rounded-md px-2.5 py-2 text-left text-sm transition-colors ${
                    activeNs === ns.key ? "bg-primary/10 font-medium text-primary" : "text-muted-foreground hover:bg-accent"
                  }`}
                  onClick={() => setActiveNs(activeNs === ns.key ? "" : ns.key)}
                >
                  <div className="font-medium">{ns.name}</div>
                  <div className="text-xs">{ns.key}</div>
                </button>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          {items.isPending ? (
            <div className="flex justify-center py-16"><Spinner /></div>
          ) : !itemRows.length ? (
            <div className="p-5"><EmptyState title="暂无配置项" hint="创建配置项并发布后，宿主运行时可经 resolve 解析生效值。" /></div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th className="px-4 py-3 font-medium">配置项</th>
                  <th className="px-4 py-3 font-medium">类型</th>
                  <th className="px-4 py-3 font-medium">稳定版</th>
                  <th className="px-4 py-3 font-medium">灰度态</th>
                  <th className="px-4 py-3 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {itemRows.map((item) => (
                  <tr key={`${item.namespace}:${item.key}`} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                    <td className="px-4 py-3">
                      <div className="font-medium">{item.name || item.key}</div>
                      <div className="text-xs text-muted-foreground">{item.namespace} / {item.key}</div>
                    </td>
                    <td className="px-4 py-3"><Badge>{item.value_type}</Badge></td>
                    <td className="px-4 py-3 text-muted-foreground">{item.stable_version || "—"}</td>
                    <td className="px-4 py-3">
                      {item.gray ? (
                        <Badge tone="warning">灰度 {item.gray.percent}% · {item.gray.version}</Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1.5">
                        <PermissionGate permission="configcenter:write">
                          <Button variant="secondary" className="h-7 text-xs"
                            onClick={() => setEditingItem(item)}>
                            编辑草稿
                          </Button>
                          <Button variant="secondary" className="h-7 text-xs"
                            onClick={() => setPublishingItem(item)}>
                            发布
                          </Button>
                        </PermissionGate>
                        <Button variant="ghost" className="h-7 text-xs" onClick={() => setHistoryItem(item)}>
                          历史
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>

      <CreateNamespaceModal open={creatingNs} onClose={() => setCreatingNs(false)} onCreated={(key) => { setCreatingNs(false); setActiveNs(key); refresh(); }} />
      <CreateItemModal
        open={creatingItem}
        namespaces={nsRows}
        defaultNamespace={activeNs}
        onClose={() => setCreatingItem(false)}
        onCreated={() => { setCreatingItem(false); refresh(); }}
      />
      {editingItem && (
        <EditDraftModal
          item={editingItem}
          onClose={() => { setEditingItem(null); refresh(); }}
        />
      )}
      {publishingItem && (
        <PublishModal
          item={publishingItem}
          canWrite={canWrite}
          onClose={() => { setPublishingItem(null); refresh(); }}
        />
      )}
      {historyItem && (
        <HistoryModal item={historyItem} canWrite={canWrite} onClose={() => { setHistoryItem(null); refresh(); }} />
      )}
      {canWrite && null}
    </div>
  );
}

function useValidateJson(valueType: string, content: string): string {
  return useMemo(() => {
    if (valueType !== "JSON") return "";
    try {
      JSON.parse(content);
      return "";
    } catch (e) {
      return `JSON 格式错误：${(e as Error).message}`;
    }
  }, [valueType, content]);
}

function CreateNamespaceModal({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (key: string) => void }) {
  const { toast } = useToast();
  const [form, setForm] = useState({ key: "", name: "", description: "" });
  const [busy, setBusy] = useState(false);
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="新建命名空间"
      footer={
        <ModalActions onCancel={onClose} busy={busy}>
          <Button disabled={busy || !form.key} onClick={async () => {
            setBusy(true);
            try {
              await dispatch("configcenter.namespaces.create", { action: "namespaces.create", payload: form });
              toast({ title: "命名空间已创建", tone: "success" });
              onCreated(form.key);
            } catch (err) {
              toast({ title: "创建失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
            } finally { setBusy(false); }
          }}>{busy ? "创建中…" : "创建"}</Button>
        </ModalActions>
      }
    >
      <div className="grid gap-3">
        <Field label="标识" hint="2-48 位小写字母/数字/下划线/横线，字母开头">
          <Input value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} placeholder="pricing" />
        </Field>
        <Field label="名称"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
        <Field label="描述"><Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
      </div>
    </Modal>
  );
}

function CreateItemModal({
  open, namespaces, defaultNamespace, onClose, onCreated,
}: {
  open: boolean;
  namespaces: Namespace[];
  defaultNamespace: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const { toast } = useToast();
  const [form, setForm] = useState({ namespace: defaultNamespace, key: "", name: "", value_type: "JSON", description: "" });
  const [content, setContent] = useState("{}");
  const [busy, setBusy] = useState(false);
  const jsonError = useValidateJson(form.value_type, content);
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="新建配置项"
      description="创建后为草稿版本，发布（可灰度）后宿主运行时可解析生效值"
      width="max-w-2xl"
      footer={
        <ModalActions onCancel={onClose} busy={busy}>
          <Button disabled={busy || !form.namespace || !form.key || Boolean(jsonError)} onClick={async () => {
            setBusy(true);
            try {
              await dispatch("configcenter.items.create", { action: "items.create", payload: { ...form, content } });
              toast({ title: "配置项已创建（草稿）", tone: "success" });
              onCreated();
            } catch (err) {
              toast({ title: "创建失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
            } finally { setBusy(false); }
          }}>{busy ? "创建中…" : "创建"}</Button>
        </ModalActions>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="命名空间">
          <Select value={form.namespace} onChange={(e) => setForm({ ...form, namespace: e.target.value })}>
            <option value="">选择命名空间</option>
            {namespaces.map((ns) => <option key={ns.key} value={ns.key}>{ns.name}（{ns.key}）</option>)}
          </Select>
        </Field>
        <Field label="配置键" hint="字母开头，仅字母/数字/下划线/点号/横线，长度 2-64">
          <Input value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} placeholder="discount_rate" />
        </Field>
        <Field label="名称"><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
        <Field label="类型">
          <Select value={form.value_type} onChange={(e) => setForm({ ...form, value_type: e.target.value })}>
            <option value="JSON">JSON</option>
            <option value="TEXT">TEXT</option>
          </Select>
        </Field>
        <Field label="内容" className="sm:col-span-2" hint={jsonError || undefined}>
          <Textarea rows={6} className="font-mono text-xs" value={content} onChange={(e) => setContent(e.target.value)} />
        </Field>
        <Field label="描述" className="sm:col-span-2">
          <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
      </div>
    </Modal>
  );
}

function EditDraftModal({ item, onClose }: { item: ConfigItem; onClose: () => void }) {
  const { toast } = useToast();
  const draft = [...item.versions].reverse().find((v) => v.status === "DRAFT");
  const [content, setContent] = useState(draft?.content ?? item.versions[item.versions.length - 1]?.content ?? "");
  const [changelog, setChangelog] = useState("");
  const [version, setVersion] = useState(draft?.version ?? "");
  const [busy, setBusy] = useState(false);
  const jsonError = useValidateJson(item.value_type, content);
  return (
    <Modal
      open
      onClose={onClose}
      title={`编辑草稿 · ${item.namespace}/${item.key}`}
      description={draft ? `当前草稿 ${draft.version}；留空版本号则就地更新或自动派生` : "无草稿：留空版本号自动派生新草稿"}
      width="max-w-2xl"
      footer={
        <ModalActions onCancel={onClose} busy={busy}>
          <Button disabled={busy || Boolean(jsonError)} onClick={async () => {
            setBusy(true);
            try {
              await dispatch("configcenter.items.version.save", {
                action: "items.version.save",
                payload: { namespace: item.namespace, key: item.key, version: version || undefined, content, changelog: changelog || undefined },
              });
              toast({ title: "草稿已保存", tone: "success" });
              onClose();
            } catch (err) {
              toast({ title: "保存失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
            } finally { setBusy(false); }
          }}>{busy ? "保存中…" : "保存草稿"}</Button>
        </ModalActions>
      }
    >
      <div className="grid gap-3">
        <Field label="版本号（留空自动）">
          <Input value={version} onChange={(e) => setVersion(e.target.value)} placeholder="v1.0.2" />
        </Field>
        <Field label={`内容（${item.value_type}）`} hint={jsonError || undefined}>
          <Textarea rows={8} className="font-mono text-xs" value={content} onChange={(e) => setContent(e.target.value)} />
        </Field>
        <Field label="变更说明">
          <Input value={changelog} onChange={(e) => setChangelog(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}

function PublishModal({ item, canWrite, onClose }: { item: ConfigItem; canWrite: boolean; onClose: () => void }) {
  const { toast } = useToast();
  const { activeEnvironments } = useScope();
  const draft = [...item.versions].reverse().find((v) => v.status === "DRAFT");
  const [version, setVersion] = useState(draft?.version ?? "");
  const [env, setEnv] = useState("");
  const [percent, setPercent] = useState(100);
  const [whitelist, setWhitelist] = useState("");
  const [busy, setBusy] = useState(false);
  return (
    <Modal
      open
      onClose={onClose}
      title={`发布 · ${item.namespace}/${item.key}`}
      description="灰度发布：命中百分比分桶或白名单的用户取新内容，其余取稳定版；全量发布即提升为稳定版"
      footer={
        <ModalActions onCancel={onClose} busy={busy}>
          <Button disabled={busy || !canWrite || !version} onClick={async () => {
            setBusy(true);
            try {
              await dispatch("configcenter.items.publish", {
                action: "items.publish",
                payload: {
                  namespace: item.namespace, key: item.key, version,
                  env: env || undefined,
                  gray: { percent, whitelist: whitelist.split(/[\s,]+/).filter(Boolean) },
                },
              });
              toast({ title: percent >= 100 ? "已全量发布" : "灰度发布已生效", tone: "success" });
              onClose();
            } catch (err) {
              toast({ title: "发布失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
            } finally { setBusy(false); }
          }}>{busy ? "发布中…" : "发布"}</Button>
        </ModalActions>
      }
    >
      <div className="grid gap-3">
        <Field label="发布环境" hint="预上线/线上为保护级：仅项目所有者可发布">
          <Select value={env} onChange={(e) => setEnv(e.target.value)}>
            <option value="">默认（遗留/无环境上下文）</option>
            {activeEnvironments.map((env) => (
              <option key={env.key} value={env.key}>{env.name}{env.protected ? " 🔒" : ""}</option>
            ))}
          </Select>
        </Field>
        <Field label="版本">
          <Select value={version} onChange={(e) => setVersion(e.target.value)}>
            {[...item.versions].reverse().filter((v) => v.status !== "SUPERSEDED").map((v) => (
              <option key={v.version} value={v.version}>{v.version}（{v.status}）</option>
            ))}
          </Select>
        </Field>
        <Field label="灰度百分比（100 = 全量）">
          <Input type="number" min={0} max={100} value={percent} onChange={(e) => setPercent(Number(e.target.value))} />
        </Field>
        <Field label="白名单 uid（逗号或空格分隔，直通灰度）">
          <Textarea rows={2} value={whitelist} onChange={(e) => setWhitelist(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}

function HistoryModal({ item, canWrite, onClose }: { item: ConfigItem; canWrite: boolean; onClose: () => void }) {
  const { toast } = useToast();
  const qc = useQueryClient();
  const history = useQuery({
    queryKey: ["config-history", item.namespace, item.key],
    queryFn: () =>
      dispatch<{ versions: ConfigVersion[]; stable_version: string }>("configcenter.items.history", {
        namespace: item.namespace, key: item.key,
      }),
  });
  const [diffPair, setDiffPair] = useState<[string, string] | null>(null);
  const rows = history.data?.versions || [];
  const byVersion = Object.fromEntries(rows.map((v) => [v.version, v]));
  const diffText = useMemo(() => {
    if (!diffPair) return "";
    const left = byVersion[diffPair[0]]?.content ?? "";
    const right = byVersion[diffPair[1]]?.content ?? "";
    return diffLines(left, right)
      .map((row) => {
        if (row.kind === "same") return `  ${row.left ?? ""}`;
        if (row.kind === "removed") return `- ${row.left ?? ""}`;
        return `+ ${row.right ?? ""}`;
      })
      .join("\n");
  }, [diffPair, byVersion]);

  const rollback = async (version: string) => {
    try {
      await dispatch("configcenter.items.rollback", {
        action: "items.rollback", payload: { namespace: item.namespace, key: item.key, version },
      });
      toast({ title: `已回滚到 ${version}`, tone: "success" });
      qc.invalidateQueries({ queryKey: ["config-history"] });
      qc.invalidateQueries({ queryKey: ["config-items"] });
      onClose();
    } catch (err) {
      toast({ title: "回滚失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
    }
  };

  return (
    <Modal open onClose={onClose} title={`版本历史 · ${item.namespace}/${item.key}`} width="max-w-2xl">
      <div className="space-y-2">
        {!rows.length ? (
          <EmptyState title="暂无版本" />
        ) : (
          rows.map((v) => (
            <div key={v.version} className="flex items-center justify-between gap-2 rounded-md border border-border/70 px-3 py-2">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium">{v.version}</span>
                  <Badge tone={v.status === "PUBLISHED" ? "success" : v.status === "DRAFT" ? "warning" : "neutral"}>{v.status}</Badge>
                  {history.data?.stable_version === v.version && <Badge tone="primary">稳定版</Badge>}
                </div>
                <div className="truncate text-xs text-muted-foreground">{v.changelog || "—"}</div>
              </div>
              <div className="flex shrink-0 gap-1.5">
                {canWrite && v.status !== "DRAFT" && history.data?.stable_version !== v.version && (
                  <Button variant="secondary" className="h-7 text-xs" onClick={() => rollback(v.version)}>回滚到此版</Button>
                )}
                <Button variant="ghost" className="h-7 text-xs"
                  onClick={() => setDiffPair(diffPair ? null : [v.version, history.data?.stable_version || v.version])}>
                  {diffPair?.[0] === v.version ? "收起对比" : "与稳定版对比"}
                </Button>
              </div>
            </div>
          ))
        )}
        {diffPair && (
          <Textarea readOnly rows={10} className="font-mono text-xs" value={diffText} />
        )}
      </div>
    </Modal>
  );
}
