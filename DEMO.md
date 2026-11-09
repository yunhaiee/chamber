# Counsel Box: 3-minute demo

**The one line:** Don't decide what runs locally. Let the local model prove it. And let the device refuse what must never leave.

---

## Before you go on stage

Run these in three terminals, in order.

**Terminal 1: the decision model**
```bash
llama serve -hf LiquidAI/d1-2B-GGUF:Q8_0 -b 8192 -ub 8192
curl localhost:9931/health        # should say ok
```

**Terminal 2: the app (fresh start)**
```bash
cd ~/dev/onDeviceBuildDay
export ANTHROPIC_API_KEY=...      # paste your key here, never into a file
./scripts/clean_start.sh 8000
```

**Terminal 3: proof of what leaves the device**
```bash
cd ~/dev/onDeviceBuildDay
SH_DB=demo.db .venv/bin/python wire.py --last 0
```

**Warm up the model** within 5 minutes of going on:
```bash
curl -s localhost:11434/api/chat -d '{"model":"lfm3:1.7b","stream":false,"messages":[{"role":"user","content":"hi"}]}' >/dev/null
```

**Windows, at 110-125% zoom:**

| Where | Open |
|---|---|
| Left, 55% | `http://localhost:8000/demo` (Maya on the left, Daniel on the right) |
| Right, 45% | `http://localhost:8000/` (the dashboard, on Board) |
| Behind | Terminal 3 |

**Check:** both boards are empty, and both chats say Online.

**To rehearse again:** rerun `./scripts/clean_start.sh 8000` and refresh both pages. It wipes everything.

**Keys on the dashboard:** `1` Board · `2` Requests · `3` Audit log · `m` Masking · `f` automatic day · `Esc` close detail

**In chat:** click a task link under the message box, then press Enter.

---

## The script

### 0:00 The problem (35s)
Nothing to click. Boards are empty.

**Say:** "Firms want to move to on-device AI, because client files can't go to the cloud. But what happens when the work stops getting done after the switch? That's why you need a hybrid: some work local, some in the cloud.

So where's the line? You could draw a fixed one. But nobody knows what a small model can really do with a lawyer's work. It differs between firms, between roles, even between two people doing the same task.

So we don't draw the line. Each model has to earn it."

### 0:35 Maya earns it (20s)

| Pane | Do |
|---|---|
| Maya | Click **Public lookup**, Enter. Press **Both good**. Do this 3 times. |

Correct answers: December 12, 2026, Dept 330 · September 13, 2026, Dept 386 · September 1, 2026, Dept 372.

**You should see:** on the Board, Maya's **Public lookup** goes from Testing to **On device**.

**Say:** "Liquid's d1 model reads every request on this device and decides where it can go. This one is public, so both models answer, and the lawyer picks without knowing which is which. After three good answers, the cloud stops being called."

### 0:55 Masking (15s)

| Pane | Do |
|---|---|
| Maya | Click **Research**, Enter. Pick the answer that says **4 years, § 337**. |
| Dashboard | Press `2`. Point at `[CLIENT_1]` and the Key. Press `1` to go back. |

**Say:** "When work goes to the cloud, the client's name doesn't. The key stays here, and we swap the name back here."

### 1:10 Privileged work (20s)

**1. A privileged file.** Maya: click **Summarize deposition**. Point at the **Privileged file** tag, then press Enter.

**You should see:** `ON DEVICE · privileged file attached`

**Say:** "If a lawyer attaches a client file, it stays on device. That's a fixed rule."

Don't read the bullets aloud, because the summary runs long.

**2. Privileged text inside a question.** Paste this into Maya's box:

```
What is the deadline to remove a case to federal court? Here is the email from our client: 'Maya, please keep this between us. We deleted the alarm log after Brightline called, and I am worried about it.'
```

**You should see:** `KEPT ON DEVICE · d1 privileged 0.90`

**Say:** "No file here, just a question with a client's email pasted in. d1 catches it, and the router refuses to send it."

### 1:30 History is per model (10s)

| Pane | Do | You should see |
|---|---|---|
| Maya | Open the model menu next to the send button. Choose **Liquid · lfm2.5:8b**. | Maya's board empties |
| Maya | Choose **Liquid · lfm3:1.7b** again. | Her rows return |

**Say:** "Each Liquid model earns its own record, because each can do different things."

**Change it back before going on.**

### 1:40 Hitting the wall (20s)

