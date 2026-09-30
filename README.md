# Z&T AI Document & Email Ops Agent (n8n)

An **AI-powered automation** built in **n8n** that turns a real business's manual lead + document
handling into an end-to-end automated pipeline. When a customer inquiry or supplier invoice arrives,
the workflow **reads it, extracts the key data with an LLM, scores it, writes a grounded reply, routes
it to the right people, and logs everything to a CRM** — with error handling and auto-retry for
production reliability.

Built for a real client: **Z&T Landscape & Construction** (Rawalpindi) — [live website](https://zt-landscaping.vercel.app).

---

## The problem it solves

Z&T received customer quote requests (web form, email, WhatsApp) and supplier invoices by hand. The
owner read every message, decided which were serious, copied invoice data into a sheet, and often
replied late — so hot leads went cold and admin ate hours.

## What the automation does

1. **Ingests** a lead via **webhook** (website form) or email.
2. **Validates** the data and builds an idempotency key (duplicate protection).
3. **Extracts** structured fields from free text with an **LLM** (service, budget, timeline, location).
4. **Scores** the lead with transparent, deterministic rules → **HOT / WARM / NURTURE**.
5. **Retrieves** the company's real services & pricing (**RAG**) and has the LLM write a **grounded,
   personalized reply** — it never invents prices and politely declines out-of-scope requests.
6. **Routes**: HOT → alert the owner **and** send the client a tailored reply · WARM → auto-reply to
   the client · NURTURE → log only.
7. **Logs** every lead to an **Airtable CRM** (full audit trail); invoices go to a separate table.
8. **Error workflow** catches any failure, logs it, and emails the operator the real cause.

```
Webhook / Email
      │
   Validate + dedupe
      │
   LLM extract (Gemini)  ──▶ Score (HOT/WARM/NURTURE)
      │                          │
      │                     RAG over services/pricing
      │                          │
      │                     LLM reply (grounded, per-lead)
      │                          │
      ├──────────────▶ Route ──▶ HOT: owner alert + client reply
      │                          WARM: client reply
      │                          NURTURE: log only
      └──────────────▶ Airtable CRM (audit trail)

   (any failure) ──▶ Error workflow ──▶ log + alert with real cause
```

## Why the design is production-minded

- **Deterministic scoring** — the LLM *enriches*, it does not decide. Business logic is transparent,
  testable, and never changes based on model output.
- **RAG grounding** — replies are based only on the company's real service/pricing knowledge base.
- **Reliability** — strict JSON parsing with safe fallbacks, auto-retry on transient LLM errors, a
  dedicated error-handler workflow, and an idempotency key to prevent duplicate processing.
- **Provider-agnostic** — uses Google **Gemini** (free tier); swaps to Claude/OpenAI by changing one
  node.

## Tech stack

**n8n** (workflow automation) · **Google Gemini API** (LLM extraction + generation) ·
**Airtable** (CRM / logging) · **Gmail SMTP** (email) · **Python** (unit-tested scoring logic) ·
webhooks · REST · JSON · Docker.

## Repo layout

```
├── workflows/
│   ├── main.json            # the full lead automation (import into n8n)
│   └── error-handler.json   # the error-catching workflow
├── src/score_lead.py        # deterministic scoring (mirrors the n8n Code node)
├── tests/test_score_lead.py # unit tests for the scoring logic
├── knowledge_base/
│   └── zt-services.md        # the RAG knowledge base (real services & pricing)
├── samples/                  # example webhook payloads (hot / nurture / invoice / invalid)
├── lead-form.html            # branded web form that posts leads to the webhook
├── docker-compose.yml        # run n8n locally
├── BUILD_SPEC.md             # full technical spec
└── STEP_BY_STEP.md           # build guide
```

## Run it locally

```bash
docker compose up -d          # start n8n at http://localhost:5678
```

1. Import `workflows/main.json` and `workflows/error-handler.json` into n8n.
2. Add your own credentials (Gemini API key, Airtable token, Gmail SMTP) — see `.env.example`.
3. Create the Airtable tables (`Leads`, `Invoices`, `Errors`).
4. Open `lead-form.html`, submit a test lead, and watch it flow through to email + Airtable.

Run the scoring tests:

```bash
pip install pytest && pytest -q
```

## Note

Built as a portfolio project modeled on Z&T's real workflow. Credentials are never committed
(`.env` is git-ignored; workflow exports contain credential *references* only, no secrets).

Built by **Danish Razzaq**.
