import { useQuery } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import { Card, CardContent, CardHeader, CardTitle, PageHeader, Spinner } from "@opchub/console-ui";

interface CatalogList {
  total?: number;
}

export function OverviewPage() {
  const counts = useQuery({
    queryKey: ["catalog-counts"],
    queryFn: async () => {
      const [operators, subgraphs, scenarios] = await Promise.all([
        dispatch<CatalogList>("orchestration.catalog.operators", { page: 1, page_size: 1 }),
        dispatch<CatalogList>("orchestration.catalog.subgraphs", { page: 1, page_size: 1 }),
        dispatch<CatalogList>("orchestration.catalog.scenarios", { page: 1, page_size: 1 }),
      ]);
      return {
        operators: operators?.total ?? 0,
        subgraphs: subgraphs?.total ?? 0,
        scenarios: scenarios?.total ?? 0,
      };
    },
  });

  const cards = [
    { label: "算子", value: counts.data?.operators, hint: "契约化的最小业务单元" },
    { label: "子图", value: counts.data?.subgraphs, hint: "可复用的复合编排" },
    { label: "场景", value: counts.data?.scenarios, hint: "对外发布的业务流程" },
  ];

  return (
    <div>
      <PageHeader title="总览" description="三层资产目录与 MicroFlow release 概览" />
      <div className="grid gap-4 sm:grid-cols-3">
        {cards.map((c) => (
          <Card key={c.label}>
            <CardHeader>
              <CardTitle className="text-muted-foreground">{c.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-semibold tracking-tight">
                {counts.isPending ? <Spinner /> : c.value ?? 0}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">{c.hint}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
