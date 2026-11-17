# Thuyan — Solid Waste Management WhatsApp Bot

A WhatsApp chatbot for The Nilgiris district that collects solid waste
complaints from citizens and routes them to the District Collector.

Built with the Meta WhatsApp Cloud API, FastAPI, PostgreSQL and ngrok. The
bot is bilingual (English / Tamil), runs a guided complaint flow using
WhatsApp interactive list and button messages, and currently runs locally
against a Meta test number.

> **Status as of 2026-10-23:** completed complaints are saved to PostgreSQL
> with a reference number, assigned to the officer for that local body, and
> sent to the officer on WhatsApp. Officers resolve a complaint by replying
> with a photo, and the citizen is told. Photos are stored in Supabase
> Storage. A read-only admin dashboard (`admin-ui/`) and a pytest suite
> (`tests/`) are in place. Still open: a restart test, officer escalation,
> and Tamil review. See sections 12, 13 and 16.

---

# 1. Current Architecture

```
Citizen
   |  WhatsApp message
   v
Meta WhatsApp Cloud API
   |  POST /webhook
   v
ngrok  (development tunnel)
   |
   v
FastAPI  ->  webhook.py           parse + route the incoming message
             conversation_manager load the user's state from the DB, persist it after
             chatbot_service      state machine, decides what happens next
             messages.py          all user-facing copy, English + Tamil
             local_bodies.py      Nilgiris local body data + list paging
             whatsapp_service     build and send the outbound payload
             db/complaints.py     save a complaint, reference numbers, officer lookup
             officer_service      alert the officer, handle their resolution reply
             storage.py           copy WhatsApp photos into Supabase Storage
             api/admin.py         read-only /admin/api/* for the dashboard
             PostgreSQL           complaints, officers, conversation_state
   |
   v
Meta WhatsApp Cloud API
   |
   v
Citizen
```

Each webhook call loads the sender's conversation from the
`conversation_state` table, handles the message, then writes the
conversation back (or deletes it once it is finished). A completed
complaint is saved to `complaints` in the same request, assigned to the
officer for its local body, and the officer is alerted before the citizen's
receipt is sent.

---

# 2. Conversation Flow

```
any message
   -> language prompt  (the only bilingual screen: English / தமிழ்)
   -> complaint menu          list, 6 options
   -> [typed complaint]       only if "Type your complaint" chosen
   -> local body type         list: Municipality / Town Panchayat / Village Panchayat
   -> [block]                 list, only for Village Panchayat
   -> local body              list, paged
   -> ward number             free text, digits required
   -> location                typed text or a shared WhatsApp location pin
   -> photo?                  buttons Yes / No
   -> [photo upload]
   -> confirmation            receipt with the complaint reference number
```

After the language is chosen, **every screen is in that language only**.
Sending `hi` after a completed complaint clears the stored language and
starts again from the language prompt.

Restart keywords: `hi`, `hello`, `start`, `new complaint`, `வணக்கம்`,
`புதிய புகார்`.

Buttons and typing both work at every step — a citizen can tap a list row
or type `english`, `2`, `Hulical`, `ஆம்` and so on.

## Conversation states

Defined in `app/state/conversation_state.py`:

```
START
WAITING_FOR_LANGUAGE
WAITING_FOR_COMPLAINT
WAITING_FOR_CUSTOM_COMPLAINT
WAITING_FOR_LOCAL_BODY_TYPE
WAITING_FOR_BLOCK
WAITING_FOR_LOCAL_BODY
WAITING_FOR_WARD
WAITING_FOR_LOCATION
ASKING_FOR_PHOTO
WAITING_FOR_PHOTO
COMPLETED
```

---

# 3. Languages

All user-facing text lives in `app/services/messages.py`, keyed by
language (`en` / `ta`). Nothing is hardcoded in the handlers.

The chosen language is stored separately from the conversation data so a
mid-flow reset does not lose it.

