# Chamber: 3-minute demo

**The one line:** Don't decide what runs locally. Let the local model prove it. And let the device refuse what must never leave.

---

## Before you go on stage

Run these in two terminals, in order. Terminal 3 is optional, for questions about what left the device.

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

**Terminal 3 (optional): proof of what leaves the device**
```bash
cd ~/dev/onDeviceBuildDay
SH_DB=demo.db .venv/bin/python wire.py --last 0
```

**Warm up the model** within 5 minutes of going on:
```bash
curl -s localhost:11434/api/chat -d '{"model":"lfm3:1.7b","stream":false,"messages":[{"role":"user","content":"hi"}]}' >/dev/null
```

**One window, full screen:** open `http://localhost:8000/demo`. The **Maya Chen | Daniel Osei** switch at the top changes both the chat on the left and the board on the right.

**Check:** the board is empty and the chat doesn't say Offline. The page no longer shows when the cloud is a stand-in, so read the terminal: `clean_start.sh` prints a warning if there's no key.

**To rehearse again:** click **Reset** at the top right, then click it again to confirm. It erases all history and reloads the page. It says `Still working` until any running request or firm's day finishes. If the app itself is misbehaving, rerun `./scripts/clean_start.sh 8000` and refresh.

**In chat:** on a new chat, click a task in the list. Once a chat has started, open **Tasks** next to `+ Attach file`, pick the task, then press Enter.

---

## The script

### 0:00 The problem (35s)
Nothing to click. Boards are empty.

**Say:** "Firms want to move to on-device AI, because client files can't go to the cloud. But what happens when the work stops getting done after the switch? That's why you need a hybrid: some work local, some in the cloud.

So where's the line? You could draw a fixed one. But nobody knows what a small model can really do with a lawyer's work. It differs between firms, between roles, even between two people doing the same task.

So we don't draw the line. Each model has to earn it."

### 0:35 Maya earns it (25s)

| Pane | Do |
|---|---|
| Maya | Pick **Public lookup** under Tasks, Enter. Press **Both good**. Do this 3 times. |

Correct answers: December 12, 2026, Dept 330 · September 13, 2026, Dept 386 · September 1, 2026, Dept 372.

**You should see:** on the Board, Maya's **Public lookup** goes from Testing to **On device**.

**Say:** "Liquid's d1 model reads every request on this device and decides where it can go. This one is public, so both models answer, and the lawyer picks without knowing which is which. After three good answers, the cloud stops being called. We set it to three to keep this demo short. Each model earns its own record."

### 1:00 Masking (15s)

| Pane | Do |
|---|---|
| Maya | Pick **Research** under Tasks, Enter. Pick the answer that says **4 years, § 337**. |
| Dashboard | Click **Requests**, then the top row. Point at `[CLIENT_1]` and the Key. Click **Board** to go back. |

**Say:** "When work goes to the cloud, the client's name doesn't. The key stays here, and we swap the name back here."

### 1:15 Privileged work (20s)

**1. A privileged file.** Maya: pick **Summarize deposition** under Tasks. Point at the **Privileged file** tag, then press Enter.

**You should see:** `On device`

**Say:** "If a lawyer attaches a client file, it stays on device. That's a fixed rule."

Don't read the bullets aloud, because the summary runs long.

**2. Privileged text inside a question.** Paste this into Maya's box:

```
What is the deadline to remove a case to federal court? Here is the email from our client: 'Maya, please keep this between us. We deleted the alarm log after Brightline called, and I am worried about it.'
```

**You should see:** `Kept on device`

**Say:** "No file here, just a question with a client's email pasted in. d1 catches it, and the router refuses to send it."

### 1:35 Hitting the wall (20s)

| Pane | Do | You should see |
|---|---|---|
| Daniel | Switch to **Daniel Osei** at the top. Type `Summarize the Harlow deposition.` | `No document called that in your matters.` |

**Say:** "Same on-device model, same hardware, and Daniel still can't see Maya's files. He can't even tell the file exists. Today this runs on my Mac. In a firm, it would run on a dedicated AI machine in the office."

