# Chamber

One on-device AI shared by a law firm. Each model earns the work it can do, and privileged text never leaves.

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
| Audit | A hash-chained log records in plain sentences what happened. |
| People | The head of firm adds managers and employees. A manager oversees only the people under them, and a legal decision goes to the asker's own manager. |
| Firm masking | Managers keep one list of names and private details, typed in or uploaded as a `.txt` or `.csv`. It's applied to everyone's cloud text, and employees can't change it. |
| Models | LFM3 is the default. Any other chat model installed in Ollama appears in the menu next to the send button and earns its own record. Prompts are tuned for LFM3, so others may score lower. With a key set, the cloud model is in the same menu: public work then goes straight to it, masked. Privileged work still stays on device. |

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
security add-generic-password -a chamber -s chamber-anthropic-key -U -w      # once: paste your key at the prompt
./scripts/start.sh 8000
```

The key lives in the macOS Keychain and the start scripts read it from there, so it's never in a file. `ANTHROPIC_API_KEY` overrides it if set.

Open `http://localhost:8000` on that machine and create the firm. Everything is kept in `chamber.db` on the device, so it's still there after a restart. Without a key, the cloud is replaced by a local `qwen3:8b` stand-in, which needs `ollama pull qwen3:8b`.

The app only listens on this machine by default. To let others in the office reach it, set `CHAMBER_HOST=0.0.0.0` and put HTTPS in front of it.

| Page | What it is |
|---|---|
| `http://localhost:8000/` | Sign in and chat |
| `http://localhost:8000/manage` | Board, Requests, Masking and People, for the head of firm and managers |

To run the fictional firm instead, use `./scripts/clean_start.sh 8000` and open `http://localhost:8000/demo`. That script deletes `demo.db` before it starts and never touches `chamber.db`.

`DEMO.md` has the 3-minute demo script. Run the tests with `.venv/bin/python -m pytest`.

## Stack

Python, FastAPI, SQLite, Ollama, llama.cpp, Liquid LFM3-1.7B, Liquid d1-2B, Claude API. The front end is static HTML and plain JavaScript.

## Scope

- The demo's firm, matters and documents are synthetic.
- It has run on a Mac laptop, not yet on dedicated AI hardware.
- Three trials is a demo bar. A real firm would need far more.
- The leak test catches exact client names, secrets, emails and runs of 8 words from a document, so a paraphrase would get past it. d1 can misjudge, which is why fixed rules back it up.
- The attack cases are our own, so they are a test and not a guarantee.
- Adding matters and uploading client documents aren't built yet, so a real firm's chat has no files to attach. The PINs in `seed/users.json` are demo values.
- People can't reset or change their own password yet. The password is the one their manager set.
- Some California citations in the prepared tasks haven't been checked against the official code.
- This isn't legal advice, and it doesn't replace a firm's ethics obligations.

## License

MIT