**Place names stay in Latin script in both languages.** Local body and
block names are official names and are not transliterated; only the
labels around them are translated (`நகராட்சி`, `பேரூராட்சி`, `ஊராட்சி`,
`ஒன்றியம்`). Tamil translations throughout still need review by a native
speaker before going live.

## Tamil and the length limits

WhatsApp enforces length caps on interactive fields and rejects the whole
message with `400 (#131009)` if any field is over. The caps count **code
points**, and Tamil spends roughly twice as many code points as it shows
glyphs — `வண்டி` is 3 visible characters but 5 code points. A 24-cap
field therefore holds only about 13–15 visible Tamil characters.

| Field | Cap |
|---|---|
| list row title | 24 |
| list row description | 72 |
| section title | 24 |
| header / footer | 60 |
| body | 1024 |
| list action button | 20 |
| reply button title | 20 |
| rows per list | **10** |
| sections per list | 10 |

`messages.py` checks every one of these **at import time**, including all
50 place names. An over-long string therefore fails at startup with a
clear message, rather than as a 400 on a live citizen's message.

**Windows console note:** printing Tamil under the default `cp1252`
codepage raises `UnicodeEncodeError` and crashes the handler. The debug
configs in `.vscode/launch.json` set `PYTHONUTF8=1`. If you start uvicorn
from a plain terminal, run `$env:PYTHONUTF8=1` first.

---

# 4. Local Bodies

`app/services/local_bodies.py` holds all **50** Nilgiris local bodies from
the SWM district export, plus the paging logic.

| Type | Count | How it is shown |
|---|---|---|
| Municipality | 5 | one list |
| Town Panchayat | 10 | one list (exactly at the 10-row cap) |
| Village Panchayat | 35 | block step, then a paged list |

Village panchayats cannot fit one list, and splitting by block still
leaves Ooty at 13 and Kotagiri at 11 — both over the cap. So any list
longer than 10 keeps its last row for a **More options** row:

```
Ooty village panchayats
  page 1: Balacola ... Kundha  + [More options]   (10 rows)
  page 2: Mulligoor, Nanjanad, Thummanatty, Thuneri
```

The paginator is generic, so added local bodies produce extra pages
automatically — including Town Panchayat, which is sitting exactly on the
cap and would otherwise break on the 11th entry.

Data cleanups applied to the source export: trailing spaces trimmed, the
`Village Panchyat` typo on the Gudalur rows normalised, and the lowercase
Coonoor names title-cased.

---

# 5. Project Structure

```
Solid-Waste WACB/
│
├── app/
│   ├── main.py                      FastAPI app
│   │
│   ├── api/
│   │   ├── webhook.py               GET verify + POST receive, routing, save on completion
│   │   └── admin.py                 read-only /admin/api/* for the dashboard
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py                settings from .env (pydantic-settings)
│   │
│   ├── db/
│   │   ├── models.py                Complaint, Officer, ConversationStateRow
│   │   ├── session.py               async engine + session factory
│   │   └── complaints.py            save_complaint, reference numbers, officer lookup, mark_resolved
│   │
│   ├── services/
│   │   ├── chatbot_service.py       state machine
│   │   ├── messages.py              all copy, en/ta, + limit validation
│   │   ├── local_bodies.py          local body data + paging
│   │   ├── officer_service.py       officer alerts and resolution replies
│   │   ├── storage.py               WhatsApp photo -> Supabase Storage
│   │   └── whatsapp_service.py      outbound payload builders (text, list, button, template, image)
│   │
│   └── state/
│       ├── conversation_manager.py  load/persist a user's conversation via the DB
│       └── conversation_state.py    state enum
│
├── admin-ui/                        React + Vite admin dashboard
├── tests/                           pytest suite
├── alembic/                         migrations (versions/)
├── alembic.ini
├── .vscode/launch.json              debug configs
├── check_db.py                      prints tables and columns, a connection check
├── seed_officers.py                 one test officer per local body
├── test_send.py                     manual outbound send check
├── pytest.ini
├── requirements-dev.txt             pytest, pytest-asyncio, aiosqlite
├── .venv/
├── .env                             secrets — never commit
├── requirements.txt
└── README.md
```