### 1:55 Same task, different result (35s)
Stay on **Daniel Osei**. On the Board, click **Run the firm's day**.

**Say:** "Let's send a lot of different tasks quickly and see how they split."

Give it about 30 seconds.

**You should see:** Daniel's **Public fee or limit** is **Cloud**. Tap **Maya Chen** at the top: hers is **On device**. The numbers at the top are moving.

**Say:** "Same task, different result. Maya checks a claim against one limit. Daniel works out an executor's fee across three tiers, and this small model gets that math wrong. Nobody wrote that rule. The results did. And every call that moved on device is a cloud call the firm doesn't pay for, and it's faster."

### 2:30 Human in the loop (10s)
Still on Maya. Type `Should we accept Brightline's offer?`

**You should see:** `Added to Ruth Abernathy's queue.` and `Human`

**Say:** "d1 recognizes a legal decision. No AI answers it. It goes to a person."

### 2:40 Close (20s)
Click **Requests**. Point at the **Where** column. Click **Board**.

**Say:** "Nothing privileged left the building, and the managing partner can read exactly what did.

Firms don't have to guess what can run locally. Every person, task and model builds its own record. And it isn't only law: clinics, accountants and HR all face the same question, and the answer is different for each of them.

Don't decide what runs locally. Let the local model prove it."

---

## If something goes wrong

| Problem | Do this |
|---|---|
| An answer takes more than 10 seconds | Keep talking. The first call after a pause loads the model. |
| Both A and B look wrong | Press **Neither**. It goes to the human queue, which is a fine thing to show. |
| A menu covers the answer | Click anywhere else to close it. |
| Wi-Fi drops | Say so. On-device work continues, and cloud work shows `Waiting for connection` and runs on reconnect. |
| Chat shows an error | `curl localhost:9931/health`, then rerun clean start and refresh. |
| Daniel's rows still say Testing | Wait a few more seconds. His last trials are still finishing. |
| Maya's row didn't reach On device | One pick went to the cloud. Say the evidence decided, and move on. |

---

## Say this honestly

- The firm, its matters and documents are synthetic. Every route, check and log entry on screen is real and live.
- This runs on a Mac laptop. It hasn't been run on dedicated AI hardware yet.
- 3 trials is a demo bar. A real firm would need far more.
- "Nothing privileged left" means our leak test found none. It catches exact client names, secrets, emails and runs of 8 words from a document, so a paraphrase would get past it. d1 can misjudge, which is why thresholds lean toward privileged and hard rules back it up. This reduces risk. It doesn't replace a firm's ethics obligations.
- Research answers come from the cloud and still need checking against the source. This isn't legal advice.
- Nobody has asked a law firm yet, so ask people in the room.

---

## Likely questions

**Why doesn't privileged work earn its way?**
It can't be compared with the cloud, so there's no second answer. It's produced on device, and a lawyer fixes it if it's wrong.

**Why not LFM2.5-24B-A2B?**
On this laptop it kept reasoning with thinking off, returned empty replies and took 12-35s a task. It wasn't tested on a PGX.

**Can a pasted document talk d1 into sending it to the cloud?**
We tested 136 attack cases: "ignore your instructions," fake system notes, fake approvals, claims that it's public, burying it in public text, base64, hex, rot13, reversed and spaced-out text. None would reach the cloud. d1 alone resisted the instructions. It could not read encoded text, so we added a fixed rule: text that can't be read doesn't leave. Run it yourself with `scripts/redteam_d1.py`. These are our own attacks, so it's a test and not a guarantee.

**Could an instruction inside a document make the model do something?**
Actions planned while working on privileged text are logged and never run.

**How does d1 do?**
On 144 prepared requests it picked the right kind every time, at about 0.4s median. No privileged request scored as public at the 0.30 threshold, and 5 of 24 public questions were held back as false alarms.

**Does each model really keep its own record?**
Yes. Pick another model in the menu next to the send button, and that person's board starts empty. Pick the first one again and the rows come back.

**Why does the other model score so badly?**
Prompts were tuned on `lfm3:1.7b` and not retuned. Treat those numbers as a first look.
