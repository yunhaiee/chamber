"use client";

import { Fragment, useEffect, useRef, useState } from "react";

type Node = { id: string; label: string; sub?: string; x: number; y: number; kind: string };
type Scene = { text: string; masked?: string; note: string; path: string[] };

const SCENES: Scene[] = [
  { text: "Summarize the deposition", note: "A client file is attached, so the work stays on device.", path: ["req", "d1", "local"] },
  { text: "Can Harlow Orchards remove the case?", masked: "Can [CLIENT_1] remove the case?", note: "A public question goes to the cloud with the client's name masked.", path: ["req", "d1", "mask", "cloud"] },
  { text: "What's the docket date?", note: "This task has earned its place, so the cloud isn't called.", path: ["req", "d1", "local"] },
  { text: "Should we accept the offer?", note: "A legal decision goes to a person. No AI answers it.", path: ["req", "d1", "human"] },
];
const EDGES = [["req", "d1"], ["d1", "human"], ["d1", "local"], ["d1", "mask"], ["mask", "cloud"]];

const WIDE = {
  w: 1120, h: 340, nw: 150, nh: 60, tall: false,
  nodes: [
    { id: "req", label: "A request", x: 80, y: 170, kind: "plain" },
    { id: "d1", label: "d1 reads it", sub: "on your device", x: 300, y: 170, kind: "ask" },
    { id: "human", label: "Human", sub: "no AI answers", x: 610, y: 50, kind: "human" },
    { id: "local", label: "On device", sub: "a local model answers", x: 610, y: 170, kind: "solid" },
    { id: "mask", label: "Mask names", sub: "key stays here", x: 610, y: 290, kind: "plain" },
    { id: "cloud", label: "Cloud", sub: "sees only tags", x: 1040, y: 290, kind: "cloud" },
  ] as Node[],
  wall: "M825 14V332",
  sides: [{ text: "Your device", x: 811, y: 10, right: true }, { text: "The cloud", x: 839, y: 10, right: false }],
};
const TALL = {
  w: 400, h: 680, nw: 120, nh: 62, tall: true,
  nodes: [
    { id: "req", label: "A request", x: 200, y: 40, kind: "plain" },
    { id: "d1", label: "d1 reads it", sub: "on your device", x: 200, y: 170, kind: "ask" },
    { id: "human", label: "Human", sub: "no AI answers", x: 66, y: 340, kind: "human" },
    { id: "local", label: "On device", sub: "local model", x: 200, y: 340, kind: "solid" },
    { id: "mask", label: "Mask names", sub: "key stays here", x: 334, y: 340, kind: "plain" },
    { id: "cloud", label: "Cloud", sub: "sees only tags", x: 334, y: 640, kind: "cloud" },
  ] as Node[],
  wall: "M6 500H394",
  sides: [{ text: "Your device", x: 8, y: 470, right: false }, { text: "The cloud", x: 8, y: 512, right: false }],
};