---

# 6. Requirements

- Python 3.10+
- VS Code
- ngrok
- Node.js 18+ (only for the admin dashboard)
- A Supabase project with a storage bucket (photo storage)
- PostgreSQL 14 (local is in use; `Whatsapp_ChatBot` database on `localhost:5432`)
- Meta Developer Account with a WhatsApp Cloud API app
- Meta WhatsApp test number, WABA, Phone Number ID, access token

---

# 7. Environment Variables

Create `.env` in the project root:

```
VERIFY_TOKEN=your_webhook_verify_token
WHATSAPP_ACCESS_TOKEN=your_meta_access_token
PHONE_NUMBER_ID=your_phone_number_id
DATABASE_URL=postgresql://user:password@localhost:5432/Whatsapp_ChatBot
DB_SSL=false
OFFICER_TEMPLATE_NAME=new_complaint_alert
OFFICER_TEMPLATE_LANG=en
ADMIN_TOKEN=optional_token_for_the_admin_api
SUPABASE_URL=https://YOUR-PROJECT.supabase.co
SUPABASE_SECRET_KEY=your_supabase_service_key
SUPABASE_BUCKET=complaint-photos
LOG_LEVEL=INFO
LOG_JSON=false
```

`LOG_LEVEL` is `DEBUG`, `INFO`, `WARNING` or `ERROR`. Every log line carries a
per-request id (also returned in the `X-Request-ID` header) and the user's
phone number with all but the last four digits masked. Set `LOG_JSON=true` for
one JSON object per line. Tokens and message text are never logged.

`ADMIN_TOKEN` is optional but should be set before the server is exposed
(see the Admin dashboard section). `SUPABASE_BUCKET` defaults to
`complaint-photos`; a `/rest/v1` suffix on `SUPABASE_URL` is stripped.

**Officer alert template.** WhatsApp only allows plain text within 24 hours
of the recipient last messaging the bot. Otherwise the alert falls back to
an approved template. Create it in Meta Business Manager (category
Utility) with this body, and put its name and language in `.env`:

```
New complaint {{1}}
Type: {{2}}
Area: {{3}}
Map: {{4}}

Reply to this message with a photo of the resolved issue.
```

Officers can resolve a complaint by swipe-replying to its alert with a
photo, with no reference number needed. See the next section.

`DATABASE_URL` is stored in plain `postgresql://` form. `config.py`
derives two variants from it: `postgresql+asyncpg://` for the app and
`postgresql+psycopg2://` for Alembic.

**Do not append `?sslmode=require`.** That is a psycopg2 option and
asyncpg crashes on it. Use `DB_SSL=true` instead — the app adds
`sslmode` for Alembic and passes `ssl` to asyncpg itself.

**Known issue:** the current `.env` produces
`python-dotenv could not parse statement starting at line 7` on every
start. Line 7 is a stray entry (it looks like an old `test_url=` line).
Remove it, or wrap any value containing spaces or `#` in double quotes.

Never commit `.env`. `.gitignore` should contain:

```
.venv/
.env
__pycache__/
*.pyc
```

---

## Officers and resolution

Each local body has one officer (`officers` table; run
`python seed_officers.py` to create a test officer per local body, all on
one test phone). When a complaint completes, `officer_for` picks the officer
for its local body and `officer_service.notify_officer` sends the alert as
plain text, falling back to the template above when the officer is outside
the 24-hour window. The alert's WhatsApp id is saved in
`complaints.notification_wamid`.

An officer resolves a complaint by sending a photo that:

- is a swipe-reply to the alert, or
- has the reference number (`NLG-2026-00001`) in its caption, or
- is the only pending complaint they have.

The complaint gets `officer_status = resolved` and `resolved_at`, the photo
is stored under `resolved/<reference>/`, and the citizen receives the
photo with a resolved notice in their language. An officer with several
pending complaints and no reference is asked to resend with one.

