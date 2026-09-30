# Z&T AI Ops Agent — Complete Step-by-Step Build Guide (Beginner)

Follow this top to bottom. Every file you need is already in this folder. When a step says
"tell Claude," pause and message me — I'll give you the exact node settings or fix errors.

Legend: 🖱️ = do this click · 💬 = ask Claude when here · ✅ = checkpoint (should work before moving on)

---

# PART 1 — Get n8n running (≈20 min)

We run n8n on your own PC with Docker. (This gives you the `docker-compose.yml` deliverable that
HR likes to see.)

### 1.1 Install Docker Desktop
🖱️ Download from https://www.docker.com/products/docker-desktop/ → install → restart PC if it asks.
🖱️ Open **Docker Desktop**. Wait until the little whale icon (bottom-left) is green = "Engine running."

> If Docker gives WSL2 errors on Windows: open PowerShell as admin, run `wsl --install`, restart, then
> open Docker Desktop again. 💬 If it still fails, tell me the exact error.

### 1.2 Start n8n
🖱️ Open a terminal in this folder. Easiest way: open the folder
`C:\Users\USER\Desktop\Career\zt-ai-ops-agent` in File Explorer, click the address bar, type `cmd`,
press Enter.

In that terminal, run:
```
docker compose up -d
```
Wait ~1 minute (first time downloads n8n).

### 1.3 Open n8n
🖱️ In your browser go to: **http://localhost:5678**
🖱️ First time: it asks you to create a local owner account (name, email, password). This is just for
your local n8n — use anything you'll remember. Write it down.

✅ You should see the empty n8n canvas (a blank "Workflows" area).

💬 Tell me "n8n is open" and I'll walk you into Part 3 live if you want.

---

# PART 2 — Get your free keys (≈15 min)

### 2.1 Gemini API key (free)
🖱️ Go to https://aistudio.google.com/apikey → sign in with any Google account → **Create API key** →
copy it.
🖱️ Open the file `.env.example` in this folder, **save a copy named `.env`**, paste your key after
`GEMINI_API_KEY=`.

### 2.2 Airtable (free CRM)
🖱️ Sign up at https://airtable.com (free).
🖱️ Create a new **Base** named `Z&T Ops`.
🖱️ Get a token: https://airtable.com/create/tokens → **Create token** → name it `n8n` → scopes:
`data.records:read`, `data.records:write`, `schema.bases:read` → access: your `Z&T Ops` base → Create →
copy token into `.env` after `AIRTABLE_TOKEN=`.
🖱️ Base ID: open your base, look at the URL — it starts with `app...`. Copy that into
`AIRTABLE_BASE_ID=`.

### 2.3 Gmail (for triggers + sending)
Use a **throwaway Gmail** (don't use your main one for a demo). You'll connect it inside n8n in Part 4
— no key needed now, just have the login ready.

✅ `.env` now has 3 things filled: GEMINI_API_KEY, AIRTABLE_TOKEN, AIRTABLE_BASE_ID.

---

# PART 3 — Build the Airtable tables (≈10 min)

In your `Z&T Ops` base, make **3 tables** (🖱️ click the "+" next to table tabs):

**Table 1: `Leads`** — add these fields (all "Single line text" unless noted):
Lead ID · Received At · Source · From Name · From Email · Phone · Service Requested · Location ·
Budget PKR (Number) · Timeline Days (Number) · Company Size · Decision Authority · Score (Number) ·
Qualification (Single select: HOT, WARM, NURTURE) · Score Reasons (Long text) · AI Summary (Long text)
· Fit Reason (Long text) · Risks (Long text) · Recommended Action (Long text) · Email Subject ·
Reply Body (Long text) · Sales Note (Long text) · Idempotency Key · Status (Single select: New,
Alerted, Replied, Queued)

**Table 2: `Invoices`** — Invoice ID · Received At · Supplier · Invoice No · Amount PKR (Number) ·
Due Date · Line Items (Long text) · Source Email

**Table 3: `Errors`** — Time · Workflow · Node · Message · Payload (Long text)

✅ 3 tables exist. 💬 Tell me and I'll confirm field names match what the workflow expects.

---

# PART 4 — Build the workflow in n8n

This is the heart. We build it in small blocks and TEST each block. Don't try to do it all at once.
For each block I give you the nodes; when you add a node, 💬 tell me its name and I'll give you the
exact settings to paste. n8n changes its UI sometimes, so we do this together.

> How to add a node: 🖱️ click the **"+"** on the canvas (top-right or on a connector), search the node
> name, click it.

### Block A — Receive a test lead (start simple)
1. Add node **"Manual Trigger"** (called "Trigger manually"). This lets us test by clicking "Execute."
2. Add node **"Edit Fields (Set)"** → we'll paste one sample lead (from `samples/inquiry-hot.json`)
   so we have data to work with before touching email.
✅ Click **Execute Workflow** → you see the sample lead data flow out of the Set node.

### Block B — Validate + dedupe
3. Add **"Code"** node named **Validate**. 💬 I'll give you the JS (checks email, required fields,
   builds the idempotency key).
4. Add **"If"** node → condition `valid = true`.
5. On the TRUE branch add **"Airtable"** node (Search) named **Dedupe** → looks up the idempotency key
   in `Leads`. 💬 I'll give exact settings + how to add your Airtable token as a credential.

### Block C — Extract fields with Gemini
6. Add **"Google Gemini Chat Model"** node → 💬 I'll show you where to paste your Gemini key as a
   credential.
