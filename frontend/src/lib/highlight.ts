export type HighlightTone = "green" | "amber";

export interface HighlightSegment {
  text: string;
  tone: HighlightTone | null;
}

interface Span {
  start: number;
  end: number;
  tone: HighlightTone;
}

const TONE_RANK: Record<HighlightTone, number> = { green: 0, amber: 1 };

function isBoundary(char: string | undefined): boolean {
  return char === undefined || !/[a-z0-9]/i.test(char);
}

function collectTermSpans(line: string, terms: string[], tone: HighlightTone): Span[] {
  const spans: Span[] = [];
  const lower = line.toLowerCase();
  for (const term of terms) {
    const needle = term.toLowerCase().trim();
    if (!needle) continue;
    let from = 0;
    while (from <= lower.length - needle.length) {
      const index = lower.indexOf(needle, from);
      if (index === -1) break;
      const before = index > 0 ? lower[index - 1] : undefined;
      const after = index + needle.length < lower.length ? lower[index + needle.length] : undefined;
      if (isBoundary(before) && isBoundary(after)) {
        spans.push({ start: index, end: index + needle.length, tone });
      }
      from = index + needle.length;
    }
  }
  return spans;
}

/**
 * Split a single line into segments, marking any whole-word occurrences of the
 * green/amber term lists. Longer matches win; green outranks amber on a tie.
 */
export function highlightLine(
  line: string,
  green: string[],
  amber: string[],
): HighlightSegment[] {
  const spans = [
    ...collectTermSpans(line, amber, "amber"),
    ...collectTermSpans(line, green, "green"),
  ];
  if (spans.length === 0) return [{ text: line, tone: null }];

  spans.sort(
    (a, b) => a.start - b.start || b.end - a.end || TONE_RANK[a.tone] - TONE_RANK[b.tone],
  );

  const chosen: Span[] = [];
  let cursor = 0;
  for (const span of spans) {
    if (span.start < cursor) continue;
    chosen.push(span);
    cursor = span.end;
  }

  const segments: HighlightSegment[] = [];
  let position = 0;
  for (const span of chosen) {
    if (span.start > position) {
      segments.push({ text: line.slice(position, span.start), tone: null });
    }
    segments.push({ text: line.slice(span.start, span.end), tone: span.tone });
    position = span.end;
  }
  if (position < line.length) {
    segments.push({ text: line.slice(position), tone: null });
  }
  return segments;
}
