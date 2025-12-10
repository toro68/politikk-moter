# Repository Guidelines

## Project Structure & Module Organization
- `src/politikk_moter/`: core scraper, parser modules, pipeline config, and Slack formatting utilities.
- `scripts/`: ad-hoc debugging tools (`inspect_strand.py`, `debug_parser.py`) and Playwright installers.
- `tests/`: pytest suites grouped by domain (`test_calendar_*`, `test_kommune_*`), fixtures under `tests/fixtures/`.
- `docs/`: Norwegian documentation, progress reports, and archived HTML dumps.
- `scraper.py`: runnable entry point that wires scraping, fallback data, and Slack delivery.
- `.github/workflows/daily-meetings.yml`: daily GitHub Actions workflow for automated Slack digests.

## Build, Test & Development Commands
- `python -m pip install -r requirements.txt`: install scraper, Playwright, and Google API dependencies.
- `./scripts/install_playwright.sh`: provision browsers required for Playwright-backed parsers.
- `python scraper.py --debug`: run locally without posting to Slack (prints meeting digest).
- `python scraper.py --force`: send real Slack messages; requires `SLACK_WEBHOOK_URL`.
- `pytest`: run the full test suite; prefer `pytest tests/test_<module>.py` for focused debugging.

## Coding Style & Naming Conventions
- Python 3.11, 4-space indentation, descriptive snake_case for functions, PascalCase for dataclasses/models.
- Parsers live under `src/politikk_moter/` and expose `parse_<kommune>_meetings`-style helpers.
- Keep networking logic in `MoteParser` or dedicated scraper modules; avoid duplicating session setup.
- Prefer f-strings over string concatenation; guard environment-dependent code with helper functions (see `_is_truthy_env`).
- Use existing Slack formatting helpers in `reporting.py`; avoid embedding formatting logic in new modules.

## Testing Guidelines
- Tests rely on pytest; fixtures under `tests/fixtures/kommune_html/` mirror real HTML snippets.
- Name new tests `test_<feature>.py` and place municipality-specific suites alongside existing peers.
- Ensure parsers handle no-meeting/fallback scenarios; consider adding regression fixtures when parsing new CMS variants.
- Run `pytest` (or targeted modules) before opening a PR; check that Playwright-dependent tests are skipped or mocked if browsers unavailable.

## Commit & Pull Request Guidelines
- Follow conventional, descriptive commit titles similar to `Restore turnus batching and fix related tests`.
- Keep commits scoped: separate parser changes from docs or workflow tweaks.
- PRs should explain problem, solution, validation (commands run), and any configuration updates (e.g., new secrets or env vars).
- Include screenshots or Slack output snippets when altering message formatting; link GitHub issues or Trello cards when applicable.

## Security & Configuration Tips
- Never hardcode Slack webhooks or Google credentials; rely on environment variables or GitHub Secrets (`SLACK_WEBHOOK_URL`, `GOOGLE_SERVICE_ACCOUNT_JSON`).
- Use `--debug` during development to avoid accidental Slack posts; require `--force` for intentional sends.
- Scraper handles municipal rate limits politely; do not lower default delays without confirming with stakeholders.
