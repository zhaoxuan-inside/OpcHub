import { useQuery } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import { Card, CardContent, CardHeader, CardTitle, PageHeader } from "@opchub/console-ui";

export function ReleasesPage() {
  const rules = useQuery({
    queryKey: ["gateway-rules"],
    queryFn: () => dispatch("gateway.rules", {}),
  });

  return (
    <div>
      <PageHeader
        title="版本与发布"
        description="MicroFlow release、场景版本历史与发布审批（M1-1 交付 diff/回滚/审批门）"
      />
      <Card>
        <CardHeader>
          <CardTitle>网关路由规则（当前生效版本治理面）</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="max-h-96 overflow-auto rounded-md bg-muted p-3 text-xs leading-relaxed">
            {JSON.stringify(rules.data, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}
