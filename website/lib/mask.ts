// A browser copy of the patterns Chamber's masking step uses, so visitors can try it. Nothing typed here is sent anywhere.

export type Term = { value: string; tag: string };
export type Part = { text: string; tagged: boolean };

const PATTERNS: [RegExp, string][] = [
  [/\b(?:sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,})/g, "KEY"],
  [/(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)/g, "ID"],
  [/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, "EMAIL"],
  [/(?<![\d-])(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)/g, "PHONE"],
  [/\bCGC-\d{2}-\d{6}\b/g, "CASE"],
];
const CARD = /(?<![\d-])\d(?:[ -]?\d){12,18}(?!\d)/g;

function luhn(digits: string) {
  let total = 0;
  [...digits].reverse().forEach((ch, i) => {
    let n = Number(ch);
    if (i % 2) n = n > 4 ? n * 2 - 9 : n * 2;
    total += n;
  });
  return total % 10 === 0;
}

const escapeRe = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/ /g, "\\s+");

export function tagFor(value: string) {
  if (/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(value)) return "EMAIL";
  if (/^\p{Lu}[\p{L}.'’-]*(?: \p{L}[\p{L}.'’-]*){0,3}$/u.test(value)) return "PERSON";
  return "TERM";
}

export function usable(value: string) {
  return value.length >= 2 && value.length <= 200 && !(/^\d+$/.test(value) && value.length < 5);
}

/** Entries from a .txt (one per line) or .csv (every cell, header row skipped). */
export function parseList(filename: string, text: string) {
  const clean = (s: string) => s.trim().replace(/\s+/g, " ");
  if (filename.toLowerCase().endsWith(".txt")) return text.split(/\r?\n/).map(clean).filter(Boolean);
  const header = new Set(["name", "names", "full name", "first name", "last name", "email", "e-mail", "phone", "address", "ssn", "client", "party", "id", "notes"]);
  const rows = text.split(/\r?\n/).map((line) => line.split(",").map((c) => clean(c.replace(/^"|"$/g, ""))).filter(Boolean)).filter((r) => r.length);
  if (rows[0]?.some((c) => header.has(c.toLowerCase())) && !rows[0].some((c) => /[@\d]/.test(c))) rows.shift();
  return rows.flat();
}

export function mask(text: string, terms: Term[]) {
  const spans: [number, number, string][] = [];
  for (const [pattern, tag] of PATTERNS) for (const m of text.matchAll(pattern)) spans.push([m.index, m.index + m[0].length, tag]);
  for (const m of text.matchAll(CARD)) {
    const digits = m[0].replace(/\D/g, "");
    if (digits.length >= 13 && digits.length <= 19 && luhn(digits)) spans.push([m.index, m.index + m[0].length, "CARD"]);
  }
  for (const term of terms) {
    for (const m of text.matchAll(new RegExp(`(?<![\\p{L}\\p{N}_])${escapeRe(term.value)}(?![\\p{L}\\p{N}_])`, "giu"))) {
      spans.push([m.index, m.index + m[0].length, term.tag]);
    }
  }
  spans.sort((a, b) => a[0] - b[0] || b[1] - b[0] - (a[1] - a[0]));

  const parts: Part[] = [];
  const counters: Record<string, number> = {};
  const byValue = new Map<string, string>();
  let cursor = 0;
  for (const [start, end, tag] of spans) {
    if (start < cursor) continue;
    if (start > cursor) parts.push({ text: text.slice(cursor, start), tagged: false });
    const value = text.slice(start, end);
    if (!byValue.has(value)) {
      counters[tag] = (counters[tag] || 0) + 1;
      byValue.set(value, `[${tag}_${counters[tag]}]`);
    }
    parts.push({ text: byValue.get(value)!, tagged: true });
    cursor = end;
  }
  if (cursor < text.length) parts.push({ text: text.slice(cursor), tagged: false });
  return { parts, key: [...byValue.entries()].map(([value, tag]) => ({ tag, value })) };
}
