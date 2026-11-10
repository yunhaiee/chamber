"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";

/** Adds "in" once scrolled into view, which draws the diagram's lines. */
export function Drawn({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const watcher = new IntersectionObserver(([entry]) => { if (entry.isIntersecting) { setSeen(true); watcher.disconnect(); } }, { threshold: 0.25 });
    watcher.observe(el);
    return () => watcher.disconnect();
  }, []);
  return <div ref={ref} className={`scrollx drawn${seen ? " in" : ""}`}>{children}</div>;
}

/** Shows its final value without scripts, and counts up when first seen. */
export function CountUp({ value, decimals = 0, suffix = "" }: { value: number; decimals?: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [shown, setShown] = useState(value);
  useEffect(() => {
    const el = ref.current;
    if (!el || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let frame = 0;
    const watcher = new IntersectionObserver(([entry]) => {
      if (!entry.isIntersecting) return;
      watcher.disconnect();
      const start = performance.now();
      const step = (now: number) => {
        const p = Math.min((now - start) / 900, 1);
        setShown(value * (1 - Math.pow(1 - p, 3)));
        if (p < 1) frame = requestAnimationFrame(step);
      };
      frame = requestAnimationFrame(step);
    }, { threshold: 0.4 });
    watcher.observe(el);
    return () => { watcher.disconnect(); cancelAnimationFrame(frame); };
  }, [value]);
  return <span ref={ref}>{shown.toFixed(decimals)}{suffix}</span>;
}

export function Code({ children }: { children: string }) {
  const [said, setSaid] = useState("Copy");
  async function copy() {
    try { await navigator.clipboard.writeText(children); setSaid("Copied"); }
    catch { setSaid("Press ⌘C"); }
    setTimeout(() => setSaid("Copy"), 1600);
  }
  return <div className="code">{children}<button type="button" className="copy" onClick={copy}>{said}</button></div>;
}
