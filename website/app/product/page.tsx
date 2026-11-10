import type { Metadata } from "next";
import Link from "next/link";
import { Lifecycle } from "@/components/Diagrams";
import EarnTrial from "@/components/EarnTrial";
import RouteSimulator from "@/components/RouteSimulator";

export const metadata: Metadata = { title: "Product", description: "How Chamber decides where each request goes, and how a local model earns its work." };

export default function Product() {
  return (
    <div className="wrap stack">
      <header className="intro">
        <h1 className="page-title">Every request goes to the right place.</h1>
        <p className="lede">A small decision model runs on the device and reads each request first. It decides whether the text is privileged, whether a person has to decide, and what kind of work it is.</p>
      </header>

      <section className="section">
        <div className="intro">
          <h2>Follow a request.</h2>
          <p className="prose">Pick an example and watch the decision. Then turn on &quot;earned&quot; to see what changes once the local model has proved itself.</p>
        </div>
        <RouteSimulator />
        <p className="small">A simulation of Chamber&apos;s routing rules, using example requests. In the app, the decision model makes these calls on the real text.</p>
      </section>

      <section className="section">
        <h2>Five paths.</h2>
        <div className="rows">
          <div className="row3"><span><span className="pill on">On device</span></span><b>Privileged work</b><span className="muted">Attached client files, marked text and anything the decision model flags as privileged are answered on your machine. Text that can&apos;t be read stays too.</span></div>
          <div className="row3"><span><span className="pill test">Testing</span></span><b>New public work</b><span className="muted">A local model and the cloud both answer. The lawyer picks between two unlabeled answers.</span></div>
          <div className="row3"><span><span className="pill on">On device</span></span><b>Work that has earned it</b><span className="muted">Once the local model has enough good answers, that task moves on device and the cloud stops being called.</span></div>
          <div className="row3"><span><span className="pill cloud">Cloud</span></span><b>Public work it can&apos;t do yet</b><span className="muted">Client names and private details are masked first, and restored on the device.</span></div>
          <div className="row3"><span><span className="pill human">Human</span></span><b>Legal decisions</b><span className="muted">No AI answers. It goes to the person&apos;s manager.</span></div>
        </div>
      </section>

      <section className="section">
        <div className="intro">
          <h2>Work is earned, and it can be lost.</h2>
          <p className="prose">Each person, task and model keeps its own record. A task on device keeps getting spot checks, and it goes back to testing if the local model starts getting it wrong.</p>
        </div>
        <Lifecycle />
      </section>

      <section className="two">
        <div className="intro">
          <h2>Judged by lawyers, not by a benchmark.</h2>
          <p className="prose">The people doing the work decide what&apos;s good enough. They see two unlabeled answers, so they can&apos;t favor either model.</p>
        </div>
        <EarnTrial />
      </section>

      <section className="section">
        <h2>Choose your models.</h2>
        <div className="grid2">
          <div><b>Liquid LFM3-1.7B</b><span>The default model for work on the device.</span></div>
          <div><b>Liquid d1-2B</b><span>The decision model that reads every request. It always runs on the device.</span></div>
          <div><b>Any chat model in Ollama</b><span>Install one and it appears in the menu, with its own separate record.</span></div>
          <div><b>Claude for public work</b><span>Pick it to send public work straight to the cloud, masked. Privileged work still stays on device.</span></div>
        </div>
        <p className="small">Prompts are tuned for LFM3, so other models may score lower.</p>
        <div className="actions"><Link className="btn quiet" href="/security/">See what can leave the device</Link></div>
      </section>
    </div>
  );
}
