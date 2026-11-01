/** 跨项目显式复制入口：项目完全隔离下复用资产的唯一通道。
 *
 * 目标项目限定为当前用户持有编排写权限的项目；编码全局唯一，
 * 占用时由后端自动派生空闲编码。
 */
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import { useScope } from "@opchub/console-ui";
import { Button, Input } from "@opchub/console-ui";

export function CopyToProject({
  assetKind,
  code,
}: {
  assetKind: "operator" | "subgraph" | "scenario";
  code: string;
}) {
  const { myScope, refresh } = useScope();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [target, setTarget] = useState("");
  const [newCode, setNewCode] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const targets = (myScope?.projects || []).filter(
    (p) => p.status === "ACTIVE" && (p.role?.permissions || []).includes("orchestration:write"),
  );
  if (!targets.length) return null;

  const copy = async () => {
    if (!target) return;
    setPending(true);
    setMessage(null);
    try {
      const result = await dispatch<{ name?: string; code?: string }>("orchestration.assets.copy", {
        action: "assets.copy",
        payload: {
          asset_kind: assetKind,
          code,
          target_project_id: target,
          ...(newCode.trim() ? { new_code: newCode.trim() } : {}),
        },
      });
      const landed = result.name || result.code || "";
      setMessage(landed ? `已复制为 ${landed}` : "复制成功");
      setNewCode("");
      setOpen(false);
      refresh();
      qc.invalidateQueries({ queryKey: ["catalog-operators"] });
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="inline-flex flex-col gap-1">
      <Button variant="secondary" className="h-7 text-xs" onClick={() => setOpen(!open)}>
        复制到项目
      </Button>
      {open && (
        <div className="flex items-center gap-1.5 rounded-md border border-border bg-background p-1.5">
          <select
            aria-label="选择目标项目"
            className="h-7 rounded-md border border-border bg-background px-1.5 text-xs"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
          >
            <option value="">目标项目</option>
            {targets.map((p) => (
              <option key={p.project_id} value={p.project_id}>
                {p.name}
              </option>
            ))}
          </select>
          <Input
            placeholder="新编码（可选）"
            value={newCode}
            onChange={(e) => setNewCode(e.target.value)}
            className="h-7 w-28 text-xs"
          />
          <Button className="h-7 text-xs" disabled={!target || pending} onClick={copy}>
            {pending ? "复制中…" : "确认"}
          </Button>
        </div>
      )}
      {message && <span className="text-[11px] text-muted-foreground">{message}</span>}
    </div>
  );
}
