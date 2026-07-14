# CLAUDE.md

## Project Identity

**Project Name:** Synaptic
**Type:** AI-Powered Google Ads Automation System
**Role of Claude:** Lead Developer — writes, reviews, debugs, and architects all code
**Team:** 4 FYP students
**Status:** Phase 1 Complete — Infrastructure & Authentication fully operational

---

## What Is Synaptic

Synaptic is a fully automated Google Ads management system powered by AI. It removes
the need for a business owner to manually manage their campaigns. The owner provides
only a business description — Synaptic handles everything else automatically.

---

## Repository Structure

```
synaptic/
├── CLAUDE.md                        ← This file
├── google-ads.yaml                  ← Central credentials config
├── main.py                          ← Orchestrates all agents
├── credentials/
│   ├── client_secret.json           ← OAuth2 client (Google Cloud)
│   ├── get_refresh_token.py         ← One-time OAuth login flow
│   ├── test_connection.py           ← Verifies API connection
│   └── check_accounts.py            ← Lists accessible ad accounts
└── agents/
    ├── keyword_agent.py             ← Phase 2 — in progress
    ├── competitor_agent.py          ← Phase 3 — planned
    ├── ad_writing_agent.py          ← Phase 4 — planned
    ├── campaign_agent.py            ← Phase 5 — planned
    └── reporting_agent.py           ← Phase 6 — planned
```

---

## Running the Scripts

```bash
python credentials/get_refresh_token.py   # One-time OAuth login, prints refresh token
python credentials/test_connection.py     # Verify GoogleAdsClient connects
python credentials/check_accounts.py      # List accessible Google Ads accounts
python main.py                            # Run full Synaptic pipeline (Phase 2+)
```

---

## Architecture & Data Flow

```
client_secret.json  +  google-ads.yaml  +  Developer Token
                          ↓
                  GoogleAdsClient connects
                          ↓
          keyword_agent → competitor_agent → ad_writing_agent
                          ↓
          campaign_agent → reporting_agent → Streamlit Dashboard
```

---

## Authentication — Two Credential Systems

**OAuth 2.0** — proves Synaptic's identity to Google
- client_id, client_secret → who Synaptic is
- refresh_token → keeps Synaptic connected automatically without re-login

**Developer Token** — proves Synaptic has permission to use Google Ads API
- Obtained from Google Ads → Tools & Settings → API Center

Both required. Neither works without the other.

---

## google-ads.yaml — Central Config

All scripts must load credentials from here:
```python
client = GoogleAdsClient.load_from_storage("google-ads.yaml")
```

**Known gap:** scripts currently hardcode credentials inline.
Migrating to `google-ads.yaml` is the immediate next step.

---

## Dependencies

```bash
pip install google-ads google-auth-oauthlib anthropic pandas streamlit
```

No `requirements.txt` configured yet.

---

## Phase Status

| Phase | Task                        | Status      |
|-------|-----------------------------|-------------|
| 1     | Setup & Authentication      | Complete    |
| 2     | Keyword Research Agent      | In Progress |
| 3     | Competitor Research Agent   | Planned     |
| 4     | Ad Writing Agent            | Planned     |
| 5     | Campaign Manager Agent      | Planned     |
| 6     | Reporting + Dashboard       | Planned     |
| 7     | Integration & Testing       | Planned     |

---

## Claude's Role as Lead Developer

Claude writes all code, makes all architectural decisions, debugs all errors,
and guides the 4-student team step by step. Students run the code and report
results — Claude iterates and builds.

When working in this repo, Claude must:
- Read this file before writing or modifying any code
- Build and fully test one agent before moving to the next
- Write clean, commented Python that students can understand
- Never expose credentials in output, logs, or terminal prints

---

## Security

**Treat the entire `credentials/` directory as sensitive.**
Contains live OAuth client secret, developer token, and refresh token in plaintext.

Never commit, share, or print any file from `credentials/`.

`.gitignore` must include:
```
credentials/
google-ads.yaml
*.json
```