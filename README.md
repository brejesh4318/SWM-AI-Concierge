# Thuyan — Solid Waste Management WhatsApp Bot

A WhatsApp chatbot for The Nilgiris district that collects solid waste
complaints from citizens and routes them to the District Collector.

Built with the Meta WhatsApp Cloud API, FastAPI and ngrok. The bot is
bilingual (English / Tamil), runs a guided complaint flow using WhatsApp
interactive list and button messages, and currently runs locally against
a Meta test number.

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
FastAPI  ->  webhook.py      parse + route the incoming message
             chatbot_service  state machine, decides what happens next
             messages.py      all user-facing copy, English + Tamil
             local_bodies.py  Nilgiris local body data + list paging
             whatsapp_service build and send the outbound payload
   |
   v
Meta WhatsApp Cloud API
   |
   v
Citizen
```

Conversation state currently lives in **memory** (`app/state/`), so it is
lost on restart. Moving it to PostgreSQL is the next major task — see
section 12.

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
   -> confirmation
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
│   │   └── webhook.py               GET verify + POST receive, routing
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py                settings from .env (pydantic-settings)
│   │
│   ├── db/                          NOT yet wired into the bot
│   │   ├── models.py                Complaint, ConversationStateRow
│   │   └── session.py               async engine + session factory
│   │
│   ├── services/
│   │   ├── chatbot_service.py       state machine
│   │   ├── messages.py              all copy, en/ta, + limit validation
│   │   ├── local_bodies.py          local body data + paging
│   │   └── whatsapp_service.py      outbound payload builders
│   │
│   └── state/
│       ├── conversation_manager.py  in-memory state (to be replaced)
│       └── conversation_state.py    state enum
│
├── .vscode/launch.json              debug configs
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
- PostgreSQL (local or hosted — not yet in use)
- Meta Developer Account with a WhatsApp Cloud API app
- Meta WhatsApp test number, WABA, Phone Number ID, access token

---

# 7. Environment Variables

Create `.env` in the project root:

```
VERIFY_TOKEN=your_webhook_verify_token
WHATSAPP_ACCESS_TOKEN=your_meta_access_token
PHONE_NUMBER_ID=your_phone_number_id
DATABASE_URL=postgresql://user:password@localhost:5432/swm
DB_SSL=false
```

`DATABASE_URL` is stored in plain `postgresql://` form. `config.py`
derives two variants from it: `postgresql+asyncpg://` for the app and
`postgresql+psycopg2://` for Alembic.

**Do not append `?sslmode=require`.** That is a psycopg2 option and
asyncpg crashes on it. Use `DB_SSL=true` instead — the app adds
`sslmode` for Alembic and passes `ssl` to asyncpg itself.

Never commit `.env`. `.gitignore` should contain:

```
.venv/
.env
__pycache__/
*.pyc
```

---

# 8. First-Time Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
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

Keep both open. If the ngrok URL changed, update the Meta webhook
Callback URL to `https://NEW-NGROK-URL/webhook`.

Shut down with `CTRL + C` in each terminal.

## Restarting matters

`--reload` only watches `.py` files. It does **not** reload on a `.env`
change, so a new access token needs a manual restart. The non-reload
debug config does not reload at all — if a code change seems to have no
effect, that is almost always why.

Restarting also wipes all in-memory conversation state, so send `hi`
fresh rather than continuing an existing thread.

---

# 10. Verifying the Setup

**FastAPI:** open `http://127.0.0.1:8000/` — expect
`{"message": "WhatsApp Bot is Running"}`. Swagger is at `/docs`.

**ngrok:** open the HTTPS URL — same response confirms
Internet → ngrok → FastAPI.

**Webhook verification:**

```
https://YOUR-NGROK-URL/webhook?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=987654
```

Expect `987654`.

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

**Real message:** send `hi` from the authorised test recipient. The bot
should reply with the Thuyan intro and the language buttons.

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

# 12. Database — In Progress

The `complaints` and `conversation_state` tables are designed but
**nothing in the bot reads or writes them yet**. Completed complaints are
currently only `print()`ed to the terminal and then lost.

Done:

- [x] `asyncpg` and `pydantic-settings` installed
- [x] `app/core/config.py` — settings, async/sync URL derivation
- [x] `app/db/models.py` — `Complaint`, `ConversationStateRow`
- [x] `app/db/session.py` — async engine, session factory, dependency

Still to do for step 1:

- [ ] `app/db/__init__.py` (empty file, currently missing)
- [ ] A working `DATABASE_URL` — the current one fails with
      `password authentication failed for user "postgres"`
- [ ] `alembic init alembic`, point `env.py` at `Base.metadata` and
      `get_settings().sync_url`, remove `sqlalchemy.url` from `alembic.ini`
- [ ] `alembic revision --autogenerate` then `alembic upgrade head`

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
- [x] Photo question and photo upload
- [x] Conversation state machine (in memory)
- [x] Restart / new complaint handling
- [x] WhatsApp field length validation at import time
- [x] Webhook error handling that never triggers Meta retries

## Not completed

- [ ] **Database wiring** — see section 12
- [ ] **Persist conversation state** (currently lost on restart, and
      blocks running more than one uvicorn worker)
- [ ] **Store complaints** so they reach the District Collector
- [ ] **Complaint reference number** returned to the citizen
- [ ] **Photo storage** — `photo_media_id` expires after ~30 days, so
      images must be downloaded and stored in object storage
- [ ] **Duplicate protection** — store the WhatsApp `wamid` with a unique
      constraint; Meta re-delivers and can file the same complaint twice
- [ ] Tamil review by a native speaker
- [ ] Admin view / export for the Collector's office
- [ ] Structured logging
- [ ] Production hosting (replace ngrok with a stable HTTPS backend)
- [ ] Production WhatsApp number, permanent token, business verification
- [ ] Monitoring, rate limiting, Docker deployment

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

**`401` / `code 190`** — the access token expired. See section 11.

**`400 (#131009)` "Parameter value is not valid"** — an interactive field
is over its cap. `error_data.details` names the field. See section 3.

**`UnicodeEncodeError: 'charmap' codec`** — Tamil printed to a cp1252
console. Set `PYTHONUTF8=1`.

**`invalid dsn: invalid connection option "sslmode"`** — remove
`?sslmode=require` from `DATABASE_URL` and set `DB_SSL=true`.

**`python-dotenv could not parse statement`** — a malformed line in
`.env`. Values containing `#`, spaces or quotes need wrapping in double
quotes.

**`uvicorn is not recognized`** — activate the venv, or use
`python -m uvicorn app.main:app --reload`.

**Webhook verification fails** — check FastAPI and ngrok are running, the
Callback URL includes `/webhook`, the verify token matches `.env`, and the
current ngrok URL is in use.

**Local POST works but Meta does not** — check the WABA is subscribed to
the app and the `messages` field is subscribed.

---

# 16. Next Step

Finish the database work in section 12, then switch
`conversation_manager` from dicts to the `conversation_state` table. That
single change fixes restart data loss and unlocks running more than one
worker.

After that, persist complaints and return a reference number to the
citizen.
