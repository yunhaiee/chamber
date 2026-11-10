"use client";

import { useState } from "react";

const NEED = 3;
const ROUNDS = [
  { ask: "When is the next hearing in this public docket?", local: "December 12, 2026, Dept 330", cloud: "The next hearing is set for December 12, 2026, in Department 330." },
  { ask: "What date is the case management conference?", local: "September 13, 2026, Dept 386", cloud: "The conference is on September 13, 2026, in Department 386." },
  { ask: "When does the motion get heard?", local: "September 1, 2026, Dept 372", cloud: "It's calendared for September 1, 2026, in Department 372." },
];

export default function EarnTrial() {
  const [round, setRound] = useState(0);
  const [streak, setStreak] = useState(0);
  const [said, setSaid] = useState("Pick the answer you'd use. You don't know which model wrote it.");

  const item = ROUNDS[round % ROUNDS.length];
  const localFirst = round % 2 === 0;
  const a = localFirst ? item.local : item.cloud;
  const b = localFirst ? item.cloud : item.local;
  const done = streak >= NEED;

  function pick(choice: "a" | "b" | "both" | "neither") {
    const reveal = `${localFirst ? "A" : "B"} was the local model.`;
    const localPicked = choice === "both" || (choice === "a" && localFirst) || (choice === "b" && !localFirst);
    const next = localPicked ? streak + 1 : 0;
    setStreak(next);
    setRound(round + 1);
    if (next >= NEED) setSaid(`${reveal} This task now runs on device for you, and the cloud stops being called.`);
    else if (choice === "neither") setSaid(`${reveal} Neither answer was good, so it goes to a person and the count starts over.`);
    else if (localPicked) setSaid(`${reveal} ${next} of ${NEED} good answers.`);
    else setSaid(`${reveal} You preferred the cloud, so the count starts over.`);
  }

  function restart() {
    setRound(0);
    setStreak(0);
    setSaid("Pick the answer you'd use. You don't know which model wrote it.");
  }

  return (
    <div className="panel">
      <div className="trial-head">
        <b>Public lookup</b>
        <span key={done ? "done" : "test"} className={done ? "pill on draw" : "pill test"}>{done ? "On device" : "Testing"}</span>
        <span className="marks" aria-hidden="true">{[0, 1, 2].map((i) => <i key={i} className={`mark${i < streak ? " pass" : ""}`} />)}</span>
      </div>
      {!done && (
        <>
          <div>{item.ask}</div>
          <div className="answers">
            <div className="answer"><small>Answer A</small>{a}</div>
            <div className="answer"><small>Answer B</small>{b}</div>
          </div>
          <div className="choices">
            <button type="button" className="choice" onClick={() => pick("a")}>A is better</button>
            <button type="button" className="choice" onClick={() => pick("b")}>B is better</button>
            <button type="button" className="choice" onClick={() => pick("both")}>Both good</button>
            <button type="button" className="choice" onClick={() => pick("neither")}>Neither</button>
          </div>
        </>
      )}
      <p className="status" role="status">{said}</p>
      {(done || round > 0) && <div><button type="button" className="choice text" onClick={restart}>Start over</button></div>}
      <p className="sample">Example answers. The real app uses your own lawyers&apos; judgment on live work.</p>
    </div>
  );
}
