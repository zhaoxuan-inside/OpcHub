import { useQuery } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import { Badge, Card, EmptyState, PageHeader, Spinner } from "@opchub/console-ui";

interface ScenarioAsset {
  name: string;
  display_name?: string;
  description?: string;
  current_version?: string;
  versions?: Array<{ version: string; status: string }>;
}

const statusTone: Record<string, "neutral" | "success" | "warning"> = {
  PUBLISHED: "success",
  DRAFT: "warning",
  SUPERSEDED: "neutral",
};

export function ScenariosPage() {
  const q = useQuery({
    queryKey: ["catalog-scenarios"],
    queryFn: () =>
      dispatch<{ scenarios: ScenarioAsset[]; total: number }>(
        "orchestration.catalog.scenarios",
        { page: 1, page_size: 100 },
      ),
  });

  return (
    <div>
      <PageHeader
        title="场景目录"
        description="对外发布的业务流程资产（子图内联展开，仅发布版本可编排）"
      />
      <Card>
        {q.isPending ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : !q.data?.scenarios?.length ? (
          <div className="p-5"><EmptyState title="暂无场景" /></div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-5 py-3 font-medium">场景</th>
                <th className="px-5 py-3 font-medium">当前版本</th>
                <th className="px-5 py-3 font-medium">状态</th>
                <th className="px-5 py-3 font-medium">版本数</th>
              </tr>
            </thead>
            <tbody>
              {q.data.scenarios.map((sc) => (
                <tr key={sc.name} className="border-b border-border/60 last:border-0 hover:bg-accent/40">
                  <td className="px-5 py-3">
                    <div className="font-medium">{sc.display_name || sc.name}</div>
                    <div className="max-w-md truncate text-xs text-muted-foreground">
                      {sc.description}
                    </div>
                  </td>
                  <td className="px-5 py-3 text-muted-foreground">{sc.current_version || "—"}</td>
                  <td className="px-5 py-3">
                    <Badge tone={statusTone[sc.versions?.[0]?.status || ""] || "neutral"}>
                      {sc.versions?.[0]?.status || "—"}
                    </Badge>
                  </td>
                  <td className="px-5 py-3 text-muted-foreground">{sc.versions?.length ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
