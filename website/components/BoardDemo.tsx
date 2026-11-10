"use client";

import { useMemo, useState } from "react";

type Row = { person: string; task: string; dest: string; n: number };
const ROUTES = [{ id: "device", word: "On device" }, { id: "cloud", word: "Cloud, names masked" }, { id: "human", word: "Human" }];
const SAMPLE: Row[] = [
  { person: "Maya", task: "Public lookup", dest: "device", n: 6 }, { person: "Maya", task: "Public fee or limit", dest: "device", n: 5 },
  { person: "Maya", task: "Research", dest: "cloud", n: 4 }, { person: "Maya", task: "Summarize a deposition", dest: "device", n: 4 }, { person: "Maya", task: "Advice", dest: "human", n: 1 },
  { person: "Daniel", task: "Public lookup", dest: "device", n: 4 }, { person: "Daniel", task: "Public fee or limit", dest: "cloud", n: 4 },
  { person: "Daniel", task: "Research", dest: "cloud", n: 3 }, { person: "Daniel", task: "Summarize a will", dest: "device", n: 3 }, { person: "Daniel", task: "Advice", dest: "human", n: 1 },
];
const W = 900, H = 340, X0 = 190, X1 = W - 210, GAP = 14, BAR = 5;
const paint: Record<string, { fill: string; opacity: number }> = { device: { fill: "#000", opacity: 0.2 }, cloud: { fill: "#9b9b9b", opacity: 0.3 }, human: { fill: "url(#site-hatch)", opacity: 0.45 } };

export default function BoardDemo() {
  const [by, setBy] = useState<"person" | "task">("person");
  const [hot, setHot] = useState<string | null>(null);
  const [sel, setSel] = useState<{ side: string; dest: string } | null>({ side: "Daniel", dest: "cloud" });

  const field = by;
  const shape = useMemo(() => {
    const left = [...new Set(SAMPLE.map((r) => r[field]))];
    const sum = (rows: Row[]) => rows.reduce((a, r) => a + r.n, 0);
    const total = sum(SAMPLE);
    const unit = (H - 20 - GAP * Math.max(left.length - 1, ROUTES.length - 1)) / total;
    const leftH = left.map((l) => sum(SAMPLE.filter((r) => r[field] === l)) * unit);
    const totals = ROUTES.map((d) => sum(SAMPLE.filter((r) => r.dest === d.id)));
    const rightH = totals.map((t) => t * unit);
    const stack = (hs: number[]) => { let y = (H - hs.reduce((a, b) => a + b, 0) - GAP * (hs.length - 1)) / 2; return hs.map((h) => { const at = y; y += h + GAP; return at; }); };
    const leftY = stack(leftH), rightY = stack(rightH), cursor = [...rightY];
    const bands: { key: string; side: string; dest: string; n: number; d: string }[] = [];
    left.forEach((l, i) => {
      let y = leftY[i];
      ROUTES.forEach((route, r) => {
        const n = sum(SAMPLE.filter((x) => x[field] === l && x.dest === route.id));
        if (!n) return;
        const h = n * unit, a = y, b = cursor[r], m = (X0 + X1) / 2;
        y += h; cursor[r] += h;
        bands.push({ key: `${l}|${route.id}`, side: l, dest: route.id, n, d: `M${X0} ${a}C${m} ${a} ${m} ${b} ${X1} ${b}L${X1} ${b + h}C${m} ${b + h} ${m} ${a + h} ${X0} ${a + h}Z` });
      });
    });
    return { left, leftH, leftY, rightH, rightY, totals, bands };
  }, [field]);

  const opened = sel ? SAMPLE.filter((r) => r[field] === sel.side && r.dest === sel.dest) : [];
  const list = opened.flatMap((r) => Array.from({ length: r.n }, (_, i) => ({ ...r, id: `${r.person}-${r.task}-${i}` })));
  const word = (id: string) => ROUTES.find((r) => r.id === id)!.word.split(",")[0];

  return (
    <div className="section" style={{ gap: 16 }}>
      <div className="sechead">
        <span className="sample">Sample data. Click a band to open the requests behind it.</span>
        <div className="tabs">
          <button type="button" className={by === "person" ? "on" : ""} onClick={() => { setBy("person"); setSel({ side: "Daniel", dest: "cloud" }); }}>By person</button>
          <button type="button" className={by === "task" ? "on" : ""} onClick={() => { setBy("task"); setSel({ side: "Public fee or limit", dest: "cloud" }); }}>By task</button>
        </div>
      </div>
      <div className="scrollx">
        <svg className={`board${hot ? " dim" : ""}`} viewBox={`0 0 ${W} ${H}`} role="group" aria-label="Where work went, sample data">
          <defs><pattern id="site-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#fff" /><rect width="2" height="6" fill="#000" /></pattern></defs>
          {shape.bands.map((b) => {
            const isSel = sel?.side === b.side && sel.dest === b.dest;
            const open = () => setSel({ side: b.side, dest: b.dest });
            return (
              <g key={b.key} className={`band${hot === b.key ? " hot" : ""}${isSel ? " sel" : ""}`} tabIndex={0} role="button" aria-label={`${b.side}: ${b.n} requests to ${word(b.dest)}`} aria-pressed={isSel}
                onMouseEnter={() => setHot(b.key)} onMouseLeave={() => setHot(null)} onClick={open}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } }}>
                <path d={b.d} fill={paint[b.dest].fill} fillOpacity={isSel ? paint[b.dest].opacity + 0.12 : paint[b.dest].opacity} />
              </g>
            );
          })}
          {shape.left.map((l, i) => (
            <g key={l}>
              <rect x={X0 - BAR} y={shape.leftY[i]} width={BAR} height={shape.leftH[i]} rx={2} fill="#000" />
              <text x={X0 - 14} y={shape.leftY[i] + shape.leftH[i] / 2 + 5} textAnchor="end">{l}</text>
            </g>
          ))}
          {ROUTES.map((r, i) => (
            <g key={r.id}>
              <rect x={X1} y={shape.rightY[i]} width={BAR} height={shape.rightH[i]} rx={2} fill="#000" />
              <text x={X1 + 16} y={shape.rightY[i] + shape.rightH[i] / 2 + 6}><tspan fontSize="20" fontWeight="300">{shape.totals[i]}</tspan><tspan dx="7">{r.word}</tspan></text>
            </g>
          ))}
        </svg>
      </div>
      {sel && (
        <div role="status" className="scrollx">
          <table className="reqlist">
            <thead><tr><th>Task</th><th>Who</th><th>Where</th></tr></thead>
            <tbody>{list.slice(0, 5).map((r) => <tr key={r.id}><td>{r.task}</td><td>{r.person}</td><td><span className={`pill ${r.dest === "device" ? "on" : r.dest === "cloud" ? "cloud" : "human"}`}>{word(r.dest)}</span></td></tr>)}</tbody>
          </table>
          {list.length > 5 && <p className="sample" style={{ marginTop: 8 }}>and {list.length - 5} more</p>}
        </div>
      )}
    </div>
  );
}
