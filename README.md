[![Build Status](https://github.com/andgineer/lexiflux/workflows/CI/badge.svg)](https://github.com/andgineer/lexiflux/actions)
[![Coverage](https://raw.githubusercontent.com/andgineer/lexiflux/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/andgineer/lexiflux/blob/python-coverage-comment-action-data/htmlcov/index.html)
<br/><br/>
<img align="left" width="200" src="lexiflux/static/android-chrome-192x192.png" />

# Lexiflux reader

**Keep reading. Get help where you need it.**

Read books and articles in another language with translations inside the text
and AI explanations beside it. Bring your own EPUB, HTML, or text files, import
a web page, or send books from Calibre.

![Inline translation and AI explanations in the Lexiflux reader](docs/common/images/ponedeljak.png)

* **Stay with the text.** Select a word or phrase for an inline translation in the sense
  it has in the sentence, or its entry in an offline Wiktionary; open the sidebar for usage,
  origins, or an explanation of the surrounding sentence.
* **Choose your reading tools.** Configure dictionaries, AI models, and custom
  prompts separately for each language. The default AI article runs on a pool of free-tier
  models and streams into the sidebar as it is written.
* **Take vocabulary with you.** Export your lookup history with context to Anki
  through AnkiConnect or an Anki deck file, or download it as CSV.

[Quick start](https://andgineer.github.io/lexiflux/quickstart/) ·
[Documentation](https://andgineer.github.io/lexiflux/) ·
[Docker image](https://hub.docker.com/r/andgineer/lexiflux)

## Under the hood

**A lookup needs its sentence.** The reader maps selected words back to their
sentences and sends the AI two plain values: the selected term and its sentence,
so a prompt can distinguish what to explain from the context that determines its
meaning. A very short sentence is extended with its neighbours. See the
[context construction](lexiflux/language/term_context.py).

**Translations change the page.** An inline explanation changes line lengths and
scroll positions. The TypeScript reader tracks words and translation spans,
merges overlapping or adjacent selections, and adjusts the viewport to keep
the text readable. [Reader tests](tests/js/) cover selection and viewport
behaviour alongside the Python suite.

**Several tools, one reading workflow.** Django manages the library, language
preferences, and lookup history. Dictionaries, external reference sites, and
AI prompts are configurable parts of the same sidebar; the inline translation
defaults to a free-pool LLM, and the offline Wiktionary or Google translate without one
(see the [inline translation spec](specs/inline-translation.md)).
AI calls go through [llmbroker](https://github.com/andgineer/llmbroker), and the
[AI models guide](docs/src/en/aimodels.md) explains the models, the translators, their costs
and where the API keys go. The [Calibre plugin](lexiflux/calibre_plugin/) connects an existing
ebook library to the reader.

<details>
<summary><b>Contributing</b></summary>

Clone the repository and install [uv](https://docs.astral.sh/uv/), then:

```bash
source ./activate.sh
npm ci
inv buildjs
inv init-db
inv run
```

Open [127.0.0.1:8001](http://127.0.0.1:8001). `inv init-db` initializes the
database with sample data; `inv run` enables local auto-login.
For AI articles, put the API keys in `.env` in the repository root:
`llmbroker env freetier >> .env` appends the free-pool key names with links to get them.
Fill in at least one of `GROQ_API_KEY`, `GEMINI_API_KEY`, `ZAI_API_KEY` and skip
`OPENROUTER_API_KEY`: Lexiflux leaves the OpenRouter models out of the pool.
For the Wiktionary translator, `./manage import-wiktionary` downloads about 3.2 GB from
kaikki.org and builds `wiktionary.sqlite3` (about 230 MB) next to the database in a few minutes.

Run checks from the activated environment:

```bash
inv pre
npm test
python -m pytest tests
```

The browser tests use the Selenium Grid defined in `docker-compose.yml` and
require Docker. `inv test` also generates and opens the Allure report.

The reader's AI panels and inline popup have Playwright tests in `tests/e2e_playwright/`. They need
the built bundle (`inv buildjs`) and Chromium (`playwright install chromium`, done by
`activate.sh` when it creates the environment):

```bash
python -m pytest -m playwright tests             # headless
python -m pytest -m playwright --headed tests    # visible browser
LEXIFLUX_REAL_LLM=1 python -m pytest -m real_llm tests  # real free-pool smoke, needs pool keys in .env
```
See [AGENTS.md](AGENTS.md) for repository conventions and `inv --list` for tasks.

For local HTTPS, run `inv keygen`, then `inv runssl`. To use a locally trusted
certificate, create one with mkcert and configure the certificate paths in
the `runssl` task.

**Access from other devices (Tailscale).** `inv run` listens on 127.0.0.1 only.
To open it from your other tailnet devices over HTTPS, publish it with
`tailscale serve --bg --https=443 http://127.0.0.1:8001` and open
`https://<machine>.<tailnet>.ts.net`. Undo with `tailscale serve --https=443 off`.
The local settings accept any `*.ts.net` host and trust HTTPS from that proxy.
`inv run` auto-logs-in everyone who can reach it, so expose it only with `tailscale serve`
(tailnet only), never `tailscale funnel`.

[Allure test report](https://andgineer.github.io/lexiflux/builds/tests/)

</details>
