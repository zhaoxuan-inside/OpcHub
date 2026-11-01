/** 编排目录契约：写操作信封、类型与共享工具。
 *
 * 写操作统一 {action, payload} 双层信封（catalog_write_adapter 契约），
 * 由 OPC_ORCHESTRATION_CATALOG_PIPELINE 执行；读操作直连 catalog.* 场景。
 */
import { dispatch } from "@opchub/console-api";

export type AssetKind = "operator" | "subgraph" | "scenario";

export interface AssetVersion {
  version: string;
  status: "DRAFT" | "PUBLISHED" | "SUPERSEDED";
  changelog?: string;
  created_by?: string;
  created_at?: string;
  published_by?: string;
  published_at?: string;
  definition?: { code?: string; entry_function?: string };
  graph?: {
    entry_node: string;
    exit_node: string;
    nodes: GraphNode[];
    edges: GraphEdge[];
    enable_saga_compensation?: boolean;
  };
  compiled?: unknown;
}

export interface GraphNode {
  id: string;
  _x?: number; // 画布拖拽位置缓存（仅前端呈现，不参与后端校验）
  _y?: number;
  kind?: "OPERATOR" | "SUBGRAPH";
  operator?: string;
  operator_version?: string;
  subgraph?: string;
  subgraph_version?: string;
  type: string; // GUARD | BIZ | STORAGE | CACHE
  timeout_ms?: number;
}

export interface GraphEdge {
  from_node: string;
  to_node: string;
}

export interface CatalogAsset {
  name?: string; // operator
  code?: string; // subgraph / scenario
  display_name?: string;
  description?: string;
  domain?: string;
  source?: "builtin" | "custom" | "managed" | "runtime";
  current_version?: string;
  versions?: AssetVersion[];
  created_by?: string;
  project_id?: string;
  lock_status?: AssetLockState | null;
  runtime_status?: string;
  referenced_by?: string[];
  in_use?: boolean;
}

export interface AssetLockState {
  entity_type: string;
  entity_key: string;
  holder_id: string;
  holder_name?: string;
  expires_at?: string;
}

/** 目录写操作：锁由调用方持有，这里只负责信封。 */
export async function catalogWrite<T = CatalogAsset>(action: string, payload: Record<string, unknown>) {
  const route = `orchestration.${action}`;
  return dispatch<T>(route, { action, payload });
}

export function assetId(asset: CatalogAsset): string {
  return asset.name || asset.code || "";
}

export function assetKindLabel(kind: AssetKind): string {
  return kind === "operator" ? "算子" : kind === "subgraph" ? "子图" : "场景";
}

export function assetIdField(kind: AssetKind): "name" | "code" {
  return kind === "operator" ? "name" : "code";
}

export const versionTone: Record<string, "neutral" | "success" | "warning" | "primary"> = {
  DRAFT: "warning",
  PUBLISHED: "success",
  SUPERSEDED: "neutral",
};

/** 节点类型推断（与主站 GraphEditor inferNodeType 语义一致）。 */
export function inferNodeType(handlerKey: string): string {
  if (/guard|validate|check/.test(handlerKey)) return "GUARD";
  if (/persist|save|store/.test(handlerKey)) return "STORAGE";
  if (/cache/.test(handlerKey)) return "CACHE";
  return "BIZ";
}
