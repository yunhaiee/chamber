"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import HeroFlow from "@/components/HeroFlow";
import { GITHUB } from "@/lib/site";

const WORDS: Record<string, string> = { local: "on device?", mask: "to the cloud?", human: "to a human?" };

export default function Hero() {
  const [word, setWord] = useState(WORDS.local);
  const [wipe, setWipe] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  // The bar covers the old word, the word changes behind it, then the bar clears.
  const onRoute = useCallback((dest: string) => {
    setWipe((n) => n + 1);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setWord(WORDS[dest]), 340);
  }, []);
  useEffect(() => () => clearTimeout(timer.current), []);

  return (
    <header className="section hero">
      <h1 className="rotating" aria-label="Should this go on device, to the cloud, or to a human?">
        <span aria-hidden="true">Should this go</span>
        <span aria-hidden="true"><span key={wipe} className={`swap${wipe ? " wipe" : ""}`}>{word}</span></span>
      </h1>
      <div className="hero-row">
        <p className="lede">Don&apos;t decide what runs locally. Let the local model prove it. Chamber moves the work a small model handles well onto your own machine, and keeps privileged text from leaving.</p>
        <div className="actions">
          <Link className="btn main" href="/start/">Get started</Link>
          <a className="btn quiet" href={GITHUB}>View on GitHub</a>
        </div>
      </div>
      <HeroFlow onRoute={onRoute} />
    </header>
  );
}
