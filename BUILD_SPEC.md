# Z&T AI Document & Email Ops Agent — Full Build Spec

**Project for the application:** Associate AI Automation Engineer @ Bitzsol (Rawalpindi)
**Client (real):** Z&T Landscape & Construction, Rawalpindi — live site: https://zt-landscaping.vercel.app
**Builder:** Danish Razzaq
**Core deliverable:** a real, importable, tested **n8n Community Edition** workflow.

---

## 0. The story (what you tell HR)

Z&T gets customer quote requests (website form, email, WhatsApp) **and** supplier invoices as
email attachments. The owner reads every message by hand, decides what's serious, copies invoice
numbers into a sheet, and replies late — so hot leads go cold and admin eats hours.

This workflow sits on their inbox and handles it end to end: captures each message, uses an LLM to
**extract structured data**, checks requests against Z&T's own **services/pricing knowledge base
(RAG)**, then **routes** them — instant alert for hot quotes, auto-drafted reply for general
questions, logged invoice for accounts — with everything saved to Airtable.

**Honesty line:** "A landscaping/construction business I built the website for." True. Do NOT claim
they paid you or that it's in their production unless it is. Truthful framing: *"I built it modeled
on their real workflow; it runs in my n8n with their real service data."*

---

## 1. What this project proves (maps to the JD word-for-word)

| JD requirement | Where it shows up |
|---|---|
| n8n / automation platform | whole workflow |
| Python | `src/extract_fields.py` helper + `Code` node scoring |
| LLM API (OpenAI/Claude/Gemini) | Gemini node (Claude/OpenAI swap documented) |
| Prompt engineering | extraction + reply prompts w/ strict JSON schema |
| REST APIs, webhooks, JSON | webhook trigger, HTTP nodes, JSON everywhere |
| Document processing | reads PDF/image invoice + quote attachments |
| Data extraction | LLM pulls structured fields |
| Email handling | Gmail trigger + auto-draft/send replies |
| Basic RAG | Gemini embeddings + vector store over Z&T KB |
| AI agents | AI Agent node routes + answers with the KB as a tool |
| Chatbot | chat endpoint to query processed records |
| Testing, debugging, monitoring | scoring tests + error workflow + audit log |
| Documentation | README, architecture, schema, setup guide |
| Turn manual task into automation | the whole point |

---

## 2. Free tool stack (₨0)

- **n8n Community Edition** (self-hosted via Docker Desktop)
- **Google Gemini API** — free developer tier (default LLM + embeddings)
- **Airtable** — free workspace (CRM/log)
- **Gmail** — trigger + SMTP send (a throwaway Gmail is fine for the demo)
- **Docker Desktop** — runs n8n
- **GitHub** — public portfolio repo

> Provider swap: to use **Claude**, replace the "Google Gemini Chat Model" node with the
> "Anthropic Chat Model" node (add Anthropic credential). To use **OpenAI**, use the "OpenAI Chat
> Model" node. Nothing else changes — that's the point of keeping prompts model-agnostic.

---

## 3. Architecture

```
                         ┌─────────────────────────────┐
  Website form ─webhook─▶│                             │
  Supplier email ─Gmail─▶│   1. INGEST & NORMALIZE     │
  Customer email ─Gmail─▶│   (merge sources → 1 shape) │
                         └──────────────┬──────────────┘
                                        ▼
                         ┌─────────────────────────────┐
                         │  2. VALIDATE + DEDUPE        │
                         │  (required fields, email fmt,│
                         │   idempotency key)           │
                         └──────────────┬──────────────┘
                              valid ▼        ▼ invalid → return errors / log
                         ┌─────────────────────────────┐
                         │  3. DOC PROCESS + EXTRACT    │
                         │  (if attachment: read file → │
                         │   LLM extract fields → JSON) │
                         └──────────────┬──────────────┘
                                        ▼
                    ┌────────────────────────────────────────┐
                    │  4. CLASSIFY doc_type                    │
                    │  INQUIRY ───────────┐   INVOICE ──────┐  │
                    └─────────────────────┼─────────────────┼──┘
                          ▼ (inquiry)     │                 ▼ (invoice)
              ┌───────────────────────┐   │        ┌──────────────────┐
              │ 5a. SCORE (Python)    │   │        │ 5b. LOG INVOICE  │
              │ + RAG fit-check vs KB │   │        │ to Airtable      │
              │ → HOT/WARM/NURTURE    │   │        └──────────────────┘
              └───────────┬───────────┘   │
                          ▼               │
        ┌───────────────────────────────┐│
        │ 6. LLM ENRICH + DRAFT REPLY    ││  (RAG-grounded on Z&T services/pricing)
        │  strict JSON: summary, fit,    ││
        │  risks, next_action, subject,  ││
        │  reply_body, sales_note        ││
        └───────────────┬───────────────┘│
                        ▼                 │
        ┌───────────────────────────────┐│
        │ 7. ROUTE                        ││
        │ HOT → owner alert + draft reply ││
        │ WARM → auto-draft reply         ││
        │ NURTURE → nurture queue         ││
        └───────────────┬───────────────┘│
                        ▼                 ▼
        ┌───────────────────────────────────────────┐
        │ 8. SAVE to Airtable (audit trail)          │
        └───────────────┬───────────────────────────┘
                        ▼
        ┌───────────────────────────────────────────┐
        │ 9. CHATBOT workflow (separate): ask the     │
        │    Airtable data in natural language        │
        └────────────────────────────────────────────┘

  ⚠ Any node error ─────▶ ERROR WORKFLOW: log + alert operator (separate workflow)
```

