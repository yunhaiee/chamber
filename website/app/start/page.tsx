import type { Metadata } from "next";
import { Code } from "@/components/Bits";
import { GITHUB } from "@/lib/site";

export const metadata: Metadata = { title: "Get started", description: "Run Chamber on your own machine." };

const STEPS = [
  { title: "Get the code and install", body: "You need Python 3.12, Ollama and llama.cpp.", code: `git clone ${GITHUB}.git\ncd chamber\npython3.12 -m venv .venv\n.venv/bin/pip install fastapi uvicorn httpx anthropic pytest\nollama pull lfm3:1.7b` },
  { title: "Store your cloud key", body: "This goes in the macOS Keychain, so it's never in a file. Paste your Anthropic key at the prompt. Without a key, a local stand-in plays the cloud, which needs ollama pull qwen3:8b.", code: "security add-generic-password -a chamber -s chamber-anthropic-key -U -w" },
  { title: "Start the decision model", body: "Leave this running in its own terminal.", code: "llama serve -hf LiquidAI/d1-2B-GGUF:Q8_0 -b 8192 -ub 8192 --port 9931" },
  { title: "Start Chamber", body: "Run this in another terminal, then open http://localhost:8000 and create your firm. Your data stays in chamber.db on the device.", code: "./scripts/start.sh 8000" },
];

export default function Start() {
  return (
    <div className="wrap stack">
      <header className="intro">
        <h1 className="page-title">Run it on your own machine.</h1>
        <p className="lede">Four steps. Everything runs on your device except masked public work sent to the cloud.</p>
      </header>

      <section className="cmds">
        {STEPS.map((step, i) => (
          <div className="cmd-step" key={step.title}>
            <span>{i + 1}</span>
            <div>
              <h3>{step.title}</h3>
              <p className="muted">{step.body}</p>
              <Code>{step.code}</Code>
            </div>
          </div>
        ))}
      </section>

      <section className="section">
        <div className="intro">
          <h2>Want to see it with a fictional firm first?</h2>
          <p className="prose">The demo starts with two lawyers and a managing partner. It wipes its own demo database each time and never touches your firm&apos;s data.</p>
        </div>
        <Code>./scripts/clean_start.sh 8000</Code>
        <p className="small">Then open http://localhost:8000/demo.</p>
      </section>
    </div>
  );
}
