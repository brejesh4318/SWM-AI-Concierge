## What and why

<!-- One or two sentences: the change and the reason for it. -->

## How I tested it

- [ ] Unit tests added or updated
- [ ] Ran locally against a real database / WhatsApp sandbox (if relevant)

## Risk and rollback

- [ ] Includes an Alembic migration (reversible, safe on live data)
- [ ] Adds or changes env vars / config (`.env.example`, README updated)
- Rollback plan:

## Self-review checklist

- [ ] I read the full diff on GitHub
- [ ] No secrets, tokens or phone numbers in code or logs
- [ ] Webhook and admin endpoints keep their auth / signature checks
- [ ] External calls have error handling and timeouts
