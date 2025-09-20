# Repository Guidelines

## Project Structure & Module Organization
- `lexiflux/`: Django app (models, views, templates/, static/, viewport/ TypeScript, admin, migrations).
- `tests/`: Python tests; `tests/js/`: Jest + TypeScript tests.
- `docs/`: MkDocs sources; `scripts/`: helper scripts; `docker/`: Dockerfiles; `ssl_certs/`: local dev certs.
- Entrypoints: `manage` (symlink to `manage.py`), `tasks.py` (Invoke tasks).

## Build, Test, and Development Commands
- Setup env: `pipx install invoke` then `. ./activate.sh` (uses uv; creates `.venv`).
- Run server: `inv run` (auto-login) or `inv runssl` (HTTPS). Open http://localhost:8000.
- Initialize DB: `inv init-db` (migrate, superuser, default user, sample data).
- JS bundle: `inv buildjs` (runs `npm run build`).
- Python tests: `inv test` or `python -m pytest tests -q`.
  - Filter: `inv test -k "reader or import"`.
- JS tests: `npm test` (uses `jest.config.ts`).
- Lint/format: `inv pre` (pre-commit across repo).
- Misc: `inv --list` to see all tasks; version bump `inv ver-feature|ver-bug|ver-release`; Docker image `inv docker`.

## Coding Style & Naming Conventions
- Python: 4-space indent; type hints preferred.
- Linting: Ruff (line length ~100), Flake8 (max 99), Pylint minimal; `ruff-format` for formatting.
- Static typing: `mypy` (pre-commit). Keep imports ordered (Ruff I rules).
- TS: place source under `lexiflux/viewport/`; keep tests in `tests/js/*.test.ts`.
- Naming: Python tests `tests/test_*.py`; modules, functions `snake_case`; classes `PascalCase`.

## Testing Guidelines
- Frameworks: Pytest (+ markers: `docker`, `selenium`) and Jest for TS.
- Coverage: Jest writes to `coverage/`; Python coverage reported in CI. Add/keep tests for new logic.
- Django settings for tests: `pytest.ini` sets `DJANGO_SETTINGS_MODULE=tests.django_settings`.

## Commit & Pull Request Guidelines
- Commits: clear, focused; reference issues (e.g., `Fix import flow (#99)`); version bumps as `Version vX.Y.Z` when applicable.
- Before PR: run `inv pre`, `npm test`, and `inv test`; ensure CI is green.
- PRs: include description, linked issues, screenshots for UI changes, and notes on tests/coverage.

## Security & Configuration Tips
- Never commit secrets; use environment variables. For local auth bypass: `LEXIFLUX_SKIP_AUTH=true` (Invoke tasks set this automatically where safe).
