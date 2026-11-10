"use client";

import { useState } from "react";

type Role = "head" | "manager" | "employee";
const WORD: Record<Role, string> = { head: "Head of firm", manager: "Manager", employee: "Employee" };
const CAN: [string, Role[]][] = [
  ["Ask Chamber for help with their own work", ["head", "manager", "employee"]],
  ["Add employees", ["head", "manager"]],
  ["Add managers and change anyone's role", ["head"]],
  ["See the Board and Requests for their own people", ["head", "manager"]],
  ["See the whole firm's Board and Requests", ["head"]],
  ["Edit the firm's masking list or upload one", ["head", "manager"]],
  ["Receive legal decisions from the people below them", ["head", "manager"]],
  ["Read privileged text in someone else's request", []],
];

export default function OrgChart() {
  const [role, setRole] = useState<Role>("manager");
  const node = (r: Role, key?: string) => (
    <button key={key ?? r} type="button" aria-pressed={role === r} className={`org-node${role === r ? " on" : ""}`} onClick={() => setRole(r)}>{WORD[r]}</button>
  );
  return (
    <div className="two" style={{ alignItems: "center" }}>
      <div className="org">
        <div className="org-row">{node("head")}</div>
        <span className="org-link" />
        <div className="org-row">{node("manager", "m1")}{node("manager", "m2")}</div>
        <span className="org-link" />
        <div className="org-row">{node("employee", "e1")}{node("employee", "e2")}{node("employee", "e3")}</div>
      </div>
      <div className="can" role="status">
        <h3 style={{ paddingBottom: 12 }}>{WORD[role]}</h3>
        {CAN.map(([text, who]) => {
          const yes = who.includes(role);
          return <div key={text} className={yes ? "" : "no"}><span aria-hidden="true">{yes ? "✓" : "–"}</span><span>{yes ? "" : <span className="visually-none">Cannot: </span>}{text}</span></div>;
        })}
      </div>
    </div>
  );
}
