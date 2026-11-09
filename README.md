# Chamber

One on-device AI shared by a law firm. Each model earns the work it can do, and privileged text never leaves.

[한국어](README.ko.md)

Built for the AGI House *Personal Agent to Real-World Deployment* Build Day, November 2026.

## The problem

Firms want on-device AI because client files can't go to the cloud. But the work still has to get done after the switch. A hybrid helps, but nobody knows where to draw the line, because what a small model can really do with a lawyer's work differs by firm, role and person.

Chamber doesn't draw the line. Each model earns it, per person, per task, per model.

## How it works

| Step | What happens |
|---|---|
| Read | Liquid's d1-2B reads every request on device and decides whether it is privileged, needs a human, and what kind of work it is. |
| Privileged | Liquid's LFM3-1.7B answers on device. Attached client files, marked text and unreadable text stay on device whatever d1 scores. |
| New public work | LFM3 and the cloud both answer. The lawyer picks between two unlabeled answers. After 3 good results, that task moves on device. The threshold of 3 is set to keep the demo short. |
| Cloud | Names are masked first. The key stays on device and names are restored locally. |
| Legal decisions | These go to a human. No AI answers them. |
| Walls | Lawyers share one model but can't see each other's matters. The server enforces this. |
| Audit | A hash-chained log tells the managing partner in plain sentences what happened. |

**Same task, different result.** Two lawyers ran "Public fee or limit." Checking a claim against one limit moved on device. An executor's fee across three tiers stayed in the cloud, because LFM3 got the math wrong. Nobody wrote that rule.

## Measured

These numbers come from running the system on a Mac laptop.

- 12 cloud calls avoided in one simulated firm day.
- 1.0s on device vs 2.6s cloud, median over 23 requests both answered.
- d1 picked the right kind of work on 144 of 144 test requests, at about 0.4s.
- No privileged test request scored as public at the 0.30 threshold.
- 136 attack cases we wrote did not get privileged text to the cloud, after one fix. Run them with `scripts/redteam_d1.py`.

## Run it

You need Python 3.12, [Ollama](https://ollama.com), and [llama.cpp](https://github.com/ggml-org/llama.cpp).

```bash
python3.12 -m venv .venv
.venv/bin/pip install fastapi uvicorn httpx anthropic pytest
ollama pull lfm3:1.7b
```

Start the decision model in one terminal:

```bash
llama serve -hf LiquidAI/d1-2B-GGUF:Q8_0 -b 8192 -ub 8192 --port 9931
```

Start the app in another:

```bash
export ANTHROPIC_API_KEY=...      # never put this in a file
./scripts/clean_start.sh 8000
```

`clean_start.sh` deletes the demo database before it starts. Without a key, the cloud is replaced by a local `qwen3:8b` stand-in, which needs `ollama pull qwen3:8b`.

| Page | What it is |
|---|---|
| `http://localhost:8000/demo` | One window: chat, a Maya / Daniel switch, the firm's board, and Reset at the top right |
| `http://localhost:8000/chat` | Chat for one lawyer |
| `http://localhost:8000/` | The managing partner's dashboard |

`DEMO.md` has the 3-minute demo script. Run the tests with `.venv/bin/python -m pytest`.

## Stack

Python, FastAPI, SQLite, Ollama, llama.cpp, Liquid LFM3-1.7B, Liquid d1-2B, Claude API. The front end is static HTML and plain JavaScript.

## Scope

- The firm, matters and documents are synthetic.
- It has run on a Mac laptop, not yet on dedicated AI hardware.
- Three trials is a demo bar. A real firm would need far more.
- The leak test catches exact client names, secrets, emails and runs of 8 words from a document, so a paraphrase would get past it. d1 can misjudge, which is why fixed rules back it up.
- The attack cases are our own, so they are a test and not a guarantee.
- File upload and real sign-in aren't built. Files are picked from the seeded set, and the PINs in `seed/users.json` are demo values.
- Some California citations in the prepared tasks haven't been checked against the official code.
- This isn't legal advice, and it doesn't replace a firm's ethics obligations.

## License

MIT