Photos from citizens (`photo_url`) and officers (`resolved_photo_url`) are
downloaded from Meta and uploaded to Supabase Storage by `storage.py`; the
object path is saved. If an upload fails, the Meta media id is kept instead.

---

# 8. First-Time Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python seed_officers.py     # optional: test officers
```

---

# 9. Daily Startup

Two terminals.

**Terminal 1 — FastAPI**

```powershell
cd "E:\CODING\Solid-Waste WACB"
.venv\Scripts\activate
$env:PYTHONUTF8=1
uvicorn app.main:app --reload
```

Or press **F5** in VS Code and pick **FastAPI: uvicorn (reload)**.

**Terminal 2 — ngrok**

```powershell
ngrok http 8000
```
cd admin-ui

'''UI - npm run dev'''

Keep both open. If the ngrok URL changed, update the Meta webhook
Callback URL to `https://NEW-NGROK-URL/webhook`.

Shut down with `CTRL + C` in each terminal.

## Only one server on port 8000

If startup prints `[Errno 10048] ... only one usage of each socket address`,
another uvicorn is already on port 8000. It may be an older copy running
old code, or one started with a different Python. Find it and stop it:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen |
  ForEach-Object { Get-CimInstance Win32_Process -Filter "ProcessId=$($_.OwningProcess)" | Select-Object ProcessId, CommandLine }
Stop-Process -Id PID_FROM_ABOVE -Force
```

Then start the server again. Use the `.venv` Python so the same
dependencies load every time.

## Restarting matters

`--reload` only watches `.py` files. It does **not** reload on a `.env`
change, so a new access token needs a manual restart. The non-reload
debug config does not reload at all — if a code change seems to have no
effect, that is almost always why.

Conversation state is in the database, so a restart no longer resets a
citizen's place in the flow. Saved complaints also survive restarts.

---

# 10. Verifying the Setup

**FastAPI:** open `http://127.0.0.1:8000/` — expect
`{"message": "WhatsApp Bot is Running"}`. Swagger is at `/docs`.

**Database:** `python check_db.py` should list `complaints` and
`conversation_state` and print their columns.

**ngrok:** open the HTTPS URL — same response confirms
Internet → ngrok → FastAPI.

**Webhook verification:**

```
https://YOUR-NGROK-URL/webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=987654
```

Expect `987654`. A wrong token returns `403 Verification failed`.

**POST locally:**

```powershell
curl.exe -X POST "http://127.0.0.1:8000/webhook" -H "Content-Type: application/json" -d "{\"test\":\"hello\"}"
```

Expect `{"status":"received"}`.

**Meta Dashboard:** Your App → WhatsApp → Webhooks. Callback URL
`https://YOUR-NGROK-URL/webhook`, verify token matching `.env`, and the
`messages` field subscribed. The WABA must be subscribed to the app.

- WABA: `2495360760940821`
- App: `swm`, App ID `1914009699558609`

**Tests:**

```powershell9
pip install -r requirements-dev.txt
pytest
```

Tests live in `tests/` and use an in-memory SQLite database (`aiosqlite`),
so they need no Postgres or Meta credentials.

**Real message:** send `hi` from the authorised test recipient. The bot
should reply with the Thuyan intro and the language buttons.

**Checking a saved complaint:**

```sql
select reference_no, complaint_type, local_body, ward_number, status, created_at
from complaints order by created_at desc;
```

---

# 11. Error Handling

The webhook **always returns 200**, even when sending fails. Meta
re-delivers on any non-2xx, so returning 500 turns one failed send into
hours of retries. Failures are logged and swallowed:

```
WhatsApp API status: 401
WhatsApp API response: {"error":{...,"code":190,...}}
Webhook processing error: HTTPStatusError(...)
INFO: "POST /webhook HTTP/1.1" 200 OK      <- correct
```

An error in the log alongside `200 OK` is the intended combination.

When processing fails, the handler prints the error and full traceback,
rolls the database session back, and sends the citizen an
`error_try_again` message (English and Tamil) so a failed save is not
silent. Still check the terminal log after a test complaint.

## Access tokens expire

