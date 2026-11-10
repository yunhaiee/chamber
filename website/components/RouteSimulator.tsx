"use client";

import { useEffect, useState } from "react";

type Preset = { id: string; ask: string; hint: string; legal: boolean; priv: boolean; why?: string; masked?: string };

const PRESETS: Preset[] = [
  { id: "docket", ask: "What is the next hearing date on this public docket?", hint: "Public lookup", legal: false, priv: false },
  { id: "research", ask: "What's the limit for fraud? Harlow Orchards asked.", hint: "Public research that names a client", legal: false, priv: false, masked: "What's the limit for fraud? [CLIENT_1] asked." },
  { id: "file", ask: "Summarize this deposition.", hint: "Client file attached", legal: false, priv: true, why: "A fixed rule: an attached client file stays on device, whatever the decision model scores." },
  { id: "email", ask: "What's the deadline? Here is our client's email: please keep this between us.", hint: "Client email pasted into a question", legal: false, priv: true, why: "The decision model flags the pasted client email as privileged." },
  { id: "advice", ask: "Should we accept Brightline's offer?", hint: "A legal decision", legal: true, priv: false },
];

type Step = { q: string; a?: string; why?: string };

export default function RouteSimulator() {
  const [id, setId] = useState(PRESETS[0].id);
  const [earned, setEarned] = useState(false);
  const [shown, setShown] = useState(0);
  const preset = PRESETS.find((p) => p.id === id)!;

  const steps: Step[] = [{ q: "The decision model reads the request on your device" }, { q: "Is it a legal decision?", a: preset.legal ? "Yes" : "No" }];
  if (!preset.legal) {
    steps.push({ q: "Is it privileged?", a: preset.priv ? "Yes" : "No", why: preset.why });
    if (!preset.priv) steps.push({ q: "Has this task earned its place on device?", a: earned ? "Yes" : "No" });
  }

  useEffect(() => {
    setShown(0);
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(99);
      return;
    }
    const timers: ReturnType<typeof setTimeout>[] = [];
    for (let i = 1; i <= steps.length + 1; i++) timers.push(setTimeout(() => setShown(i), i * 620));
    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, earned]);

  const finished = shown > steps.length;
  let pill = <span className="pill test">Testing</span>;
  let line = "A local model and the cloud both answer. The lawyer picks between two unlabeled answers.";
  if (preset.legal) { pill = <span className="pill human">Human</span>; line = "No AI answers. It's added to the person's manager's queue."; }
  else if (preset.priv) { pill = <span className="pill on">On device</span>; line = "A local model answers. Nothing leaves the device."; }
  else if (earned) { pill = <span className="pill on">On device</span>; line = "The local model has earned this task for this person. The cloud isn't called."; }

  return (
    <div className="sim">
      <div className="presets" role="radiogroup" aria-label="Example requests">
        {PRESETS.map((p) => (
          <button key={p.id} type="button" role="radio" aria-checked={p.id === id} className={`preset${p.id === id ? " on" : ""}`} onClick={() => setId(p.id)}>
            <b>{p.ask}</b><small>{p.hint}</small>
          </button>
        ))}
      </div>
      <div className="panel">
        <div className="steps">
          {steps.map((step, i) => {
            const state = shown > i + 1 ? "done" : shown === i + 1 ? "live" : "";
            const reached = shown > i + 1;
            return (
              <div key={step.q} className={`step ${state}`}>
                <span className="dotmark" />
                <span>{step.q}{reached && step.why && <span className="why">{step.why}</span>}</span>
                <span>{reached && step.a}</span>
              </div>
            );
          })}
        </div>
        <div className="outcome" role="status">
          {finished && (
            <>
              <div key={`${id}-${earned}`} style={{ display: "flex" }}>{pill}</div>
              <p>{line}</p>
              {preset.masked && !earned && <p className="small">The cloud receives: <span style={{ fontFamily: "var(--mono)" }}>{preset.masked.split("[CLIENT_1]")[0]}<span className="bar">[CLIENT_1]</span>{preset.masked.split("[CLIENT_1]")[1]}</span></p>}
            </>
          )}
        </div>
        <div className="switchline">
          <button type="button" className="toggle" role="switch" aria-checked={earned} aria-label="This task has earned its place" disabled={preset.legal || preset.priv} onClick={() => setEarned(!earned)} />
          <span>This task has earned its place</span>
        </div>
      </div>
    </div>
  );
}
