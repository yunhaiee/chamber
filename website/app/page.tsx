import Link from "next/link";
import EarnTrial from "@/components/EarnTrial";
import Hero from "@/components/Hero";
import MaskPlayground from "@/components/MaskPlayground";
import { GITHUB } from "@/lib/site";

export default function Home() {
  return (
    <div className="wrap stack">
      <Hero />

      <section className="intro">
        <h2>Nobody knows where the line is.</h2>
        <p className="prose">Firms want AI on their own machines because client files can&apos;t go to the cloud. A small local model can&apos;t do everything, so they need a hybrid. But what a small model can really do for a lawyer differs by firm and by role, and a fixed rule can only guess. Chamber measures it instead.</p>
      </section>

      <section className="section" aria-labelledby="why">
        <div className="intro">
          <h2 id="why">Why firms hold back.</h2>
          <p className="prose">Lawyers have taken up AI faster than their firms have. What holds firms back is what Chamber is built around: client information that stays private, answers they can trust, and a clear view of how AI is used.</p>
        </div>
        <div className="numbers">
          <div><strong>69%</strong><p><b>of legal professionals use AI tools for work</b>, up from 31% a year earlier.</p></div>
          <div><strong>46%</strong><p><b>of firms have put AI tools in place.</b> Most lawyers are already ahead of their firm.</p></div>
          <div><strong>46%</strong><p><b>call data security a significant barrier</b>, and 39% cite privilege concerns. So privileged text stays on device, and cloud text is masked first.</p></div>
          <div><strong>39%</strong><p><b>cite lack of trust in AI&apos;s answers.</b> So in Chamber, a local model has to prove each task before any work moves to it.</p></div>
          <div><strong>43%</strong><p><b>have no AI policy and no plans for one.</b> So managers keep one masking list for everyone, and the Board shows where all the work went.</p></div>
        </div>
        <p className="prose">The ethics rules point the same way. The ABA&apos;s 2024 opinion on generative AI says a lawyer generally needs the client&apos;s informed consent before putting client information into a self-learning AI tool, and a boilerplate clause in the engagement letter isn&apos;t enough.</p>
        <p className="small">Sources: <a className="textlink" href="https://www.8am.com/blog/ai-adoption-law-firms-2026-legal-industry-report/">8am 2026 Legal Industry Report</a>, more than 1,300 legal professionals surveyed in September and October 2025, most at solo and small firms. The barrier and policy figures are as reported by <a className="textlink" href="https://www.lawnext.com/2026/03/ai-adoption-among-legal-professionals-has-more-than-doubled-in-a-year-new-8am-report-finds-but-firms-lag-far-behind-individual-practitioners.html">LawNext</a> (March 2026). ABA Formal Opinion 512 (July 2024), summarized by the <a className="textlink" href="https://www.americanbar.org/groups/litigation/resources/newsletters/ethics-professionalism/generative-ai-lawyers-part-2-maintaining-confidentiality/">ABA Litigation Section</a>.</p>
      </section>

      <section className="section">
        <div className="link-row">
          <Link href="/product/"><h3>It earns the work</h3><span>Local and cloud models answer side by side until the local model has proved itself, per person, per task, per model.</span><em>See how it decides</em></Link>
          <Link href="/security/"><h3>It protects what matters</h3><span>Privileged text stays on device. Anything that goes to the cloud has client names and private details masked first.</span><em>See what can leave</em></Link>
          <Link href="/firms/"><h3>It fits how a firm is run</h3><span>A head of firm, managers and employees, one masking list for everyone, and a clear view of where all work went.</span><em>See it for firms</em></Link>
        </div>
      </section>

      <section className="two">
        <div className="intro">
          <h2>Be the lawyer. Judge the answers.</h2>
          <p className="prose">Two models answer and you can&apos;t tell which is which. Give the local model three good answers in a row and watch the task move on device.</p>
        </div>
        <EarnTrial />
      </section>

      <section className="section">
        <div className="intro">
          <h2>Try the masking yourself.</h2>
          <p className="prose">Edit the text, add a name to the firm&apos;s list, or upload a file, and see exactly what would reach the cloud.</p>
        </div>
        <MaskPlayground />
      </section>

      <section className="section">
        <div className="intro">
          <h2>Same task. Different result.</h2>
          <p className="prose">Two lawyers ran the same kind of task, a public fee or limit. Nobody wrote a rule that split them. The results did.</p>
        </div>
        <div className="rows">
          <div className="row3"><b>Maya</b><span className="muted">Checks a claim against one limit. The local model gets it right.</span><span><span className="pill on">On device</span></span></div>
          <div className="row3"><b>Daniel</b><span className="muted">Works out a fee across three tiers. The local model gets the math wrong.</span><span><span className="pill cloud">Cloud</span></span></div>
        </div>
      </section>

      <section className="cta">
        <h2>Run it on your own machine.</h2>
        <p className="prose">Chamber is open source under the MIT license. It needs Python, Ollama and llama.cpp.</p>
        <div className="actions">
          <Link className="btn main" href="/start/">Get started</Link>
          <a className="btn quiet" href={GITHUB}>View on GitHub</a>
        </div>
      </section>
    </div>
  );
}
