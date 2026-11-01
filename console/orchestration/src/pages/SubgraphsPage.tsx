/** 子图目录：已发布算子的可复用编排；发布时编译为算子级扁平图。 */
import { GraphAssetPage } from "../features/GraphAssetPage";

export function SubgraphsPage() {
  return <GraphAssetPage assetKind="subgraph" />;
}
