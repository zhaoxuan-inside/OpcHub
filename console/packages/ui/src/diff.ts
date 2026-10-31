/** Minimal LCS line diff for side-by-side JSON views (no external dependency). */
export type DiffRow = { kind: "same" | "added" | "removed"; left?: string; right?: string };

export function diffLines(left: string, right: string): DiffRow[] {
  const a = left.split("\n");
  const b = right.split("\n");
  const n = a.length;
  const m = b.length;
  // LCS table (fine for config-sized JSON; guard against pathological sizes)
  if (n * m > 4_000_000) {
    return [
      { kind: "removed", left: `（左侧 ${n} 行）` },
      { kind: "added", right: `（右侧 ${m} 行）` },
    ];
  }
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const rows: DiffRow[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      rows.push({ kind: "same", left: a[i], right: b[j] });
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      rows.push({ kind: "removed", left: a[i] });
      i++;
    } else {
      rows.push({ kind: "added", right: b[j] });
      j++;
    }
  }
  while (i < n) rows.push({ kind: "removed", left: a[i++] });
  while (j < m) rows.push({ kind: "added", right: b[j++] });
  return rows;
}
