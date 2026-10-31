import { useQuery } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import {
  Badge,
  Card,
  EmptyState,
  PageHeader,
  Spinner,
  cn,
} from "@opchub/console-ui";

interface OperatorAsset {
  name: string;
  display_name?: string;
  description?: string;
  source?: string;
  current_version?: string;
  lock_status?: { holder?: string } | null;
  in_use?: boolean;
}

export function OperatorsPage() {
  const q = useQuery({
    queryKey: ["catalog-operators"],
    queryFn: () =>
      dispatch<{ operators: OperatorAsset[]; total: number }>(
        "orchestration.catalog.operators",
        { page: 1, page_size: 100 },
      ),
  });

  return (
    <div>
      <PageHeader
        title="算子目录"
        description="契约化算子注册表（内置 + 自定义，含版本与锁定状态）"
      />
      <Card>
        {q.isPending ? (
          <div className="flex justify-center py-16"><Spinner /></div>
        ) : !q.data?.operators?.length ? (
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
              </tr>
            </thead>
            <tbody>
              {q.data.operators.map((op) => (
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
                    <span
                      className={cn(
                        "text-xs",
                        op.lock_status?.holder ? "text-warning" : "text-muted-foreground",
                      )}
                    >
                      {op.lock_status?.holder ? `被 ${op.lock_status.holder} 锁定` : "空闲"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
