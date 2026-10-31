import { PageHeader } from "@opchub/console-ui";

export function ConfigsPage() {
  return (
    <div>
      <PageHeader
        title="配置管理"
        description="命名空间 → 配置项 → 历史 → 灰度发布 —— M1-3 交付"
      />
      <div className="rounded-lg border border-dashed border-border p-12 text-center text-sm text-muted-foreground">
        配置管理页在 M1-3 交付。
      </div>
    </div>
  );
}
