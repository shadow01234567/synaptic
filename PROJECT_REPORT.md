firsfirst # Project Report: Google Ads API Connection Setup

## What This Project Is

This project sets up a working connection between a Python application and the
**Google Ads API**, so that ad account data (starting with account access) can
be read programmatically instead of through the Google Ads web UI.

To make an authenticated call to the Google Ads API, four things had to come
together:

1. A registered OAuth2 client in Google Cloud Console (so Google knows who is asking).
2. A one-time browser login flow that trades that OAuth client for a long-lived
   **refresh token** (so the app can re-authenticate without a browser every time).
3. A script that uses developer token + OAuth credentials + refresh token to open
   an actual `GoogleAdsClient` session and confirm the connection works.
4. A script that uses that same session to pull real data back — the list of
   Google Ads accounts (`customer` resources) accessible under our login
   customer ID.

Right now, the project can successfully connect and confirms **2 Google Ads
accounts** are accessible under login customer ID `9934468919`. Config is still
hardcoded in scripts rather than centralized in `google-ads.yaml` (planned, not
yet done).

---

## Work Breakdown — 4 People

### Person 1 — OAuth Client / Google Cloud Setup
**File:** `credentials/client_secret.json`

- Created the OAuth2 "Installed App" client in Google Cloud Console under
  project `copper-freedom-495911-c3`.
- Registered `client_id`, `client_secret`, and redirect URI (`http://localhost`).
- Deliverable: the raw client credentials file every other script depends on.
- **Status: Done.**

### Person 2 — Authentication Flow
**File:** `credentials/get_refresh_token.py`

- Wrote the one-time OAuth consent script using `google_auth_oauthlib`.
- Wired it to the `adwords` API scope (`https://www.googleapis.com/auth/adwords`).
- Ran the local server flow (port 8080) to complete browser login and generate
  the refresh token needed for all future, no-browser API calls.
- Deliverable: a valid, working refresh token.
- **Status: Done.**

### Person 3 — Connection Testing & Error Handling
**File:** `credentials/test_connection.py`

- Built the first working `GoogleAdsClient` session using developer token +
  OAuth credentials + refresh token + login customer ID.
- Added try/except error handling so failures are reported cleanly instead of
  crashing with a raw traceback.
- Debugged and fixed a `UnicodeEncodeError` caused by emoji characters
  (✅ / ❌) that Windows terminal's default `cp1252` encoding couldn't print —
  removed the emoji so the script runs cleanly on this machine.
- Deliverable: confirmed, working connection to the Google Ads API.
- **Status: Done.**

### Person 4 — Account Data Retrieval & Config Cleanup
**File:** `credentials/check_accounts.py` + `google-ads.yaml` (in progress)

- Built the script that actually lists accessible Google Ads accounts via
  `CustomerService.list_accessible_customers()`.
- Confirmed output: 2 accounts accessible under login customer ID `9934468919`.
- Responsible for the next step (not yet done): moving hardcoded credentials
  out of the Python scripts and into `google-ads.yaml`, the standard config
  file the `google-ads` library can auto-load from, so the two connection
  scripts stop duplicating the same hardcoded dict.
- **Status: Partially done — account listing works, config centralization pending.**

---

## Overall Progress

| Part | Owner | Status |
|---|---|---|
| OAuth client setup | Person 1 | Done |
| Refresh token generation | Person 2 | Done |
| Connection test + error handling | Person 3 | Done |
| Account listing | Person 4 | Done |
| `google-ads.yaml` config centralization | Person 4 | Pending |
| Remove hardcoded secrets from scripts | Person 4 | Pending |

**Estimated completion: ~85%** — core connection and data retrieval work end to
end; only config cleanup and secret handling remain.