7. Add **"Basic LLM Chain"** node named **Extract** → connect the Gemini model to it → paste the
   **Extraction prompt** (I'll give it). Output = JSON of the lead's fields.
8. Add **"Code"** node **Parse JSON** → safely parses the AI output (with fallback if it's malformed).

### Block D — Score + ground the reply (RAG)
9. Add **"Code"** node **Score** → 💬 I'll paste the JavaScript version of the scoring (same logic as
   `src/score_lead.py`, which already passes its tests).
10. RAG (grounding on Z&T services):
   - **Simple version (we'll do this first, it always works):** add a **"Read/Write Files from Disk"**
     node to read `/data/knowledge_base/zt-services.md`, then inject that text into the reply prompt.
   - **Level-up (recommended for your CV, do after the simple one works):** swap to real vector RAG:
     **Google Gemini Embeddings** → **Simple Vector Store (In-Memory)** → **Vector Store Retriever**,
     fed into an **AI Agent**. 💬 I'll guide this when you're ready — it's the piece that lets you
     truthfully say "RAG pipeline" on your CV.
11. Add **"Basic LLM Chain"** (or **AI Agent**) named **Enrich+Reply** → 💬 paste the **Reply prompt**.
    Output JSON: ai_summary, fit_reason, risks, recommended_action, email_subject, reply_body,
    sales_note.
12. Add **"Code"** node **Validate LLM JSON** → schema check + fallback.

### Block E — Route by qualification
13. Add **"Switch"** node on `qualification`: HOT / WARM / NURTURE.
   - HOT → **Gmail** (Send: alert to OWNER_EMAIL) + **Gmail** (Create Draft: reply to customer).
   - WARM → **Gmail** (Send: auto-reply using reply_body).
   - NURTURE → just continue (no email).
   💬 I'll walk you through connecting Gmail (OAuth popup — you approve it once).

### Block F — Save everything
14. Add **"Airtable"** node (Create) named **Save Lead** → maps all fields into `Leads`.

### Block G — Invoices branch
Back at the Extract step, when `doc_type = invoice`: add a **Switch** earlier (on doc_type) so invoices
go to their own **Airtable (Create)** into `Invoices` instead of scoring. 💬 I'll show the wiring.

### Block H — Error workflow (separate)
15. New workflow → **"Error Trigger"** → **Code (format)** → **Gmail (alert)** + **Airtable (Errors)**.
    Then in the MAIN workflow settings → set this as the "Error Workflow." 💬 I'll give the code.

### Block I — Email trigger (go live)
16. Once the Manual-Trigger version works end to end, replace the Manual Trigger with:
    - **"Gmail Trigger"** (new email) — for real inbox processing, and/or
    - **"Webhook"** node — so the Z&T website form can POST leads.
    💬 We do this LAST, after everything else is tested.

---

# PART 5 — Test it (the proof HR wants)

Run each of these and confirm:
- [ ] `samples/inquiry-hot.json` → Score ~94, **HOT**, owner alert + draft reply created
- [ ] `samples/inquiry-nurture.json` → low score, **NURTURE**, no email, reply politely declines
      (it asks for furniture/interior — which our KB says we DON'T do)
- [ ] `samples/invoice.json` → goes to **Invoices** table with amount 93,500
- [ ] `samples/invalid.json` → rejected with validation errors (no crash)
- [ ] Send the SAME hot lead twice → second time = no duplicate alert (dedupe works)
- [ ] Force a bad AI output once → fallback handles it (no crash)
- [ ] Trigger the error workflow on purpose → you get the error alert
- [ ] `pytest -q` in this folder → **4 passed** (already verified ✅)

💬 Tell me which ones fail and paste the n8n error — I'll fix.

---

# PART 6 — Put it on GitHub (portfolio)

1. Export each workflow: 🖱️ in n8n open the workflow → top-right "⋯" → **Download** → save into the
   `workflows/` folder (name them main-production.json, main-demo.json, chatbot.json,
   error-handler.json).
   ⚠️ Before saving to Git, **remove credentials** — n8n export keeps credential *references* but
   double-check no keys are inside. 💬 I'll show you how to scrub them.
2. Make sure `.env` is NOT included (`.gitignore` already blocks it — good).
3. Create a GitHub repo `zt-ai-ops-agent` (public) → push this whole folder.
   💬 I'll give you the exact git commands and a scan to confirm no secrets leaked.
4. 💬 I'll write your polished `README.md` (with the architecture diagram) once the workflows are final.

---

# PART 7 — Record the demo video (60–90s)

Screen-record (Windows: `Win + Alt + R`) following the script in `BUILD_SPEC.md` section 11:
hot lead → invoice → invalid+duplicate → error → tests pass → GitHub README.
Save as `demo-video/demo.mp4`. 💬 I'll tighten the script/voiceover for you.

---

# PART 8 — Apply

Email **hr.bitzsol@gmail.com**, subject **"Application for Associate AI Automation Engineer"**, with:
- Your CV (💬 I'll tailor it for this role)
- GitHub repo link
- The 3–5 line description (ready in `BUILD_SPEC.md` section 11)

---

## Your very next 3 actions
1. Install Docker Desktop + run `docker compose up -d` (Part 1).
2. Get the Gemini + Airtable keys into `.env` (Part 2).
3. 💬 Come back and say "n8n is open" — then we build Block A together, live.

Everything else (all code, prompts, node settings) I hand you as you reach each step. You never write
code — you click, I supply.
