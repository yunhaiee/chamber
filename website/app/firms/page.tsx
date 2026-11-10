import type { Metadata } from "next";
import Link from "next/link";
import BoardDemo from "@/components/BoardDemo";
import MaskPlayground from "@/components/MaskPlayground";
import OrgChart from "@/components/OrgChart";

export const metadata: Metadata = { title: "For firms", description: "Roles, a firm-wide masking list, and a clear view of where all work went." };

export default function Firms() {
  return (
    <div className="wrap stack">
      <header className="intro">
        <h1 className="page-title">Built for how a firm is run.</h1>
        <p className="lede">One shared device, a clear chain of responsibility, and a record of where every request went.</p>
      </header>

      <section className="section">
        <div className="intro">
          <h2>Everyone has a place.</h2>
          <p className="prose">The head of firm sets up the firm and adds people. Select a role to see what it can do.</p>
        </div>
        <OrgChart />
      </section>

      <section className="section">
        <div className="intro">
          <h2>See what went where.</h2>
          <p className="prose">The Board shows where all work went, by person or by task. Click any band to open the exact requests behind it.</p>
        </div>
        <BoardDemo />
      </section>

      <section className="section">
        <div className="intro">
          <h2>One masking list, enforced on everyone.</h2>
          <p className="prose">Managers type in names and private details or upload a .txt or .csv of them. Every lawyer&apos;s cloud text is masked against the same list.</p>
        </div>
        <MaskPlayground />
      </section>

      <section className="section">
        <h2>Runs where your files are.</h2>
        <div className="grid2">
          <div><b>Your database stays with you</b><span>People, requests and masking lists live in a SQLite file on the device. There&apos;s no hosted database.</span></div>
          <div><b>A key that isn&apos;t in a file</b><span>On a Mac, the cloud key is kept in the system Keychain.</span></div>
          <div><b>Works when the connection drops</b><span>On-device work continues. Cloud work waits and runs when the connection returns.</span></div>
          <div><b>Open source</b><span>MIT licensed, so your firm can read every line.</span></div>
        </div>
        <p className="small">Still to come: adding matters and uploading client documents, and letting people change their own password.</p>
        <div className="actions"><Link className="btn main" href="/start/">Get started</Link></div>
      </section>
    </div>
  );
}