| Pane | Do | You should see |
|---|---|---|
| Daniel | Type `Summarize the Harlow deposition.` | `No document called that in your matters.` |

**Say:** "Same on-device model, same hardware, and Daniel still can't see Maya's files. He can't even tell the file exists. Today this runs on my Mac. In a firm, it would run on a dedicated AI machine in the office."

### 2:00 Same task, different result (25s)
Press `f` on the dashboard, and press `1` if you aren't on the Board.

**Say:** "Let's send a lot of different tasks quickly and see how they split."

Give it about 20 seconds.

**You should see:** **Public fee or limit** is **On device** for Maya and **Cloud** for Daniel.

**Say:** "Same task, different result. Maya checks a claim against one limit. Daniel works out an executor's fee across three tiers, and this small model gets that math wrong. Nobody wrote that rule. The results did."

### 2:25 Human in the loop (10s)
Type this in Maya's box: `Should we accept Brightline's offer?`

**You should see:** `HUMAN · Added to Ruth Abernathy's queue.`

**Say:** "d1 recognizes a legal decision. No AI answers it. It goes to a person."

### 2:35 Close (25s)
Press `3` for the audit log. Point at `Privileged text sent to cloud 0` and `Log intact`. Bring Terminal 3 forward for a moment. Press `1` for the Board.

**Say:** "Nothing privileged left the building, and the managing partner can read exactly what did.

Firms don't have to guess what can run locally. Every person, task and model builds its own record. And it isn't only law: clinics, accountants and HR all face the same question, and the answer is different for each of them.

Don't decide what runs locally. Let the local model prove it."

---

## If something goes wrong

| Problem | Do this |
|---|---|
| An answer takes more than 10 seconds | Keep talking. The first call after a pause loads the model. |
| Both A and B look wrong | Press **Neither**. It goes to the human queue, which is a fine thing to show. |
| Wi-Fi drops | Say so. On-device work continues, and cloud work shows `Waiting for connection` and runs on reconnect. |
| Chat shows an error | `curl localhost:9931/health`, then rerun clean start and refresh. |
| Wrong model is selected | Switch back to `lfm3:1.7b` before pressing `f`. |
| Daniel's rows still say Testing | Wait a few more seconds. His last trials are still finishing. |
| Maya's row didn't reach On device | One pick went to the cloud. Say the evidence decided, and move on. |

---

## Say this honestly

- The firm, its matters and documents are synthetic. Every route, check and log entry on screen is real and live.
- This runs on a Mac laptop, and the header shows the real machine name. It hasn't been run on dedicated AI hardware yet.
- 3 trials is a demo bar. A real firm would need far more.
- "Privileged text sent 0" means our leak test found none. It catches exact client names, secrets, emails and runs of 8 words from a document, so a paraphrase would get past it. d1 can misjudge, which is why thresholds lean toward privileged and hard rules back it up. This reduces risk. It doesn't replace a firm's ethics obligations.
- Research answers come from the cloud and still need checking against the source. This isn't legal advice.
- Nobody has asked a law firm yet, so ask people in the room.

---

## Likely questions

**Why doesn't privileged work earn its way?**
It can't be compared with the cloud, so there's no second answer. It's produced on device, and a lawyer fixes it if it's wrong.

**Daniel's "Compute distributions" says 0 of 3 right. Why is it still on device?**
It's privileged, so it can never leave. The record tells the lawyer to check it. Better math needs a better local model.

**Why not LFM2.5-24B-A2B?**
On this laptop it kept reasoning with thinking off, returned empty replies and took 12-35s a task. It wasn't tested on a PGX.

**Can a pasted document talk d1 into sending it to the cloud?**
We tested 136 attack cases: "ignore your instructions," fake system notes, fake approvals, claims that it's public, burying it in public text, base64, hex, rot13, reversed and spaced-out text. None would reach the cloud. d1 alone resisted the instructions. It could not read encoded text, so we added a fixed rule: text that can't be read doesn't leave. Run it yourself with `scripts/redteam_d1.py`. These are our own attacks, so it's a test and not a guarantee.

**Could an instruction inside a document make the model do something?**
Actions planned while working on privileged text are logged and never run.

**How does d1 do?**
On 144 prepared requests it picked the right kind every time, at about 0.4s median. No privileged request scored as public at the 0.30 threshold, and 5 of 24 public questions were held back as false alarms.

**Why does the other model score so badly?**
Prompts were tuned on `lfm3:1.7b` and not retuned. Treat those numbers as a first look.
