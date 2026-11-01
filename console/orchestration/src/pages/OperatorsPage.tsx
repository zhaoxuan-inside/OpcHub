/** 算子目录 · 全生命周期：创建（沙箱脚本）→ 草稿编辑（持锁）→ 发布/审批 → 回滚 → 删除。
 *
 * 内置算子只读展示（随平台代码发布）；自建算子经 OPC_ORCHESTRATION_CATALOG_PIPELINE
 * 执行全部变更（{action, payload} 信封）。
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
  cn,
  useAssetLock,
  useScope,
  useToast,
} from "@opchub/console-ui";
import { CopyToProject } from "../components/CopyToProject";
import { AssetVersions } from "../features/AssetVersions";
import {
  catalogWrite,
  type AssetVersion,
  type CatalogAsset,
} from "../features/catalog";

const SCRIPT_PLACEHOLDER = "async def action_entry(inputs, context):\n    return {'result': inputs.get('x', 0) * 2}";

export function OperatorsPage() {
  const { hasPermission, myScope } = useScope();
  const { toast } = useToast();
  const qc = useQueryClient();
  const canWrite = hasPermission("orchestration:write");
  const myUserId = myScope?.user_id;

  const list = useQuery({
    queryKey: ["catalog-operators"],
    queryFn: () =>
      dispatch<{ operators: CatalogAsset[]; total: number }>(
        "orchestration.catalog.operators",
        { page: 1, page_size: 200 },
      ),
  });

  const [selected, setSelected] = useState("");
  const [creating, setCreating] = useState(false);

  const detail = useQuery({
    queryKey: ["catalog-operator", selected],
    queryFn: () => dispatch<CatalogAsset>("orchestration.catalog.operator", { name: selected }),
    enabled: Boolean(selected),
  });

  const lock = useAssetLock("operator", { myUserId });
  const detailAsset = detail.data;
  const isCustom = Boolean(detailAsset && detailAsset.source !== "builtin");

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["catalog-operators"] });
    qc.invalidateQueries({ queryKey: ["catalog-operator"] });
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
    if (!window.confirm(`删除算子「${selected}」？被已发布子图/场景引用时会被拒绝。`)) return;
    try {
      await runWithLock("operators.delete", { name: selected });
      setSelected("");
      refresh();
    } catch (err) {
      toast({ title: "删除失败", description: err instanceof Error ? err.message : String(err), tone: "destructive" });
    }
  };

  return (
    <div>
      <PageHeader
        title="算子目录"
        description="契约化算子注册表：内置算子随平台发布，自建算子走创建 → 草稿 → 发布全生命周期"
        actions={
          <PermissionGate permission="orchestration:write">
            <Button className="h-8 text-xs" onClick={() => setCreating(true)}>
              新建算子
            </Button>
          </PermissionGate>
        }
      />

      <Card className="mb-4">
        {list.isPending ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : !list.data?.operators?.length ? (
          <div className="p-5"><EmptyState title="暂无算子" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-5 py-3 font-medium">名称</th>
                <th className="px-5 py-3 font-medium">当前版本</th>
                <th className="px-5 py-3 font-medium">来源</th>
                <th className="px-5 py-3 font-medium">被引用</th>
                <th className="px-5 py-3 font-medium">锁定</th>
                <th className="px-5 py-3 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {list.data.operators.map((op) => (
                <tr key={op.name} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                  <td className="px-5 py-3">
                    <div className="font-medium">{op.display_name || op.name}</div>
                    <div className="text-xs text-muted-foreground">{op.name}</div>
                  </td>
                  <td className="px-5 py-3 text-muted-foreground">{op.current_version || "—"}</td>
                  <td className="px-5 py-3">
                    <Badge tone={op.source === "builtin" ? "neutral" : "primary"}>
                      {op.source === "builtin" ? "内置" : "自定义"}
                    </Badge>
                  </td>
                  <td className="px-5 py-3 text-muted-foreground">{op.in_use ? "是" : "否"}</td>
                  <td className="px-5 py-3">
                    <span className={cn("text-xs", op.lock_status?.holder_name ? "text-warning" : "text-muted-foreground")}>
                      {op.lock_status?.holder_name ? `被 ${op.lock_status.holder_name} 锁定` : "空闲"}
                    </span>
                  </td>
                  <td className="px-5 py-3">
                    <div className="flex gap-2">
                      <Button variant="secondary" className="h-7 text-xs" onClick={() => setSelected(op.name!)}>
                        详情
                      </Button>
                      {op.source !== "builtin" && (
                        <PermissionGate permission="orchestration:write">
                          <CopyToProject assetKind="operator" code={op.name!} />
                        </PermissionGate>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {selected && detailAsset && (
        <OperatorDetail
          asset={detailAsset}
          isCustom={isCustom}
          canWrite={canWrite}
          lock={lock}
          runWithLock={runWithLock}
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

      <CreateOperatorModal
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={(name) => {
          setCreating(false);
          setSelected(name);
          refresh();
        }}
      />
    </div>
  );
}

function OperatorDetail({
  asset,
  isCustom,
  canWrite,
  lock,
  runWithLock,
  onRemove,
  onChanged,
  onClose,
}: {
  asset: CatalogAsset;
  isCustom: boolean;
  canWrite: boolean;
  lock: ReturnType<typeof useAssetLock>;
  runWithLock: (action: string, payload: Record<string, unknown>) => Promise<void>;
  onRemove: () => void;
  onChanged: () => void;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const name = asset.name!;
  const versions: AssetVersion[] = asset.versions || [];

  const latestDraft = useMemo(
    () => [...versions].reverse().find((v) => v.status === "DRAFT"),
    [versions],
  );
  const [displayName, setDisplayName] = useState(asset.display_name || name);
  const [description, setDescription] = useState(asset.description || "");
  const [changelog, setChangelog] = useState("");
  const [code, setCode] = useState(latestDraft?.definition?.code || "");
  const [saving, setSaving] = useState(false);

  const editable = isCustom && canWrite && lock.heldByMe;

  const saveDraft = async () => {
    if (!code.trim()) {
      toast({ title: "脚本内容不能为空", tone: "warning" });
      return;
    }
    setSaving(true);
    try {
      await catalogWrite("operators.version.save", {
        name,
        display_name: displayName,
        description,
        changelog: changelog || undefined,
        definition: { code, entry_function: latestDraft?.definition?.entry_function || "action_entry" },
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
            <CardTitle className="text-base">{asset.display_name || name}</CardTitle>
            <div className="flex items-center gap-2">
              {isCustom && canWrite && (
                <Button variant="destructive" className="h-7 text-xs" onClick={onRemove}>
                  删除算子
                </Button>
              )}
              <Button variant="secondary" className="h-7 text-xs" onClick={onClose}>
                收起
              </Button>
            </div>
          </div>
          <p className="text-xs text-muted-foreground">
            {name}
            {asset.domain ? ` · ${asset.domain}` : ""}
            {asset.description ? ` · ${asset.description}` : ""}
            {asset.referenced_by?.length ? ` · 被引用：${asset.referenced_by.join("、")}` : ""}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {isCustom ? (
            <>
              <AssetLockBanner
                assetLabel={name}
                heldByMe={lock.heldByMe}
                heldByOther={lock.heldByOther}
                holderLabel={lock.holderLabel}
                remainingSeconds={lock.remainingSeconds}
                busy={lock.busy}
                onAcquire={() =>
                  lock.acquire(name).catch((err: Error) =>
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
              <Field
                label="脚本（入口 async def action_entry(inputs, context)）"
                hint="保存与发布均经过沙箱校验；发布前进行沙箱复检。"
              >
                <Textarea
                  rows={10}
                  className="font-mono text-xs"
                  value={code}
                  disabled={!editable}
                  onChange={(e) => setCode(e.target.value)}
                  placeholder={SCRIPT_PLACEHOLDER}
                />
              </Field>
              <div className="flex items-end gap-3">
                <Field label="变更说明" className="flex-1">
                  <Input
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
              内置算子由平台代码注册发布，此处只读展示（当前版本 {asset.current_version || "v1.0.0"}）。
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>版本历史</CardTitle></CardHeader>
        <CardContent>
          <AssetVersions
            assetKind="operator"
            assetCode={name}
            versions={versions}
            currentVersion={asset.current_version}
            canWrite={isCustom && canWrite}
            runWithLock={runWithLock}
            onChanged={onChanged}
          />
        </CardContent>
      </Card>
    </div>
  );
}

function CreateOperatorModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (name: string) => void;
}) {
  const { toast } = useToast();
  const [form, setForm] = useState({ name: "", display_name: "", domain: "custom", description: "", version: "v1.0.0", changelog: "初始版本" });
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);

  const create = async () => {
    setBusy(true);
    try {
      // 创建即占名并落首个草稿：先 create，再 version.save 携带脚本
      const asset = await catalogWrite<{ name: string }>("operators.create", {
        name: form.name,
        display_name: form.display_name || form.name,
        domain: form.domain || "custom",
        description: form.description,
        version: form.version,
        changelog: form.changelog,
      });
      if (code.trim()) {
        await catalogWrite("operators.version.save", {
          name: asset.name,
          definition: { code, entry_function: "action_entry" },
          changelog: form.changelog,
        });
      }
      toast({ title: "算子已创建（草稿）", description: "编辑并发布后进入运行时算子池", tone: "success" });
      onCreated(asset.name);
      setForm({ name: "", display_name: "", domain: "custom", description: "", version: "v1.0.0", changelog: "初始版本" });
      setCode("");
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
      title="新建算子"
      description="创建后处于草稿态，持锁编辑脚本并发布（或提交发布审批）后进入运行时算子池"
      footer={
        <ModalActions onCancel={onClose} busy={busy}>
          <Button disabled={busy || !form.name} onClick={create}>
            {busy ? "创建中…" : "创建"}
          </Button>
        </ModalActions>
      }
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="算子名" hint="字母开头，仅字母/数字/下划线/点号，长度 2-64">
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="my_operator" />
        </Field>
        <Field label="显示名">
          <Input value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
        </Field>
        <Field label="域标签">
          <Input value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })} />
        </Field>
        <Field label="版本号">
          <Input value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} />
        </Field>
        <Field label="描述" className="sm:col-span-2">
          <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Field label="初始脚本（可留空稍后在编辑器填写）" className="sm:col-span-2">
          <Textarea rows={8} className="font-mono text-xs" value={code} onChange={(e) => setCode(e.target.value)} placeholder={SCRIPT_PLACEHOLDER} />
        </Field>
      </div>
    </Modal>
  );
}