export default function HeroFlow({ onRoute }: { onRoute?: (dest: string) => void }) {
  const [tall, setTall] = useState(false);
  const layout = tall ? TALL : WIDE;
  const stage = useRef<HTMLDivElement>(null);
  const chip = useRef<HTMLDivElement>(null);
  const paths = useRef<Record<string, SVGPathElement | null>>({});
  const [live, setLive] = useState<{ text: string; edges: string[]; node: string; note: string; show: boolean; arrived?: boolean }>({ text: "", edges: [], node: "", note: SCENES[0].note, show: false });

  useEffect(() => {
    const narrow = matchMedia("(max-width: 700px)");
    const update = () => setTall(narrow.matches);
    update();
    narrow.addEventListener("change", update);
    return () => narrow.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let stopped = false;
    let frame = 0;
    const timers: ReturnType<typeof setTimeout>[] = [];
    const wait = (ms: number) => new Promise<void>((done) => timers.push(setTimeout(done, ms)));
    const place = (x: number, y: number) => {
      if (!chip.current) return;
      chip.current.style.left = `${(x / layout.w) * 100}%`;
      chip.current.style.top = `${(y / layout.h) * 100}%`;
    };
    const travel = (el: SVGPathElement, ms: number) =>
      new Promise<void>((done) => {
        const length = el.getTotalLength();
        const start = performance.now();
        const step = (now: number) => {
          if (stopped) return;
          const p = Math.min((now - start) / ms, 1);
          const eased = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
          const point = el.getPointAtLength(length * eased);
          place(point.x, point.y);
          if (p < 1) frame = requestAnimationFrame(step);
          else done();
        };
        frame = requestAnimationFrame(step);
      });

    (async () => {
      let index = 0;
      await wait(500);
      while (!stopped) {
        const scene = SCENES[index++ % SCENES.length];
        const first = layout.nodes[0];
        place(first.x, first.y);
        const done: string[] = [];
        setLive({ text: scene.text, edges: [], node: "", note: scene.note, show: true });
        await wait(550);
        for (let i = 0; i < scene.path.length - 1 && !stopped; i++) {
          const key = `${scene.path[i]}-${scene.path[i + 1]}`;
          done.push(key);
          const text = scene.masked && scene.path[i] === "mask" ? scene.masked : scene.text;
          setLive({ text, edges: [...done], node: scene.path[i], note: scene.note, show: true });
          if (scene.path[i] === "d1") onRoute?.(scene.path[i + 1]);
          const el = paths.current[key];
          if (el) await travel(el, 950);
        }
        const last = scene.path[scene.path.length - 1];
        setLive({ text: scene.masked ?? scene.text, edges: [...done], node: last, note: scene.note, show: true, arrived: true });
        await wait(1500);
        setLive({ text: scene.masked ?? scene.text, edges: [], node: "", note: scene.note, show: false, arrived: true });
        await wait(450);
      }
    })();

    return () => {
      stopped = true;
      cancelAnimationFrame(frame);
      timers.forEach(clearTimeout);
    };
  }, [layout, onRoute]);

  const at = Object.fromEntries(layout.nodes.map((n) => [n.id, n]));
  const edgePath = (a: Node, b: Node) => {
    if (layout.tall) {
      const y1 = a.y + layout.nh / 2, y2 = b.y - layout.nh / 2, mid = (y1 + y2) / 2;
      return `M${a.x} ${y1}C${a.x} ${mid} ${b.x} ${mid} ${b.x} ${y2}`;
    }
    const x1 = a.x + layout.nw / 2, x2 = b.x - layout.nw / 2, mid = (x1 + x2) / 2;
    return `M${x1} ${a.y}C${mid} ${a.y} ${mid} ${b.y} ${x2} ${b.y}`;
  };
  const pieces = live.text.split(/(\[CLIENT_1\])/);

  return (
    <figure className="fig">
      <div ref={stage} className="flow-stage" style={{ aspectRatio: `${layout.w} / ${layout.h}` }} aria-hidden="true">
        <svg viewBox={`0 0 ${layout.w} ${layout.h}`}>
          <path className="flow-wall" d={layout.wall} />
          {EDGES.map(([a, b]) => {
            const key = `${a}-${b}`;
            return <path key={key} ref={(el) => { paths.current[key] = el; }} className={`flow-edge${live.edges.includes(key) ? " live" : ""}`} d={edgePath(at[a], at[b])} />;
          })}
        </svg>
        {layout.sides.map((side) => (
          <span key={side.text} className="flow-side" style={{ top: `${(side.y / layout.h) * 100}%`, ...(side.right ? { right: `${100 - (side.x / layout.w) * 100}%` } : { left: `${(side.x / layout.w) * 100}%` }) }}>{side.text}</span>
        ))}
        {layout.nodes.map((n) => (
          <div key={n.id} className={`flow-node ${n.kind}${live.node === n.id ? " hit" : ""}`} style={{ left: `${(n.x / layout.w) * 100}%`, top: `${(n.y / layout.h) * 100}%`, width: `${(layout.nw / layout.w) * 100}%`, height: `${(layout.nh / layout.h) * 100}%` }}>
            <b>{n.label}</b>{n.sub && <small>{n.sub}</small>}
          </div>
        ))}
        <div ref={chip} className={`flow-chip${live.show ? " show" : ""}${live.arrived ? " arrived" : ""}`}>
          {pieces.map((piece, i) => <Fragment key={i}>{piece === "[CLIENT_1]" ? <span className="bar">{piece}</span> : piece}</Fragment>)}
        </div>
      </div>
      <figcaption>
        <span className="flow-note">{live.note}</span>
      </figcaption>
    </figure>
  );
}
