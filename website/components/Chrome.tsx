"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { GITHUB, NAV } from "@/lib/site";

export function Logo() {
  return (
    <svg viewBox="0 0 64 64" aria-hidden="true">
      <path fill="currentColor" fillRule="evenodd" d="M14 60H50A4 4 0 0 0 54 56V26A22 22 0 0 0 10 26V56A4 4 0 0 0 14 60ZM22 60V36A10 10 0 0 1 42 36V60Z" />
    </svg>
  );
}

export function Header() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [path]);
  return (
    <header className="head">
      <div className="wrap" style={{ position: "relative" }}>
        <Link className="brand" href="/"><Logo />Chamber</Link>
        <button className="menu" type="button" aria-expanded={open} aria-controls="site-nav" onClick={() => setOpen(!open)}>{open ? "Close" : "Menu"}</button>
        <nav id="site-nav" className={`navlinks${open ? " open" : ""}`} aria-label="Main">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} className={path === item.href ? "active" : ""} aria-current={path === item.href ? "page" : undefined}>{item.label}</Link>
          ))}
          <a href={GITHUB}>GitHub</a>
          <Link className="btn main" href="/start/">Get started</Link>
        </nav>
      </div>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="foot">
      <div className="wrap">
        <div>
          <Link className="brand" href="/"><Logo />Chamber</Link>
          <p>An open-source project under the MIT license, first built for the AGI House Personal Agent to Real-World Deployment Build Day. It has run on a Mac laptop with a fictional firm. It isn&apos;t legal advice and doesn&apos;t replace a firm&apos;s ethics obligations.</p>
        </div>
        <nav aria-label="Pages">
          {NAV.map((item) => <Link key={item.href} href={item.href}>{item.label}</Link>)}
          <Link href="/start/">Get started</Link>
        </nav>
        <nav aria-label="Project">
          <a href={GITHUB}>GitHub</a>
          <a href={`${GITHUB}/blob/main/LICENSE`}>MIT license</a>
        </nav>
      </div>
    </footer>
  );
}
