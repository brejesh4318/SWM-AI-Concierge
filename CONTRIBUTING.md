# Workflow

1. Branch from an up-to-date `main`: `feature/…`, `fix/…`, `chore/…`.
2. Keep each PR to one concern (aim for under ~400 changed lines).
3. Open a PR; fill in the template. CI (lint, test, migrations, audit) must pass.
4. Review your own diff on GitHub, resolve every comment, run `/code-review`.
5. Squash merge, delete the branch, tag releases (`vX.Y.Z`).

Local setup: `pip install -r requirements-dev.txt ruff pre-commit && pre-commit install`.
