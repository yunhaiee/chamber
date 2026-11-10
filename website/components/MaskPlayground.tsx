"use client";

import { type ChangeEvent, type FormEvent, useMemo, useRef, useState } from "react";
import { mask, parseList, tagFor, type Term, usable } from "@/lib/mask";

const START = "Harlow Orchards asked whether Priya Natarajan can be reached at (415) 555-0134 or priya@harlow.example about case CGC-26-418822.";

export default function MaskPlayground() {
  const [text, setText] = useState(START);
  const [terms, setTerms] = useState<Term[]>([{ value: "Harlow Orchards", tag: "CLIENT" }, { value: "Priya Natarajan", tag: "PERSON" }]);
  const [draft, setDraft] = useState("");
  const [said, setSaid] = useState("");
  const file = useRef<HTMLInputElement>(null);
  const result = useMemo(() => mask(text, terms), [text, terms]);

  function add(values: string[]) {
    const have = new Set(terms.map((t) => t.value.toLowerCase()));
    const fresh = [...new Map(values.filter(usable).filter((v) => !have.has(v.toLowerCase())).map((v) => [v.toLowerCase(), v])).values()];
    setTerms([...terms, ...fresh.map((value) => ({ value, tag: tagFor(value) }))]);
    return fresh.length;
  }

  function submit(ev: FormEvent) {
    ev.preventDefault();
    const value = draft.trim().replace(/\s+/g, " ");
    if (!value) return;
    if (!usable(value)) { setSaid("That entry is too short to mask safely."); return; }
    add([value]);
    setDraft("");
    setSaid("");
  }

  async function upload(ev: ChangeEvent<HTMLInputElement>) {
    const chosen = ev.target.files?.[0];
    ev.target.value = "";
    if (!chosen) return;
    if (!/\.(txt|csv)$/i.test(chosen.name)) { setSaid("Upload a .txt or .csv file."); return; }
    const count = add(parseList(chosen.name, await chosen.text()));
    setSaid(`Added ${count} from ${chosen.name}. It was read only in your browser.`);
  }

  return (
    <div className="panel">
      <div className="mask-grid">
        <div>
          <label className="fieldlabel" htmlFor="mask-input">The lawyer writes</label>
          <textarea id="mask-input" className="mask-input" value={text} onChange={(e) => setText(e.target.value)} spellCheck={false} />
        </div>
        <div>
          <span className="fieldlabel">The cloud receives</span>
          <div className="mask-output" aria-live="polite">{result.parts.map((p, i) => (p.tagged ? <span key={i} className="bar">{p.text}</span> : <span key={i}>{p.text}</span>))}</div>
        </div>
      </div>
      <div className="keylist" aria-label="Key">
        <span>Key, kept on the device:</span>
        {result.key.length ? result.key.map((k) => <span key={k.tag}><span>{k.tag}</span> {k.value}</span>) : <span>nothing to mask</span>}
      </div>
      <div style={{ display: "grid", gap: 8 }}>
        <span className="fieldlabel">The firm&apos;s masking list</span>
        <div className="termline">
          {terms.map((t) => <span key={t.value} className="term">{t.value}<button type="button" aria-label={`Remove ${t.value}`} onClick={() => setTerms(terms.filter((x) => x !== t))}>×</button></span>)}
        </div>
        <form className="termform" onSubmit={submit}>
          <input aria-label="Add a name or private detail" placeholder="Add a name or private detail" value={draft} onChange={(e) => setDraft(e.target.value)} />
          <button>Add</button>
          <button type="button" onClick={() => file.current?.click()}>Upload file</button>
          <input ref={file} type="file" accept=".txt,.csv" hidden onChange={upload} />
        </form>
        {said && <p className="status" role="status">{said}</p>}
      </div>
      <p className="sample">Try your own text. This demo runs entirely in your browser and sends nothing anywhere.</p>
    </div>
  );
}
