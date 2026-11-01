import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import {
  Badge,
  Button,
  PermissionGate,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  EmptyState,
  Input,
  PageHeader,
  Spinner,
  cn,
} from "@opchub/console-ui";
import { diffLines } from "@opchub/console-ui";

interface VersionRow {
  version: string;
  status: string;
  changelog?: string;
  published_by?: string;
  published_at?: string;
}
interface ScenarioDetail {
  code: string;
  current_version?: string;
  versions: VersionRow[];
}

const statusTone: Record<string, "neutral" | "success" | "warning"> = {
  PUBLISHED: "success",
  DRAFT: "warning",
  SUPERSEDED: "neutral",
};

export function ReleasesPage() {
  const qc = useQueryClient();
  const [code, setCode] = useState("");
  const [left, setLeft] = useState("");
  const [right, setRight] = useState("");

  const scenarios = useQuery({
    queryKey: ["catalog-scenarios"],
    queryFn: () =>
      dispatch<{ scenarios: Array<{ code: string; display_name?: string }> }>(
        "orchestration.catalog.scenarios",
        { page: 1, page_size: 200 },
      ),
  });

  const detail = useQuery({
    queryKey: ["scenario-detail", code],
    enabled: !!code,
    queryFn: () => dispatch<ScenarioDetail>("orchestration.catalog.scenario", { code }),
  });

  const dagList = useQuery({
    queryKey: ["dag-list", code],
    enabled: !!code,
    queryFn: () =>
      dispatch<{ configs: Array<{ version: string; status: string; topology_graph: unknown; compiled_hash: string }> }>(
        "orchestration.dag.list",
        { scenario_code: code },
      ),
  });

  const approvals = useQuery({
    queryKey: ["release-approvals"],
    queryFn: () =>
      dispatch<{ approvals: Array<Record<string, string>> }>("orchestration.approvals.list", {}),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["scenario-detail", code] });
    qc.invalidateQueries({ queryKey: ["dag-list", code] });
    qc.invalidateQueries({ queryKey: ["release-approvals"] });
  };

  const act = useMutation({
    mutationFn: ({ scenario, payload }: { scenario: string; payload: Record<string, unknown> }) =>
      dispatch(scenario, payload),
    onSuccess: invalidate,
  });
  const actWithLock = useMutation({
    mutationFn: async ({ scenario, payload }: { scenario: string; payload: Record<string, unknown> }) => {
      await dispatch("orchestration.locks.acquire", { entity_type: "scenario", entity_key: code });
      try {
        return await dispatch(scenario, payload);
      } finally {
        await dispatch("orchestration.locks.release", { entity_type: "scenario", entity_key: code });
      }
    },
    onSuccess: invalidate,
  });

  const versions = detail.data?.versions || [];
  const configs = dagList.data?.configs || [];
  const configOf = (v: string) => configs.find((c) => c.version === v);

  const diffRows = useMemo(() => {
    if (!left || !right) return null;
    const l = configOf(left);
    const r = configOf(right);
    if (!l?.topology_graph || !r?.topology_graph) return null;
    return diffLines(
      JSON.stringify(l.topology_graph, null, 2),
      JSON.stringify(r.topology_graph, null, 2),
    );
  }, [left, right, dagList.data]);

  const errMsg = (act.error || actWithLock.error) as { message?: string } | null;

  return (
    <div>
      <PageHeader
        title="版本与发布"
        description="场景版本历史 / 部署 diff / 一键回滚 / 第二人发布审批"
      />

      <div className="mb-4 flex items-center gap-2">
        <Input
          list="scenario-codes"
          placeholder="选择或输入场景编码…"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="max-w-xs"
        />
        <datalist id="scenario-codes">
          {(scenarios.data?.scenarios || []).map((s) => (
            <option key={s.code} value={s.code}>
              {s.display_name || s.code}
            </option>
          ))}
        </datalist>
      </div>

      {errMsg && (
        <div className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {errMsg.message}
        </div>
      )}

      {code && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>版本历史 {detail.isPending && <Spinner className="ml-2" />}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {versions.map((v) => (
                <div
                  key={v.version}
                  className="flex items-center justify-between gap-2 rounded-md border border-border/70 px-3 py-2"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{v.version}</span>
                      <Badge tone={statusTone[v.status] || "neutral"}>{v.status}</Badge>
                      {detail.data?.current_version === v.version && (
                        <Badge tone="primary">当前</Badge>
                      )}
                    </div>
                    <div className="truncate text-xs text-muted-foreground">
                      {v.changelog || "—"} {v.published_by ? `· ${v.published_by}` : ""}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    <PermissionGate permission="orchestration:write">
                      {v.status !== "PUBLISHED" && (
                        <Button
                          variant="secondary"
                          onClick={() =>
                            actWithLock.mutate({
                              scenario: "orchestration.scenarios.rollback",
                              payload: { action: "scenarios.rollback", payload: { code, version: v.version } },
                            })
                          }
                          disabled={actWithLock.isPending}
                        >
                          回滚到此版本
                        </Button>
                      )}
                      {v.status === "DRAFT" && (
                        <Button
                          variant="secondary"
                          onClick={() =>
                            act.mutate({
                              scenario: "orchestration.approvals.request",
                              payload: { action: "approvals.request", payload: { asset_kind: "scenario", code, version: v.version } },
                            })
                          }
                          disabled={act.isPending}
                        >
                          提交发布审批
                        </Button>
                      )}
                    </PermissionGate>
                  </div>
                </div>
              ))}
              {!detail.isPending && !versions.length && (
                <EmptyState title="该场景没有版本记录" />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>部署 diff（选择两个已部署版本）</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-3 flex items-center gap-2">
                <select
                  className="h-9 rounded-md border border-input bg-card px-2 text-sm"
                  value={left}
                  onChange={(e) => setLeft(e.target.value)}
                >
                  <option value="">左…</option>
                  {configs.map((c) => (
                    <option key={c.version} value={c.version}>
                      {c.version}（{c.status}）
                    </option>
                  ))}
                </select>
                <span className="text-muted-foreground">→</span>
                <select
                  className="h-9 rounded-md border border-input bg-card px-2 text-sm"
                  value={right}
                  onChange={(e) => setRight(e.target.value)}
                >
                  <option value="">右…</option>
                  {configs.map((c) => (
                    <option key={c.version} value={c.version}>
                      {c.version}（{c.status}）
                    </option>
                  ))}
                </select>
              </div>
              {diffRows ? (
                <div className="max-h-96 overflow-auto rounded-md border border-border font-mono text-xs">
                  {diffRows.map((row, idx) => (
                    <div
                      key={idx}
                      className={cn(
                        "grid grid-cols-2 gap-px",
                        row.kind === "added" && "bg-success/8",
                        row.kind === "removed" && "bg-destructive/8",
                      )}
                    >
                      <pre className={cn("px-2 py-0.5", row.kind === "removed" && "text-destructive")}>
                        {row.left || ""}
                      </pre>
                      <pre className={cn("px-2 py-0.5", row.kind === "added" && "text-success")}>
                        {row.right || ""}
                      </pre>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="选择左右两个版本查看部署差异" />
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>发布审批（第二人确认制）</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {approvals.isPending ? (
            <Spinner />
          ) : !approvals.data?.approvals?.length ? (
            <EmptyState title="暂无审批单" hint="在版本历史里对草稿版本提交发布审批" />
          ) : (
            approvals.data.approvals.map((a) => (
              <div
                key={a.id}
                className="flex items-center justify-between gap-2 rounded-md border border-border/70 px-3 py-2"
              >
                <div className="min-w-0 text-sm">
                  <span className="font-medium">
                    {a.asset_kind} {a.code}@{a.version}
                  </span>
                  <span className="ml-2 text-xs text-muted-foreground">
                    发起 {a.requested_by} · {a.requested_at?.slice(0, 19).replace("T", " ")}
                  </span>
                  {a.note && <div className="truncate text-xs text-muted-foreground">{a.note}</div>}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge
                    tone={
                      a.status === "APPROVED"
                        ? "success"
                        : a.status === "PENDING"
                          ? "warning"
                          : "destructive"
                    }
                  >
                    {a.status}
                  </Badge>
                  {a.status === "PENDING" && (
                    <PermissionGate permission="orchestration:write">
                      <Button
                        variant="secondary"
                        onClick={() =>
                          act.mutate({
                            scenario: "orchestration.approvals.reject",
                            payload: { action: "approvals.reject", payload: { approval_id: a.id, note: "驳回" } },
                          })
                        }
                      >
                        驳回
                      </Button>
                      <Button
                        onClick={() =>
                          act.mutate({
                            scenario: "orchestration.approvals.approve",
                            payload: { action: "approvals.approve", payload: { approval_id: a.id } },
                          })
                        }
                      >
                        通过并执行
                      </Button>
                    </PermissionGate>
                  )}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
