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
