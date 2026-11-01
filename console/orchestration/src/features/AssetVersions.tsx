/** 资产版本历史（三类资产共用）：状态徽标 + 草稿发布（直接发布或提交第二人审批）+ 回滚。
 *
 * 直接发布与回滚在持锁前提下执行（runWithLock：获取→动作→释放）；
 * 提交审批无需持锁（审批通过时以发起人身份执行，届时须仍持有编辑锁）。
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { PermissionGate, useToast } from "@opchub/console-ui";
import { Badge, Button, EmptyState } from "@opchub/console-ui";
import { catalogWrite, versionTone, type AssetKind, type AssetVersion } from "./catalog";

export function AssetVersions({
  assetKind,
  assetCode,
  versions,
  currentVersion,
  canWrite,
  runWithLock,
  onChanged,
}: {
  assetKind: AssetKind;
  assetCode: string;
  versions: AssetVersion[];
  currentVersion?: string;
  canWrite: boolean;
  runWithLock: (action: string, payload: Record<string, unknown>) => Promise<void>;
  onChanged: () => void;
}) {
  const { toast } = useToast();
  const qc = useQueryClient();
  const idField = assetKind === "operator" ? "name" : "code";

  const requestApproval = useMutation({
    mutationFn: (version: string) =>
      catalogWrite("approvals.request", { asset_kind: assetKind, code: assetCode, version }),
    onSuccess: () => {
      toast({
        title: "审批单已提交",
        description: "第二人通过后将以此刻的草稿状态发布；请保持编辑锁直至审批完成。",
        tone: "success",
      });
      qc.invalidateQueries({ queryKey: ["catalog"] });
      onChanged();
    },
    onError: (err: Error) =>
      toast({ title: "提交审批失败", description: err.message, tone: "destructive" }),
  });

  const withLock = useMutation({
    mutationFn: async ({ action, payload }: { action: string; payload: Record<string, unknown> }) => {
      await runWithLock(action, payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["catalog"] });
      onChanged();
    },
  });

  if (!versions.length) {
    return <EmptyState title="该资产没有版本记录" />;
  }

  const rows = [...versions].reverse();

  return (
    <div className="space-y-2">
      {rows.map((v) => (
        <div
          key={v.version}
          className="flex items-center justify-between gap-2 rounded-md border border-border/70 px-3 py-2"
        >
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium">{v.version}</span>
              <Badge tone={versionTone[v.status] || "neutral"}>{v.status}</Badge>
              {currentVersion === v.version && <Badge tone="primary">当前</Badge>}
            </div>
            <div className="truncate text-xs text-muted-foreground">
              {v.changelog || "—"}
              {v.published_by ? ` · ${v.published_by}` : v.created_by ? ` · ${v.created_by}` : ""}
            </div>
          </div>
          <PermissionGate permission="orchestration:write">
            <div className="flex shrink-0 items-center gap-1.5">
              {canWrite && v.status === "DRAFT" && (
                <>
                  <Button
                    variant="secondary"
                    className="h-7 text-xs"
                    disabled={withLock.isPending}
                    onClick={() =>
                      withLock.mutate({
                        action: `${assetKind}s.publish`,
                        payload: { [idField]: assetCode, version: v.version },
                      })
                    }
                  >
                    直接发布
                  </Button>
                  <Button
                    variant="secondary"
                    className="h-7 text-xs"
                    disabled={requestApproval.isPending}
                    onClick={() => requestApproval.mutate(v.version)}
                  >
                    提交发布审批
                  </Button>
                </>
              )}
              {canWrite && v.status !== "DRAFT" && currentVersion !== v.version && (
                <Button
                  variant="secondary"
                  className="h-7 text-xs"
                  disabled={withLock.isPending}
                  onClick={() =>
                    withLock.mutate({
                      action: `${assetKind}s.rollback`,
                      payload: { [idField]: assetCode, version: v.version },
                    })
                  }
                >
                  回滚到此版本
                </Button>
              )}
            </div>
          </PermissionGate>
        </div>
      ))}
    </div>
  );
}
