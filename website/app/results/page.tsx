import type { Metadata } from "next";
import { CountUp } from "@/components/Bits";
import { GITHUB } from "@/lib/site";

export const metadata: Metadata = { title: "Results", description: "What Chamber has measured so far, and what those numbers don't show." };

export default function Results() {
  return (
    <div className="wrap stack">
      <header className="intro">
        <h1 className="page-title">Measured, on a laptop.</h1>
        <p className="lede">These numbers come from running the system on a Mac laptop with a fictional firm. They show what the system did in those runs.</p>
      </header>

      <section className="numbers" aria-label="Results">
        <div><strong><CountUp value={12} /></strong><p><b>Cloud calls avoided</b> in one simulated firm day, because the work had already moved on device.</p></div>
        <div><strong><CountUp value={1.0} decimals={1} suffix="s" /> / <CountUp value={2.6} decimals={1} suffix="s" /></strong><p><b>Median answer time</b> on device and in the cloud, across 23 requests both answered.</p></div>
        <div><strong><CountUp value={144} /> of 144</strong><p><b>Right kind of work.</b> d1 picked correctly on all 144 test requests, at about 0.4 seconds each.</p></div>
        <div><strong><CountUp value={0} /></strong><p><b>Privileged test requests scored as public</b> at the 0.30 threshold. Of 24 public questions, 5 were held back as false alarms.</p></div>
        <div><strong><CountUp value={136} /></strong><p><b>Attack cases</b> we wrote. After one fix, none got privileged text to the cloud.</p></div>
      </section>

      <section className="section">
        <h2>What these numbers don&apos;t show.</h2>
        <div className="grid2">
          <div><b>A fictional firm</b><span>The firm, matters and documents in these tests are synthetic. Nobody has run it at a real firm yet.</span></div>
          <div><b>One laptop</b><span>It has run on a Mac laptop and hasn&apos;t been tested on dedicated AI hardware.</span></div>
          <div><b>A short bar</b><span>Three good answers keeps the demo short. A real firm would need far more.</span></div>
          <div><b>Our own attacks</b><span>We wrote the attack cases ourselves, so they&apos;re a test and not a guarantee.</span></div>
        </div>
        <p className="small">You can run the attack cases yourself with <code>scripts/redteam_d1.py</code> in the <a className="textlink" href={GITHUB}>repository</a>.</p>
      </section>
    </div>
  );
}