A token generated in the Meta dashboard is **temporary and expires in 24
hours**, producing `code 190` / `error_subcode 463`. To check one:

```powershell
curl.exe -s "https://graph.facebook.com/v26.0/PHONE_NUMBER_ID" -H "Authorization: Bearer TOKEN"
```

Verified names back means the token is good; `code 190` means it is dead.

For anything beyond local testing, generate a permanent **System User**
token: business.facebook.com → Business Settings → Users → System Users →
Add → Admin → Add Assets → your WABA with Full control → Generate New
Token → expiry **Never**, scopes `whatsapp_business_messaging` and
`whatsapp_business_management`.

---

# 12. Database — Wired, Not Yet Verified

Tables and code are in place:

- [x] `asyncpg`, `psycopg2-binary`, `alembic`, `pydantic-settings` installed
- [x] `app/core/config.py` — settings, async/sync URL derivation
- [x] `app/db/models.py` — `Complaint` (`reference_no` and `wamid` are unique),
      `ConversationStateRow`
- [x] `app/db/session.py` — async engine, session factory, dependency
- [x] `app/db/complaints.py` — `save_complaint`, `next_reference`
      (`NLG-2026-00001`, restarting each year), `already_saved` (duplicate check)
- [x] `app/state/conversation_manager.py` — `load_user` / `persist_user`
      read and write the `conversation_state` table on each webhook call
- [x] `Officer` model, and officer / status / resolution / `notification_wamid`
      columns on `Complaint`
- [x] Alembic migrations in `alembic/versions/`: base tables, officers,
      complaint officer status, notification wamid
- [x] `DATABASE_URL` connects to `Whatsapp_ChatBot` on `localhost:5432`
- [x] `complaints` and `conversation_state` tables exist
- [x] Two real complaints saved over WhatsApp (`NLG-2026-00001`, `NLG-2026-00002`),
      with reference numbers, local body, ward, location and photo media id

Not yet confirmed:

- [ ] A complaint and conversation survive a server restart
- [ ] `NLG-2026-00001` has an empty `complaint_type` and no `custom_complaint`.
      The state machine sets one of them at the menu step, so this complaint
      probably came from an older copy of the code, but it has not been
      reproduced either way. Complete one more complaint and check

Known gaps:

- Complaints are still `print()`ed to the terminal as well as saved.
- If a Supabase upload fails, `photo_url` falls back to the Meta media id,
  which expires after about 30 days.
- The `wamid` duplicate check only protects against Meta re-delivery of the
  same message. It does not stop a citizen filing twice on purpose.

---

# 13. Development Status

## Completed

- [x] Meta app, WABA, test number, access token
- [x] Webhook verification and message receipt
- [x] ngrok tunnel, Meta → ngrok → FastAPI
- [x] Send WhatsApp replies
- [x] Interactive list and button messages
- [x] Bilingual UI (English / Tamil) with per-user language
- [x] Thuyan introduction and language selection
- [x] Complaint menu (6 options)
- [x] Free-text complaint option
- [x] Local body type → block → local body selection, with paging
- [x] Ward number capture and validation
- [x] Location capture (typed or WhatsApp location pin)
- [x] Photo question and photo upload handling in the flow
- [x] Conversation state stored in PostgreSQL (`conversation_state`)
- [x] Restart / new complaint handling
- [x] WhatsApp field length validation at import time
- [x] Webhook error handling that never triggers Meta retries
- [x] Database connection, tables created by Alembic
- [x] Complaint save with reference number (`NLG-YYYY-NNNNN`) in the receipt
- [x] Duplicate protection on the Meta `wamid`, with a unique constraint
- [x] Save errors are logged with a traceback, rolled back, and the citizen
      is told to retry
- [x] Officers per local body, assigned on save and alerted on WhatsApp
      (text, with template fallback)
- [x] Officer resolution by photo reply; citizen notified with the photo
- [x] Photo storage in Supabase Storage (citizen and resolution photos)
- [x] Read-only admin dashboard and `/admin/api/*`
- [x] pytest suite