---

## 4. n8n build — node by node (main workflow)

> Build order. Names in **bold** are the node labels to use so screenshots read well.

### A. Ingest
1. **Webhook (Website Lead)** — `POST /webhook/zt-lead`. Receives website form JSON.
2. **Gmail Trigger (Inbox)** — polls the inbox; "Download Attachments" ON.
3. **Merge / Set (Normalize)** — a `Set` (or `Code`) node that maps every source into ONE shape:
   ```json
   {
     "source": "website|email",
     "received_at": "ISO-8601",
     "from_name": "",
     "from_email": "",
     "subject": "",
     "raw_text": "",
     "has_attachment": true,
     "attachment_type": "pdf|image|none"
   }
   ```

### B. Validate + dedupe
4. **Code (Validate)** — JS node. Rules:
   - required: `from_email`, and (`raw_text` OR attachment)
   - email format regex
   - build **idempotency_key** = sha1(`from_email` + subject + date(day)). (crypto in Code node)
   - output `{ valid: true/false, errors: [], idempotency_key }`
5. **IF (Valid?)** — false branch → **Respond / Log invalid** (webhook responds 400 with errors;
   email branch just logs). true branch continues.
6. **Airtable (Dedupe lookup)** — search `Leads` for the idempotency_key. If found → **NoOp / Stop**
   (do not re-alert). Prevents duplicate processing.

### C. Document processing + extraction
7. **IF (Has attachment?)**
   - **PDF** → **Extract from File** node (PDF) → text.
   - **Image** → send to **Gemini (vision)** to read it (Gemini handles images) OR an OCR step.
   - no attachment → use `raw_text`.
8. **Google Gemini Chat Model** + **Basic LLM Chain (Extract)** — feed the text, use the
   **Extraction prompt** (section 5). Output MUST be JSON matching the schema.
9. **Code (Parse + validate JSON)** — `JSON.parse` inside try/catch. On failure → set
   `extraction_ok=false` and fall back to a minimal record (never crash the run).

### D. Classify
10. **Switch (doc_type)** — routes on `doc_type` = `inquiry` | `invoice`.

### E-inquiry. Score + RAG + enrich
11. **Code (Score lead)** — deterministic scoring (section 6) → `score`, `qualification`,
    `score_reasons[]`.
