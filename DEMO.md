# Counsel Box: 3-minute demo

**The one line:** Don't decide what runs locally. Let the local model prove it. And let the box refuse what must never leave.

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

### 0:00 Walls (20s)
**Say:** "One box, several lawyers, one assistant. Nothing is decided in advance."

| Pane | Do | You should see |
|---|---|---|
| Daniel | Type `Summarize the Harlow deposition.` | `No document called that in your matters.` |

**Say:** "That's Maya's client. Daniel can't even learn the document exists."

### 0:20 Privileged work stays (10s)

| Pane | Do | You should see |
|---|---|---|
| Maya | Click **Summarize deposition**, Enter | `ON DEVICE · lfm3:1.7b` |

**Say:** "Privileged, so it never leaves the device."

Point at the label. Don't read the bullets aloud, because the summary runs long.

### 0:30 Maya earns it (30s)

| Pane | Do |
|---|---|
| Maya | Click **Public deadline**, Enter. Two unlabeled answers appear. Press the button below. Repeat 3 times. |

| Try | Correct answer | Press |
|---|---|---|
| 1 | December 12, 2026, Dept 330 | **Both good** |
| 2 | November 22, 2026, Dept 389 | **Both good** |
| 3 | November 19, 2026, Dept 489 | **Both good** |

**You should see:** on the Board, Maya's **Public deadline** goes from Testing to **On device**.

**Say:** "New work runs on both models, and the person picks without knowing which is which. Three right, and the cloud stops being called."

### 1:00 History is per model (10s)

| Pane | Do | You should see |
|---|---|---|
| Maya | Change the model at top right to **Liquid · lfm2.5:8b** | Maya's board empties |
| Maya | Change it back to **Liquid · lfm3:1.7b** | Her rows return |

**Say:** "Which model can do what really differs, so every model earns its own record."

**Change it back before going on.**

### 1:10 Masking (15s)

| Pane | Do |
|---|---|
| Maya | Click **Research**, Enter. Pick the answer that says **4 years, § 337**. |
| Dashboard | Press `2`, and point at `[CLIENT_1]` and the Key. Press `1` to go back. |

**Say:** "The client name never left. The key stays here, and we swap it back on device."

### 1:25 Same task, different home (35s)

| Pane | Do |
|---|---|
| Daniel | Click **Public deadline**, Enter. Three times. |

The letters are shuffled, so read the dates.

| Try | Correct answer | Press |
|---|---|---|
| 1 | 2027-01-19 | The correct one, or **Both good** if both match |
| 2 | 2027-02-24 | **The correct one.** The on-device answer is usually wrong here. |
| 3 | 2027-03-22 | The correct one, or **Both good** if both match |

**You should see:** Daniel's **Public deadline** lands in **Cloud**. Maya's stays **On device**.

**Say:** "Same task name. Maya reads a date printed on a docket. Daniel has to count four months from letters, and the small model can't do that reliably. Nobody wrote that rule. The evidence did."

### 2:00 The rest of the firm's day (5s)
Press `f` on the dashboard. The boards fill for about 60 seconds while you keep going.

### 2:05 The router refuses (15s)
Paste this into Maya's box:

```
What is the deadline to remove a case to federal court? Here is the email from our client: 'Maya, please keep this between us. We deleted the alarm log after Brightline called, and I am worried about it.'
```

**You should see:** `KEPT ON DEVICE · privileged 0.90`

**Say:** "A research question with a privileged email pasted in. It refuses to send it."

Type `Should we accept Brightline's offer?`

**You should see:** `HUMAN · Added to Ruth Abernathy's queue.`

**Say:** "A legal decision. No AI answers it."

### 2:20 Prove it (25s)
Press `3` for the audit log. Point at `Privileged text sent to cloud 0`, `Log intact`, and Daniel's blocked attempt.

Bring Terminal 3 forward.

**Say:** "This is every word that left the building. Client names are tags."

### 2:45 Close (15s)
Press `1` for the Board, now filled.

**Say:** "Liquid's d1 decides, LFM3 does the work, and privileged text never leaves. The same device fits a clinic, an accounting firm or HR. Don't decide what runs locally. Let the local model prove it."

---

## If something goes wrong

| Problem | Do this |
|---|---|
| An answer takes more than 10 seconds | Keep talking. The first call after a pause loads the model. |
| Both A and B look wrong | Press **Neither**. It goes to the human queue, which is a fine thing to show. |
| Wi-Fi drops | Say so. On-device work continues, and cloud work shows `Waiting for connection` and runs on reconnect. |
| Chat shows an error | `curl localhost:9931/health`, then rerun clean start and refresh. |
| Wrong model is selected | Switch back to `lfm3:1.7b` before pressing `f`. |
| Maya's row didn't reach On device | One pick went to the cloud. Say the evidence decided, and move on. |

---

## Say this honestly

- The firm, its matters and documents are synthetic. Every route, check and log entry on screen is real and live.
- If it's on the laptop, say so. The header shows the real machine name.
- 3 trials is a demo bar. A real firm would need far more.
- "Privileged text sent 0" means our leak test found none. d1 can misjudge, which is why thresholds lean toward privileged and hard rules back it up. This reduces risk. It doesn't replace a firm's ethics obligations.
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

**How does d1 do?**
On 144 prepared requests it picked the right kind every time, at about 0.4s median. No privileged request scored as public at the 0.30 threshold, and 5 of 24 public questions were held back as false alarms.

**Why does the other model score so badly?**
Prompts were tuned on `lfm3:1.7b` and not retuned. Treat those numbers as a first look.