## In progress

- [ ] **Restart test** — restart the server and check saved complaints and
      conversations are still in the database
- [ ] **Officer escalation** — `escalation_officer_id` exists on `officers`
      but nothing escalates an unresolved complaint yet

## Not completed

- [ ] Tamil review by a native speaker
- [ ] Export for the Collector's office (the dashboard is view-only)
- [ ] Structured logging
- [ ] Production hosting (replace ngrok with a stable HTTPS backend)
- [ ] Production WhatsApp number, permanent token, business verification
- [ ] Monitoring, rate limiting, Docker deployment
- [ ] Automated backups (`pg_dump`) and a hosted Postgres for real use

---

# 14. Security Rules

Never put these in Python code — use `.env`:

- Meta access token
- ngrok authtoken
- Database password
- API keys and webhook secrets

Configure ngrok once with
`ngrok config add-authtoken YOUR_NGROK_TOKEN`; it never belongs in the
application.

`VERIFY_TOKEN` and `WHATSAPP_ACCESS_TOKEN` are different things.
`VERIFY_TOKEN` is used by Meta to verify our webhook. The access token is
used by us to authenticate requests to Meta.

---

# 15. Troubleshooting

**Code changes have no effect** — the server is running stale code.
Restart it. `--reload` ignores `.env`, and the non-reload debug config
never reloads.

**`[Errno 10048]` on startup** — another server is on port 8000. See
section 9.

**`401` / `code 190`** — the access token expired. See section 11.

**`400 (#131009)` "Parameter value is not valid"** — an interactive field
is over its cap. `error_data.details` names the field. See section 3.

**`UnicodeEncodeError: 'charmap' codec`** — Tamil printed to a cp1252
console. Set `PYTHONUTF8=1`.

**`invalid dsn: invalid connection option "sslmode"`** — remove
`?sslmode=require` from `DATABASE_URL` and set `DB_SSL=true`.

**`password authentication failed for user "postgres"`** — the password in
`DATABASE_URL` is wrong. Check it against the local Postgres install.

**`python-dotenv could not parse statement`** — a malformed line in
`.env`. Values containing `#`, spaces or quotes need wrapping in double
quotes.

**`uvicorn is not recognized`** — activate the venv, or use
`python -m uvicorn app.main:app --reload`.

**`Webhook processing error` in the log, but the citizen got no reply** —
a save or send failed. Read the traceback above that line.

**Webhook verification fails** — check FastAPI and ngrok are running, the
Callback URL includes `/webhook`, the verify token matches `.env`, and the
current ngrok URL is in use.

**Local POST works but Meta does not** — check the WABA is subscribed to
the app and the `messages` field is subscribed.

---

# 16. Next Steps

In order:

1. **Restart test.** Restart the server and check the `complaints` and
   `conversation_state` tables still hold their rows. Then complete one more
   complaint to see whether the empty `complaint_type` on `NLG-2026-00001`
   happens again.
2. **Escalate stale complaints** to the officer's `escalation_officer_id`
   when they stay unresolved.
3. **Remove `print()` output** for completed complaints once the database
   path is confirmed.
4. **Back up the database** with `pg_dump` on a schedule, and move to a
   hosted Postgres before any real citizen uses the bot.
5. **Get Tamil reviewed** by a native speaker before going live.


---

# Admin dashboard

A read-only React dashboard in `admin-ui/`, backed by the `/admin/api/*`
endpoints in `app/api/admin.py`. Pages: Overview (key numbers and charts),
Complaints (filter, search, expand), Officers, Conversations (chats in
progress) and Database (every table's columns, row counts and latest rows).

```powershell
# Terminal 1: API
uvicorn app.main:app --reload
# Terminal 2: dashboard at http://localhost:5173
cd admin-ui
npm install
npm run dev
```

Set `ADMIN_TOKEN` in `.env` to require a token; the dashboard asks for it
on first load. **If it is unset the API is open**, and the Database and
Conversations pages expose citizens' phone numbers, so set it before the
server is reachable from outside (ngrok included).