12. **RAG sub-chain** (grounds the AI in Z&T's real services/pricing):
    - **Google Gemini Embeddings** → **In-Memory Vector Store** loaded from
      `knowledge_base/zt-services.md` (chunked). (Load once via a "Insert" run, or a
      Default Data Loader node at start.)
    - **Vector Store Retriever** → returns top-k relevant KB chunks for the inquiry.
13. **AI Agent (Enrich + Reply)** — model = Gemini; tool = the retriever; use the **Reply prompt**
    (section 5). Output strict JSON:
    `{ ai_summary, fit_reason, risks[], recommended_action, email_subject, reply_body, sales_note }`.
14. **Code (Validate LLM JSON)** — schema check + fallback (same pattern as node 9).

### E-invoice. Log
11b. **Set (Invoice record)** — map extracted invoice fields.
12b. **Airtable (Create Invoice row)** — into an `Invoices` table (section 8).

### F. Route (inquiry branch)
15. **Switch (qualification)**: HOT / WARM / NURTURE
    - **HOT** → **Gmail (Alert owner)** to Zahid (`zahidkingpk@gmail.com`) + **Gmail (Draft reply)**
      to customer (draft, not auto-send, for hot — human touch).
    - **WARM** → **Gmail (Send auto-reply)** using `reply_body`.
    - **NURTURE** → **Airtable (add to Nurture view)** / tag only, no email.

### G. Persist
16. **Airtable (Create/Update Lead row)** — full record + audit fields (section 8).
17. **Respond to Webhook** — return `{ status, score, qualification }` for website source.

### H. Errors (separate workflow)
- **Error Trigger** → **Code (format error)** → **Gmail (alert operator)** + **Airtable (Errors
  log)**. Set this workflow as the "Error Workflow" in the main workflow's settings.

### I. Chatbot (separate workflow)
- **Chat Trigger** (n8n chat) → **AI Agent** with an **Airtable tool** (or a "get records" HTTP tool)
  → answers questions like *"show this week's HOT leads"* / *"what did Ali ask for?"*.

---

## 5. Prompts (model-agnostic, strict JSON)

### 5.1 Extraction prompt
```
You are a precise data-extraction engine for a landscaping & construction business (Z&T).
From the MESSAGE below, extract ONLY facts that are present. Do not invent values.
Return STRICT JSON, no markdown, matching this schema exactly:

{
  "doc_type": "inquiry" | "invoice",
  "from_name": string|null,
  "from_email": string|null,
  "phone": string|null,
  "service_requested": "waterproofing"|"swimming_pools"|"landscape_design"|"building_works"|"other"|null,
  "location": string|null,
  "budget_pkr": number|null,
  "timeline_days": number|null,
  "company_size": "individual"|"small"|"medium"|"large"|null,
  "decision_authority": "yes"|"no"|"unknown",
  "message_summary": string,
  "invoice": {
     "supplier": string|null,
     "invoice_no": string|null,
     "amount_pkr": number|null,
     "due_date": string|null,
     "line_items": [ { "item": string, "qty": number|null, "price_pkr": number|null } ]
  } | null
}

Rules:
- If it's a customer asking for work/quote → doc_type="inquiry", invoice=null.
- If it's a supplier bill/PO → doc_type="invoice", fill invoice{}, service_requested=null.
- Missing value → null. Never guess. Output JSON only.

MESSAGE:
"""{{ $json.text }}"""
```

### 5.2 Reply/enrichment prompt (RAG-grounded)
```
You are the assistant for Z&T Landscape & Construction, Rawalpindi.
Use ONLY the CONTEXT (the company's real services & pricing) to judge fit and write the reply.
If the request is outside our services, say so politely and don't promise it.

Return STRICT JSON only:
{
  "ai_summary": string,            // 1 sentence
  "fit_reason": string,            // why this lead fits / doesn't, grounded in CONTEXT
  "risks": string[],               // e.g. "budget below our minimum", "location far"
  "recommended_action": string,    // what sales should do next
  "email_subject": string,
  "reply_body": string,            // polite, professional, ready to send; sign as "Z&T Team"
  "sales_note": string             // internal note for the owner
}

CONTEXT (Z&T services & pricing):
"""{{ retrieved_chunks }}"""

LEAD:
"""{{ $json.extracted }}"""

Constraints: temperature low. No markdown. JSON only. Don't fabricate prices not in CONTEXT.
```

---

## 6. Deterministic scoring (Python + JS)

Keep the **business decision deterministic** (the LLM enriches, it does NOT decide the score).

| Factor | Max | Rule |
|---|--:|---|
| Budget | 25 | ≥500k→25, 200–499k→18, 50–199k→10, <50k→4, null→0 |
| Timeline | 20 | ≤14d→20, 15–30d→14, 31–90d→8, >90d→3, null→0 |
| Service match | 20 | one of our 4 services→20, "other"→5, null→0 |
| Location | 15 | Rawalpindi/Islamabad→15, nearby→8, far→3, null→0 |
| Decision authority | 10 | yes→10, unknown→4, no→0 |
| Completeness | 10 | +2 each for name, email, phone, budget, timeline present |

**Total 100** → `HOT 70–100`, `WARM 45–69`, `NURTURE 0–44`.

Provide it BOTH as a `Code` node (JS) inside n8n AND as `src/score_lead.py` (Python) with tests, so
you satisfy the "solid Python" requirement and have unit tests to show.

---

## 7. RAG knowledge base

`knowledge_base/zt-services.md` — seed with Z&T's **real** services (from their site):

```
# Z&T Landscape & Construction — Services & Pricing (internal KB)

## Waterproofing
Roof, basement, water-tank waterproofing. Typical projects PKR 60,000–400,000 depending on area.
Service area: Rawalpindi & Islamabad (travel charge beyond 40km).

## Swimming Pools
Design + construction of residential pools. Starting ~PKR 1,500,000. Timeline 6–12 weeks.

## Landscape Design
Garden design, lawns, hardscaping, irrigation. PKR 80,000–600,000. Timeline 2–6 weeks.

## Building Works
Renovation, boundary walls, small construction. Quoted per site visit.

## Policy
Minimum project value PKR 50,000. Free site survey within Rawalpindi/Islamabad.
Contact: WhatsApp +92 333 5158897 · zahidkingpk@gmail.com
```

Chunk by heading → embed with Gemini embeddings → in-memory vector store. The retriever pulls the
right service section so replies quote **real** ranges, not hallucinations.

---

## 8. Airtable schema

**Table `Leads`:** Lead ID, Received At, Source, From Name, From Email, Phone, Service Requested,
Location, Budget PKR, Timeline Days, Company Size, Decision Authority, Score, Qualification,
Score Reasons, AI Summary, Fit Reason, Risks, Recommended Action, Email Subject, Reply Body,
Sales Note, Idempotency Key, Workflow Version, Status.

**Table `Invoices`:** Invoice ID, Received At, Supplier, Invoice No, Amount PKR, Due Date,
Line Items (JSON), Source Email, Workflow Version.

**Table `Errors`:** Time, Workflow, Node, Message, Payload (truncated).

---

## 9. Repo structure

```
zt-ai-ops-agent/
├── workflows/
│   ├── main-demo.json            # runs with no real creds (mock LLM + no send)
│   ├── main-production.json      # real Gmail/Gemini/Airtable
│   ├── chatbot.json
│   └── error-handler.json
├── src/
│   └── score_lead.py
├── tests/
│   └── test_score_lead.py        # 4+ cases: hot, warm, nurture, invalid
├── knowledge_base/
│   └── zt-services.md
├── samples/
│   ├── inquiry-hot.json
│   ├── inquiry-nurture.json
│   ├── invoice.json
│   └── invalid.json
├── docs/
│   ├── architecture.md           # the diagram + explanation
│   ├── airtable-schema.md
│   └── setup-guide.md
├── screenshots/
├── demo-video/
├── docker-compose.yml            # n8n Community Edition
├── .env.example                  # keys as placeholders — NEVER real
├── .gitignore                    # ignore .env, credentials
└── README.md
```

---

## 10. Proof checklist (do ALL before applying)

- [ ] Workflows import cleanly into current n8n release
- [ ] HOT inquiry → correct score + owner alert + draft reply
- [ ] NURTURE inquiry → tagged, no email
- [ ] Invoice attachment → fields extracted → Invoices row created
- [ ] Invalid payload → rejected with errors
- [ ] Duplicate submission → no second alert (idempotency works)
- [ ] LLM returns valid JSON; malformed JSON → fallback (test by forcing bad output)
- [ ] RAG reply quotes a REAL Z&T price range from the KB
- [ ] Error workflow deliberately triggered and shown
- [ ] `pytest` — 4 scoring tests pass
- [ ] No secrets in the repo (grep for keys before pushing)
- [ ] README has architecture + setup
- [ ] 60–90s screen recording of the whole flow running

---

## 11. Application package (fill after it works — keep truthful)

**Email to:** hr.bitzsol@gmail.com
**Subject:** Application for Associate AI Automation Engineer

**3–5 line project description:**
> I built an n8n automation for a landscaping & construction business I work with. They were manually
> reading every customer inquiry and supplier invoice by email and replying late, so hot leads went
> cold. My workflow captures each message, uses an LLM to extract the details, checks the request
> against the company's own services/pricing with a small RAG step, then routes it — instant alert for
> serious quotes, auto-drafted reply for general questions, and a logged record in Airtable. I added
> validation, JSON-schema fallback for the AI output, an error workflow, and tests so it stays reliable.

**CV bullets (truthful):**
- Built a production-style **n8n** automation that ingests emails/webhooks, extracts document data
  with an **LLM**, and routes leads via deterministic scoring + **RAG**-grounded replies.
- Integrated **Gemini API** (swappable to Claude/OpenAI) with strict JSON schemas, fallback handling,
  idempotent dedupe, and an error-alerting workflow.
- Added **Python** unit tests for scoring logic and full setup/architecture docs; secrets kept out of Git.

**Demo video script (60–90s):**
1. (0–10s) "This is an n8n automation I built for Z&T, a landscaping business." Show the canvas.
2. (10–35s) Fire a HOT inquiry (Postman/website) → show it flow: validate → extract → score HOT →
   owner alert email + drafted reply grounded in real pricing.
3. (35–55s) Drop a supplier invoice email → show extracted fields land in Airtable.
4. (55–75s) Send an invalid + a duplicate → show rejection + no double alert. Trigger an error →
   show the error alert. "Tests pass, no secrets in repo."
5. End on the GitHub README.

---

## 12. Build order (fastest path)
1. Docker up n8n → 2. Airtable tables → 3. normalize+validate+dedupe → 4. extraction (Gemini) →
5. scoring (Code + Python tests) → 6. KB + RAG retriever → 7. enrich/reply agent → 8. routing +
Gmail → 9. Airtable persist → 10. error workflow → 11. chatbot → 12. docs + demo video.

Ship demo mode first (no creds), then wire real Gmail/Gemini/Airtable.
```
