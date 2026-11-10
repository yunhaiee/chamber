import type { Metadata } from "next";
import { Boundary } from "@/components/Diagrams";
import MaskPlayground from "@/components/MaskPlayground";

export const metadata: Metadata = { title: "Security", description: "What can leave the device, what can't, and how Chamber enforces it." };

const ATTACKS = [
  ["Telling the model to ignore its instructions", "Text inside a document that orders the model to send it to the cloud."],
  ["Fake system notes and fake approvals", "Claims that a system or a managing partner has cleared the text for sending."],
  ["Claiming the text is public", "Privileged content labeled as a public record."],
  ["Burying it in public text", "A privileged passage hidden inside an ordinary research question."],
  ["Encoded text", "Base64, hex, rot13, reversed and spaced-out text. d1 can't read these, so a fixed rule keeps unreadable text on device."],
];

export default function Security() {
  return (
    <div className="wrap stack">
      <header className="intro">
        <h1 className="page-title">Privileged text stays on your machine.</h1>
        <p className="lede">Chamber draws a boundary around the device. Only masked public text can cross it, and every crossing goes through one step that can be audited.</p>
      </header>

      <section className="section">
        <h2>What can leave, and what can&apos;t.</h2>
        <Boundary />
      </section>

      <section className="section">
        <div className="intro">
          <h2>See what the cloud would get.</h2>
          <p className="prose">Names on the firm&apos;s list, emails, phone numbers, case numbers, government IDs, card numbers and API keys are replaced with tags. The key never leaves.</p>
        </div>
        <MaskPlayground />
      </section>

      <section className="section">
        <h2>Fixed rules back up the model.</h2>
        <div className="grid2">
          <div><b>Files stay</b><span>An attached client file stays on device, whatever d1 scores.</span></div>
          <div><b>If in doubt, keep it</b><span>If d1 is unavailable or the text can&apos;t be read, the work stays on device.</span></div>
          <div><b>No masking, no call</b><span>If the masking step fails, the cloud call is blocked.</span></div>
          <div><b>Employees can&apos;t switch it off</b><span>Only managers can change the firm&apos;s masking.</span></div>
          <div><b>Walls between lawyers</b><span>The server keeps each lawyer to their own matters. Asking for another matter&apos;s file gets the same reply as a file that doesn&apos;t exist.</span></div>
          <div><b>Managers don&apos;t read privileged text</b><span>They see that the work happened and where it ran. The text itself is hidden.</span></div>
          <div><b>A log that can&apos;t be quietly edited</b><span>Each entry is hash-chained to the last, so a changed entry fails verification.</span></div>
          <div><b>Planned actions don&apos;t run</b><span>Actions a model plans while reading privileged text are logged and never carried out.</span></div>
        </div>
      </section>

      <section className="section">
        <div className="intro">
          <h2>We tried to break it.</h2>
          <p className="prose">We wrote 136 attack cases. After one fix, none of them got privileged text to the cloud. These are our own tests, so they&apos;re a test and not a guarantee.</p>
        </div>
        <div>
          {ATTACKS.map(([title, body]) => <details key={title}><summary>{title}</summary><p>{body}</p></details>)}
        </div>
      </section>

      <section className="section">
        <h2>What this doesn&apos;t do.</h2>
        <div className="grid2">
          <div><b>The leak test has limits</b><span>It catches exact client names, secrets, emails and runs of 8 words from a document. A paraphrase would get past it.</span></div>
          <div><b>d1 can misjudge</b><span>Thresholds lean toward privileged, and fixed rules back it up. This reduces risk and doesn&apos;t remove it.</span></div>
          <div><b>Network access needs HTTPS</b><span>By default the app only listens on its own machine. Put HTTPS in front before opening it to an office.</span></div>
          <div><b>It doesn&apos;t replace your obligations</b><span>Chamber isn&apos;t legal advice and doesn&apos;t replace a firm&apos;s ethics obligations.</span></div>
        </div>
      </section>
    </div>
  );
}
