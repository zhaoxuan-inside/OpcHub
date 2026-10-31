import { PageHeader } from "@opchub/console-ui";

export function ExperimentsPage() {
  return (
    <div>
      <PageHeader
        title="A/B 实验"
        description="实验域模型（变体/流量分配/护栏指标）—— M1-2 交付服务端与分配 API"
      />
      <div className="rounded-lg border border-dashed border-border p-12 text-center text-sm text-muted-foreground">
        实验管理页在 M1-2 交付：创建实验 → 变体与流量 → 运行 → 读出。
      </div>
    </div>
  );
}
