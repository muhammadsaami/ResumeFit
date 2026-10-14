export type DiffTokenType = "same" | "added" | "removed";

export interface DiffToken {
  text: string;
  type: DiffTokenType;
}

export interface WordDiff {
  left: DiffToken[];
  right: DiffToken[];
}

function words(value: string): string[] {
  return value.trim().split(/\s+/).filter(Boolean);
}

/**
 * A small, dependency-free word-level diff (longest common subsequence).
 * The left side marks removed words; the right side marks added words.
 */
export function diffWords(before: string, after: string): WordDiff {
  const a = words(before);
  const b = words(after);
  const n = a.length;
  const m = b.length;

  const table: number[][] = Array.from({ length: n + 1 }, () =>
    new Array<number>(m + 1).fill(0),
  );
  for (let i = n - 1; i >= 0; i -= 1) {
    for (let j = m - 1; j >= 0; j -= 1) {
      table[i][j] = a[i] === b[j] ? table[i + 1][j + 1] + 1 : Math.max(table[i + 1][j], table[i][j + 1]);
    }
  }

  const left: DiffToken[] = [];
  const right: DiffToken[] = [];
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      left.push({ text: a[i], type: "same" });
      right.push({ text: b[j], type: "same" });
      i += 1;
      j += 1;
    } else if (table[i + 1][j] >= table[i][j + 1]) {
      left.push({ text: a[i], type: "removed" });
      i += 1;
    } else {
      right.push({ text: b[j], type: "added" });
      j += 1;
    }
  }
  while (i < n) {
    left.push({ text: a[i], type: "removed" });
    i += 1;
  }
  while (j < m) {
    right.push({ text: b[j], type: "added" });
    j += 1;
  }
  return { left, right };
}
