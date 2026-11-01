import { useQuery } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import { useScope } from "@opchub/console-ui";
import { Card, CardContent, CardHeader, CardTitle, PageHeader, Spinner } from "@opchub/console-ui";

interface MyScopeResp {
  is_platform_super: boolean;
  tenants: unknown[];
  projects: unknown[];
}

export function OverviewPage() {
  const scope = useQuery({
    queryKey: ["platform", "my-scope"],
    queryFn: () => dispatch<MyScopeResp>("platform.scope.my", {}),
  });

  const cards = [
    { label: "我的租户", value: scope.data?.tenants?.length ?? 0, hint: "在册的组织实体" },
    { label: "我的项目", value: scope.data?.projects?.length ?? 0, hint: "可操作的项目范围" },
    { label: "平台管理员", value: scope.data?.is_platform_super ? "是" : "否", hint: "平台级通配权限" },
  ];

  return (
    <div>
      <PageHeader title="总览" description="运营平台：业务埋点采集 / 漏斗留存 / 实验读出" />
      <div className="grid gap-4 sm:grid-cols-3">
        {cards.map((c) => (
          <Card key={c.label}>
            <CardHeader>
              <CardTitle className="text-muted-foreground">{c.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-semibold tracking-tight">
                {scope.isPending ? <Spinner /> : (c.value ?? 0)}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{c.hint}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      <Card className="mt-4 border-dashed">
        <CardContent className="px-5 py-6">
          <div className="text-sm font-medium">埋点分析能力在 M3 里程碑交付</div>
          <p className="mt-1 text-xs text-muted-foreground">
            漏斗、留存与实验读出依赖主站埋点事件接入；当前阶段先交付治理底座（分租户 / 分用户 / 分权限 / 分项目）与活动范围切换。
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
