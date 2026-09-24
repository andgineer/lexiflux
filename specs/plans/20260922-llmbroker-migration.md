# Replace LangChain with llmbroker: free pool, direct models, streaming

## Overview

lexiflux stops using LangChain. Every AI article goes through llmbroker:

- the default article (**Article**) asks the free-tier pool;
- every other AI article asks a named paid model directly, by default `gpt`
  (GPT-5.6 Sol) with reasoning off and priority processing: the configuration
  echo-words measured best for the "Подробнее" article on 2026-09-21;
- sidebar articles stream into the pane;
- lexiflux holds no API keys: llmbroker reads the operator's keys from the environment
  and `.env`, and the AI Settings page is removed;
- temperature is replaced by two per-article knobs, reasoning effort and processing
  tier, with measured defaults.

Evidence behind the model set and defaults: `../echo-words/spec/decision-llm-backend.md`,
sections "The deeper article: Sol, with reasoning off, on priority processing — 2026-09-21",
"Streamed racing with whole-answer replacement is the shipped adapter — 2026-09-06" and
"The paid tier: `gpt-5.6-luna` is the one worth reaching for". Evidence behind the context
and the prompts: lexiflux's own bench, Phase 1 below.

## Decisions

| Topic | Decision |
|---|---|
| Broker shape | One process-wide sync `llmbroker.Broker`; each request uses `broker.for_scope(f"u-{user.id}")`, which only attributes journal rows to the user |
| Keys | lexiflux stores, reads and shows no keys. llmbroker reads the operator's keys from env and `.env` in the repo root; on Koyeb they are Koyeb secrets exposed as env vars. Every user spends the operator's keys, paid models included. `AIModelConfig` rows are dropped and the AI Settings page is removed |
| Broker state | Locally and in Docker: lexiflux's own llmbroker home (`BASE_DIR / ".llmbroker"`, git- and docker-ignored), so the persistent pool exclusions do not leak into other llmbroker users on the machine. On Koyeb: lexiflux's Postgres (`DATABASE_URL`), so the pool's learned model ordering survives deploys. Keys stay in env there too |
| Existing data | No data migration. lexiflux has a single user, the author, and no database to carry over: he recreates his local DB with `invoke init-db` (it drops the old one), and it gets the new default articles through the normal defaults path. The migration is schema-only |
| Offered models | `pool`, `gpt` (Sol), `gpt-fast` (Luna), `opus`. Sonnet, Haiku, gpt-mini, Gemini paid, Grok, DeepSeek, Mistral and Ollama are dropped |
| Knobs | Reasoning effort and processing tier, per article, with per-model defaults, only for providers where measured |
| Streaming | In v1. NDJSON over `fetch`; pool uses `fastest_of=2, wait=25` with whole-answer replacement. The streaming response bypasses `GZipMiddleware` |
| Serving | Stays WSGI (`runserver`). llmbroker gets a sync `stream()` (Phase 0) |
| Term context | The prompt gets two plain values, the selected **word** and its **sentence**, as echo-words does. No `[FRAGMENT]`/`[HIGHLIGHT]` marks. A sentence shorter than 6 words is extended with its neighbours (Phase 1 result) |
| Prompts | AI dictionary → echo-words short-article rules; new In depth → echo-words extended prompt plus one sentence naming the whole unit; Origin gets the "only where you know it" rule; all prompts get language names instead of Google codes |
| Rendering | AI article panels keep the answer's line breaks; Markdown `**x**`/`*x*` in an answer is shown as bold/italic |

### Offered models and default knobs

| Option | Provider | Default effort | Default tier | Measured on the deeper article (24 words) |
|---|---|---|---|---|
| `pool` | free pool | — | — | echo-words short article: first text 0.8 s median, whole p90 3.6 s |
| `gpt` | openai | none | priority | 4.04/5, 5 serious errors, 0.78 s to start, 7.3 s whole, $0.036 |
| `gpt-fast` | openai | low | priority | 3.67/5, 8 serious errors, 2.69 s to start, $0.003 |
| `opus` | anthropic | low | — | 4.38/5, 3 serious errors, 17.6 s to start (p90 29.6 s), $0.058 |

### Knob vocabulary per provider

Only what echo-words sent (`experiments/tier_screen.py`, lines 72–101). Anything else is
"model default", which sends nothing.

| Provider | Effort values → request body | Tier values → request body |
|---|---|---|
| openai | `none`/`low`/`medium`/`high` → `{"reasoning_effort": v}` | `priority` → `{"service_tier": "priority"}`; `standard` → nothing |
| anthropic | `none` → `{"thinking": {"type": "disabled"}}`; `low`/`medium`/`high` → `{"reasoning_effort": v}` | not offered |

### Default articles (new users)

| Title | Type | Parameters |
|---|---|---|
| Article | `AI dictionary` | `{"model": "pool"}` |
| In depth | `In depth` (new) | `{"model": "gpt", "effort": "none", "tier": "priority"}` |
| Sentence | `Sentence` | `{"model": "gpt", "effort": "none", "tier": "priority"}` |
| glosbe | `Site` | unchanged |

Inline translation: `Dictionary` / `GoogleTranslator` (unchanged default).
Any AI article type a user adds defaults to `gpt`, `none`, `priority`.

## Context

lexiflux:
- `lexiflux/language/llm.py`: LangChain pipelines, `mark_term_and_sentence` (lines ~310–400),
  `_get_or_create_model`, `AIModelError`, `AIModelRetiredError`, `lru_cache` article cache
- `lexiflux/language/sentence_extractor_llm.py`: only its four mark constants are used in
  production; `break_into_sentences_llm` runs only from its own `__main__` and tests
- `lexiflux/resources/chat_models.yaml`, `lexiflux/resources/prompts/*.txt`
- `lexiflux/models.py`: `SUPPORTED_CHAT_MODELS` (line 26), `LexicalArticleType` (49),
  `LEXICAL_ARTICLE_PARAMETERS` (63), `AIModelConfig` (571), `LexicalArticle` (625),
  `BookPage.words` (391), `BookPage.word_sentence_mapping` (461), `Language.name` (121)
- `lexiflux/language_preferences_default.py`: `DEFAULT_LEXICAL_ARTICLES`
- `lexiflux/views/lexical_views.py`: `get_lexical_article`, `translate`,
  `get_context_for_translation_history` (line 222), `get_llm_errors_folder`
- AI Settings, all removed: `lexiflux/views/ai_settings_views.py`,
  `lexiflux/templates/ai-settings.html`, `lexiflux/templates/ai-settings-vue.js`, its routes in
  `lexiflux/urls.py`, its link in `lexiflux/templates/hamburger.html`
- `lexiflux/views/language_preferences_views.py` (line 88: `ai_models` from `chat_models`),
  `lexiflux/templates/language-preferences-vue.js`,
  `lexiflux/templates/partials/lexical_artical_modal.html` (model selects at lines 51, 70)
- `lexiflux/templates/llm-error/*.html`, `lexiflux/templates/llm-error-env/*.html` (12 files)
- `lexiflux/viewport/translate.ts`: `makeRequest` (line 148), `updateLexicalPanel` (430),
  `showSpinnerInLexicalPanel`; `.lexical-content` has no `white-space` rule
- `lexiflux/templates/reader.html` (article tabs, lines 155–171), `lexiflux/views/reader_views.py`
- `lexiflux/environments/{base,local,docker,koyeb}.py` (`GZipMiddleware` in `base.py` line 62 and
  `koyeb.py` line 64; `DATABASE_URL` in `koyeb.py`), `lexiflux/lexiflux_settings.py`
- `docker/Dockerfile` (Ollama: lines 15, 34, 41), `docker/start.sh` (line 3),
  `docker/start_ollama.sh`, `tasks.py` `rundocker` (line 304), `.dockerignore`
- `requirements.in` (lines 13–23), `requirements.koyeb.in` (lines 24–31)
- `tests/profile_llm.py`, `llm_benchmark.json`: the old profiler, superseded by the echo-words research
- `experiments/lexical_articles.ipynb`
- Docs: `docs/src/en/aimodels.md`, `docs/src/en/docker.md`
- Phase 1 bench: `experiments/context_bench.py`, `experiments/context_bench_aggregate.py`,
  `experiments/context_bench.json`, `experiments/.context-bench/review/`,
  `experiments/context_bench_prompts/`

llmbroker (`../llmbroker`; Phase 0 released as 1.11.0):
- `src/llmbroker/sync.py`: sync `Broker`/`LLMs` over a background loop thread
- `src/llmbroker/broker/curated.py`: `curated_pool()` (`configs`, `keys` with `help`),
  `curated_paid()` (`CuratedModel.provider.id`), `curated_providers()` (`key_help`, `label`)
- `src/llmbroker/standalone/secrets.py`: `Secrets(env_file)`, env first, then the file
- `Broker("postgresql://…")` needs the `llmbroker[postgres]` extra (asyncpg); `secrets=` picks
  the key source separately from the datasource
- `downstream.toml`: hosts checked on every llmbroker change

## Phase 0 — llmbroker: sync streaming (released as 1.11.0)

Released as llmbroker 1.11.0 after five review rounds. Gate green: `invoke pre`,
`invoke test` (both passes), `invoke downstream` (dinary, echo-words, lexiflux: no regression).

The API lexiflux uses:
- `Broker.stream(...)` and `LLMs.stream(...)` (scoped, from `for_scope`), with the async
  arguments (`operation`, `wait`, `fastest_of`, `stream_selection_window`, …), return
  `llmbroker.Stream`: an iterator of text deltas and a context manager; `close()` cancels the
  provider call. Each `next()` runs one pull of the async stream on the broker's loop thread
- `DirectClient.stream(prompt, *, messages=None, timeout=None, params=None) -> Iterator[str]`
  over blocking httpx; closing it closes the connection. `llms.direct(model)` returns a
  `DirectClient` that owns an HTTP client and is closed with `with`
- Pooled stream errors: at the first `next()`, `NoLLMAvailableError` with `.reason`
  `no_keys` / `empty_pool` / `all_disabled` / `excluded` / `timeout` (`.retry_at` on
  `timeout`) or `ProviderError`; `AuthError`, `RateLimitError` and `MissingKeyError` never
  reach a pooled caller. Mid-stream: `StreamInterruptedError`, `LLMTimeoutError` (`wait` ran
  out), `StreamReplacementError` (`.replacement.text`)
- Direct stream errors: `MissingKeyError` / `UnknownModelError` at `direct(...)`;
  `AuthError`, `RateLimitError` (`.retry_after`), `ProviderError`,
  `InvalidProviderResponseError`, `LLMTimeoutError` at the first `next()`; mid-stream
  `LLMTimeoutError` or a raw `httpx.TransportError`
- A stream whose broker was garbage-collected raises `RuntimeError("the broker is closed")`

Lifetime contract (added after four review rounds all found defects in shutdown by garbage
collection):
- A sync `Stream` and a scoped `LLMs` keep their broker alive, so a broker with a live stream
  or scoped caller is never collected
- Closing the broker (`with llmbroker.Broker(...) as broker:`, or `close()`) is the orderly
  shutdown: it closes owned streams and settles and journals them
- A broker that is simply dropped is still cleaned up, as a best-effort backstop: collection
  and interpreter exit never block the collecting thread and promise no journal row for an
  answer still in flight
- Reviews judge the sync layer against this contract; behaviour it does not promise is not a
  finding

Remaining:
- [x] Review → fix loop until a fresh review is clean
- [x] Release 1.11.0: commit and push llmbroker `main`, then `invoke ver-feature`. Only with the
  user's explicit go-ahead
- [x] After Phase 7: add lexiflux to `downstream.toml` as a host

## Phase 1 — Experiment: context and prompt for the default article (done)

Bench: 24 words (8 English, 8 German, 8 Serbian) in real sentences, target language English.
Answers were scored blind by six fresh reviewers (1–5, serious errors quoted, whether the
article leads with the sense used in the passage, whether it heads the dictionary form,
format). Files are listed under Context.

Results, on Gemini 3.5 Flash Lite (the model that answers almost every pool request in
steady state; 24 answers per row):

| Instructions | How the word is given | Score /5 | Serious errors | Leads with the sense in the text | Format kept |
|---|---|---|---|---|---|
| current lexiflux prompt | passage with marks (today's code) | 3.17 | 15 | 24/24 | 0/24 |
| echo-words short-article rules | passage with marks | 3.88 | 8 | 24/24 | 22/24 |
| echo-words short-article rules | word + sentence | 3.58 | 9 | 17/24 | 19/24 |

- The echo-words rules beat the current prompt clearly; answers shrink from ~3200 to
  ~900–1500 characters.
- Word + sentence lost only on two stress classes the bench over-represents (12 of 24
  items): the splitter cutting a sentence short at an abbreviation or a dialogue line (the
  sense-in-text hit 2/6 against 6/6), and one word repeated in a sentence in two senses (3/6
  against 6/6). On the 12 ordinary items (polysemy, multi-word, separable verbs) word +
  sentence was as good or better: sense-in-text 12/12 against 12/12, score 4.25 against 3.92,
  serious errors 1 against 2. Word + sentence ships, with the short-sentence extension below
  covering the splitter case; the repeated-word case is rare and accepted
- The pool: on a cold broker Groq gpt-oss-120b wrote 10 of 23 answers (2.2/5, 23 serious
  errors) and Gemini 13 (3.85/5, 4 serious errors); first text p50 3.0 s, p90 14.5 s, one
  timeout. Three minutes later, warm, Gemini wrote 20 of 24, first text p50 0.9 s, p90 1.6 s.
  In echo-words' steady state Gemini writes ~97% of answers. Hence persistent broker state on
  Koyeb
- In depth on `gpt` (none, priority), 12 answers: all within the HTML contract and 4000
  characters (2.6–3.6k), about $0.035 per article. The verbatim echo-words prompt headed
  the selected piece (`made`, `steht`, `vratio`) instead of the unit; one added sentence made
  it head `make out`, `aufstehen`, `vratiti se` at the same length and cost
- Every answer under the new rules lays itself out with line breaks, which the pane
  currently collapses; Groq and some pool answers use Markdown emphasis

## Phase 2 — Dependencies and the broker module

- [x] `requirements.in`: remove `langchain`, `langchain-community`, `langchain-core`,
  `langchain-openai`, `langchain_anthropic`, `langchain_google_genai`, `langchain_mistralai`,
  `langchain_ollama`, `openai`, `ollama`; add `llmbroker>=1.11.0`. `requirements.koyeb.in`:
  the same removals, add `llmbroker[postgres]>=1.11.0`
- [x] `requirements*.txt` recompiled against llmbroker 1.11.0 from PyPI, without `--upgrade`
  (only llmbroker, `tomli-w` and, for Koyeb, `asyncpg` added); `.venv` and `.venv-koyeb` synced
- [x] New `lexiflux/language/broker.py`:
  - `get_broker() -> llmbroker.Broker`: lazily created once per process with
    `secrets=llmbroker.Secrets(BASE_DIR / ".env")`, `direct=` the aliases of the offered paid
    models, and the datasource from a setting: none in `environments/local.py` and
    `environments/docker.py`, `DATABASE_URL` in `environments/koyeb.py`; `home=` from
    `LLMBROKER_HOME` (`BASE_DIR / ".llmbroker"` locally and in Docker, none on Koyeb), also
    passed to every `curated_*()` catalog read. Closed at process exit
  - `llms_for(user) -> LLMs`: `get_broker().for_scope(f"u-{user.id}")`
- [x] New `lexiflux/language/ai_models.py`: the offered-model table and knob vocabulary
  above; `request_params(model, effort, tier) -> dict`; `default_knobs(model)`;
  `provider_of(model)` read from `curated_paid()` by alias. A catalog alias that
  disappears makes that option unavailable, and its articles show the retired-model message

## Phase 3 — Context, prompts and article generation

- [x] New `term_context(page, term_word_ids) -> TermContext(word, sentence)` (in
  `lexiflux/language/`), using `page.words` and `page.word_sentence_mapping`: `word` is the
  selected words as they stand; the sentence is the span of all words whose sentence id lies
  between the first and last selected word's sentence ids, HTML-stripped with
  `extract_content_from_html`. When that span has fewer than 6 words, it is extended with the
  previous and the next sentence where they exist. Also returns the offsets
  `get_context_for_translation_history` needs
- [x] Rewrite `get_context_for_translation_history` on those offsets. The stored format
  (`TranslationHistory.CONTEXT_MARK` around the sentence and in place of the term, ≥10
  context words expanded to full sentences) stays identical; a test pins it
- [x] Prompts in `lexiflux/resources/prompts/`, with placeholders `{word}`, `{sentence}`,
  `{text_language}`, `{user_language}` (language **names** from `Language.name`):
  - `AI dictionary.txt`: `experiments/context_bench_prompts/AI dictionary.C.txt` as is
  - `In depth.txt`: `experiments/context_bench_prompts/In depth.unit.txt` as is (echo-words
    `_EXTENDED_PROMPT`, bound 4000 characters, the context note, and the sentence naming
    the whole unit)
  - `Origin.txt`: replace "Time period of first known use" with echo-words rule 5 ("Origin
    only where you know it … leave it out")
  - `Sentence.txt`: takes `{sentence}` only
  - `Translate.txt`, `Explain.txt`, `Lexical.txt`: rewritten from marks to `{word}` +
    `{sentence}`, otherwise unchanged
  - custom `AI` type: the user's prompt followed by word + sentence (on the direct path as a
    system and a user message; the pool takes one prompt string, so there they are joined)
- [x] Rewrite `lexiflux/language/llm.py` without LangChain:
  - `ArticleRequest(article_type, model, effort, tier, prompt, word, sentence,
    text_language, user_language, user)` built by the view
  - `stream_article(req) -> Iterator[ArticleEvent]` for sidebar articles:
    - `pool` → `with llms_for(user).stream(prompt, operation=article_type, fastest_of=2, wait=25) as stream:`;
      on `StreamReplacementError` emit `replace(exc.replacement.text)`
    - direct → `with llms_for(user).direct(model) as client:` and
      `client.stream(prompt, params=request_params(...))`
    - both `with` blocks sit inside the generator, so Django's `close()` on an aborted response
      cancels the provider call
  - `generate_article(req) -> str` for the inline popup (`lexical_article=0`): same
    routing via `ask`
  - Finished-article cache: key = (user id, article type, prompt text, model, effort,
    tier, word, sentence, languages), a bounded dict; a hit replays as one `delta`. Only
    complete answers are cached
- [x] Delete: `mark_term_and_sentence`, `_extract_sentence`, `_remove_word_marks`,
  `_remove_sentence_marks`, `TextOutputParser`, `find_nth_occurrence`, `detect_term_words`,
  `_get_or_create_model`, `AI_MODEL_API_KEY_ENV_VAR`, `AIModelSettings`, `safe_float`,
  `lexiflux/language/sentence_extractor_llm.py`, `lexiflux/resources/chat_models.yaml`,
  `tests/profile_llm.py`, `llm_benchmark.json`, `tests/test_sentence_extractor_llm.py`
- [x] Errors: llmbroker exceptions → `ArticleError(kind, html)` rendered from one
  template `lexiflux/templates/llm-error.html`. No message links to a settings page:
  - `NoLLMAvailableError(reason="no_keys")` → "The free pool needs at least one key" +
    each pool key's llmbroker `help` (Markdown link rendered) + where the key goes: its env
    var name, in `.env` locally and in Docker, in the server environment on Koyeb
  - `NoLLMAvailableError` with another reason → "busy, retry" (in N s from `retry_at` when
    present)
  - `MissingKeyError` → the provider's `key_help` + the env var name and where it goes
  - `AuthError` → "key rejected by <provider label>"
  - `RateLimitError` → "busy, retry in N s" from `retry_after` when present
  - `StreamInterruptedError`, `LLMTimeoutError` or `httpx.TransportError` after text → keep the
    text, add "answer cut off, retry"; `LLMTimeoutError` before any text → "busy, retry";
    `httpx.TransportError` before any text → the generic message
  - unknown model (dropped alias or dropped option) → current retired-model message
  - anything else → generic message with the exception text
- [x] Delete `lexiflux/templates/llm-error/` and `lexiflux/templates/llm-error-env/`,
  `get_llm_errors_folder`, `AIModelError`

## Phase 4 — Data model and the schema migration

- [x] `LexicalArticleType`: add `IN_DEPTH = "In depth"`; `LEXICAL_ARTICLE_PARAMETERS`: AI
  types take `model`, `effort`, `tier` (`AI` also `prompt`)
- [x] `LexicalArticle.clean()`: `model` must be an offered option; `effort`/`tier` must be
  in the model provider's vocabulary or absent; `pool` takes neither
- [x] Delete `AIModelConfig` and `SUPPORTED_CHAT_MODELS`. No key model replaces them
- [x] `DEFAULT_LEXICAL_ARTICLES` = the default-articles table above
- [x] Migration `0023_llmbroker.py`, schema-only, generated by `makemigrations`: delete
  `AIModelConfig`, alter `LexicalArticle.type` and `LanguagePreferences.inline_translation_type`
  choices. No `RunPython`: no data migration, the single user starts from a fresh DB

## Phase 5 — Views and UI

AI Settings removal:
- [x] Delete `ai_settings_views.py`, `ai-settings.html`, `ai-settings-vue.js`, their routes and
  the hamburger-menu link, and every other reference (grep `ai-settings`, `ai_settings`)

Article editor:
- [x] `language_preferences_views.py`: `ai_models` = offered models with title, provider,
  knob vocabulary and default knobs (from `ai_models.py`)
- [x] `lexical_artical_modal.html` + `language-preferences-vue.js`: after the model
  select, show "Reasoning effort" and "Processing tier" selects only when the provider
  has them; changing the model resets knobs to its defaults; tier `priority` shows the
  note "about 2× the price, about 3× faster (measured on Sol)"; article cards show model
  + knobs

Streaming:
- [x] New view `translate_stream` at `/translate/stream`, same GET params as `/translate`,
  for sidebar articles of **every** type: `StreamingHttpResponse(content_type="application/x-ndjson")`
  with headers `Cache-Control: no-cache`, `X-Accel-Buffering: no`. Events, one JSON
  object per line:
  `{"event":"delta","text":…}`, `{"event":"replace","text":…}`,
  `{"event":"error","html":…}`, `{"event":"site","url":…,"window":…}`, `{"event":"done"}`.
  Site and Dictionary articles emit one event and `done`
- [x] The stream response bypasses `GZipMiddleware`: Django's `compress_sequence` does not
  flush per chunk, so gzip would hold the NDJSON lines back until the answer ends. A test
  requests with `Accept-Encoding: gzip` and checks the response is not gzip-encoded
- [x] `/translate` keeps serving the inline popup (`lexical_article=0`) as JSON, through
  `generate_article`
- [x] `translate.ts`: sidebar panels call `/translate/stream`, read `response.body.getReader()`
  with `TextDecoder`, split on newlines; spinner until the first event; `delta` appends
  to a buffer and sets `innerHTML`; `replace` resets the buffer; `error` renders the HTML;
  `site` goes through the existing Site handling; `done` marks the panel updated. An
  `AbortController` per panel aborts when the selection changes or the panel is re-requested
- [x] Before `innerHTML`, the whole buffer goes through one Markdown-emphasis conversion
  (`**x**` → `<b>x</b>`, `*x*` → `<i>x</i>`); the inline popup uses the same function
- [x] AI article panels keep line breaks (`white-space: pre-line`) for every article type
  whose prompt forbids block tags (AI dictionary, In depth, and any other prompt rewritten to
  the same format rules); panels whose answers are HTML blocks are left as they are
- [x] `npm run build` / `invoke buildjs`

## Phase 6 — Keys in env, Docker, Ollama removal

- [x] `tasks.py` `rundocker`: add `--env-file .env` when `.env` exists
- [x] `.dockerignore`: add `.env`, as a guard in case a future `COPY . .` is added
- [x] `docker/Dockerfile`: remove `OLLAMA_LOAD_MODEL`, the Ollama binary copy and
  `start_ollama.sh`; `docker/start.sh`: remove the Ollama start line; delete
  `docker/start_ollama.sh`
- [x] Docs: `docs/src/en/docker.md` (`--env-file .env`, Ollama section removed),
  `docs/src/en/aimodels.md` rewritten: free pool, the three direct models with their
  measured trade-offs, knobs, where keys go (`.env` locally and in Docker, Koyeb secrets as
  env vars on Koyeb; `llmbroker env freetier` prints the pool key names and links), and that
  users do not enter keys. Other `docs/src/*` languages if they have these pages
- [x] `README.md`: key setup line

## Phase 7 — Tests, spec, verification

- [x] `tests/test_term_context.py`: single word, multi-word, selection across a sentence
  boundary, first/last word of page, a sentence under 6 words extended with its neighbours
  (and at the page edges); translation-history context format unchanged
- [x] `tests/test_ai_models.py`: `request_params` for every provider/knob combination;
  defaults per model; invalid knob rejected by `LexicalArticle.clean()`
- [x] `tests/test_broker.py`: `get_broker` builds one broker per process; the datasource
  follows the environment settings (`DATABASE_URL` on Koyeb, default storage locally);
  keys come from `llmbroker.Secrets` over the repo's `.env`
- [x] `tests/test_llm.py` rewritten over a fake llmbroker (`deltas`, `StreamReplacementError`,
  `StreamInterruptedError` / `LLMTimeoutError` / `httpx.TransportError` after text and before
  text, each error kind → message); cache hit replays one `delta`; the prompt contains the
  language names and word + sentence; closing the generator early closes the pool stream and
  the direct client
- [x] `tests/test_view_translate.py`: `/translate/stream` event sequences for AI, Site and
  Dictionary types; no gzip on the stream with `Accept-Encoding: gzip`; inline `/translate`
  unchanged
- [x] AI Settings: its URL answers 404 and the menu link is gone
- [x] `tests/test_llmbroker_contract.py` (modelled on echo-words' file of the same name):
  the installed catalog carries `gpt`, `gpt-fast` and `opus` with providers `openai`,
  `openai` and `anthropic`; every pool key has a non-empty `help`; sync `stream()` exists on
  the scoped `LLMs` and on `DirectClient`
- [x] `tests/test_default_languages_preferences.py`, `tests/test_view_language_preferences.py`:
  new defaults, knobs in parameters
- [x] Jest: NDJSON reader (split lines across chunks, `replace`, `error`, abort on a new
  selection); Markdown-emphasis conversion
- [x] Selenium (`tests/test_e2e_reader_page.py` and page models): new default tabs; no AI
  Settings menu item
- [x] `specs/ai-articles.md` (new; decisions and business rules only, per the global spec
  rules): pool for the default article and its persistent state on Koyeb, Sol none+priority
  for the others and why (echo-words numbers), the offered model set and what was left out
  and why, operator keys from the environment and no keys in lexiflux, streaming, word +
  sentence context with the Phase 1 result
- [x] `CLAUDE.md`: replace "LangChain-based chat models" and `chat_models.yaml` mentions

Verification:
```
source ./activate.sh && invoke pre
source ./activate.sh && invoke test
npm test
source ./activate.sh && invoke buildjs
source ./activate.sh && invoke selenium
```

Manual:
- `invoke run` with `.env` holding the pool keys and `OPENAI_API_KEY`: Article streams from
  the pool, In depth streams from Sol, and text appears in about a second; line breaks show
- Remove the pool keys from `.env`, restart: Article shows the no-key message with the pool
  key links and the env var names
- Switch selection while In depth streams: the request is aborted (server log shows the
  stream closed)
- `curl -N -H 'Accept-Encoding: gzip' '<stream url>'`: lines arrive one by one, uncompressed
- `invoke docker && invoke rundocker`: same as the first check, keys from `--env-file`
- Koyeb staging (`LEXIFLUX_ENV=koyeb`, keys as Koyeb secrets): articles work; after a
  redeploy the pool still answers fast (state in Postgres); streaming is not buffered by
  Koyeb's proxy (text arrives progressively)

## Phase 8 — Playwright e2e tests for the reader's AI panels

Selenium stays for the existing page tests. The streaming behaviour a browser alone can show
(text arriving progressively, abort on a new selection, rendering) gets Playwright tests.

- [x] `pytest-playwright` in `requirements.dev.in` (compile without `--upgrade`, so other pins
  stay), Chromium only; `playwright install chromium` in the dev setup (`activate.sh` or the
  documented setup step); CI installs it too if CI runs the e2e tests
- [x] Marker `playwright` in `pytest.ini`; tests in `tests/e2e_playwright/` (or next to the
  Selenium page models if that reads better), against pytest-django's `live_server`, headless by
  default, `--headed` for a visible run
- [x] A fake article stream for the tests: `stream_article` replaced by a generator that yields
  deltas with small delays and records when it was closed. The autouse guard against real LLM
  calls stays in force
- [x] Scenarios:
  - Article text appears progressively: the spinner goes at the first delta, and the panel shows
    partial text before `done`
  - a new selection while a panel streams aborts it: the old generator is closed server-side,
    late text never shows, the new article shows
  - `replace` resets the text; a `cut_off` error is appended after the text; another error
    replaces the panel; a stream ending without `done` gets the cut-off notice
  - Markdown `**x**`/`*x*` renders as bold/italic; the answer's line breaks show; an error alert
    has no blank gaps (computed style / element geometry)
  - the stream response has no `Content-Encoding`
  - the inline popup shows the translation, and an AI error as a formatted alert
  - the article editor: changing the model resets the knobs; the priority note shows for
    `priority`
- [x] One opt-in real smoke, `-m real_llm`, skipped unless `LEXIFLUX_REAL_LLM=1`: a real
  free-pool Article through the real broker in the browser, asserting first text under 3 s. Free
  pool only
- [x] `CLAUDE.md` and the testing docs: how to run the Playwright tests (headless, headed, the
  real smoke)

## Risks and open checks

- **Koyeb's edge proxy buffering NDJSON.** Checked in the Koyeb manual step. If it buffers,
  try a padding first chunk, then SSE framing over the same `fetch` reader.
- **`runserver` threads.** Each streaming request holds a thread for 3–10 s (up to about
  30 s on `opus`). Fine for current load; gunicorn with threads is the fallback.
- **The operator pays for every user's paid-model clicks** (In depth about $0.035). There is
  no per-user limit; if sign-ups are open, add a daily per-user limit as a follow-up.
- **Groq gpt-oss-120b in the pool** scored 2.2–2.5/5 with about two serious errors per
  article; it answers mostly while the pool is cold or Gemini stalls. Watch its share in the
  journal; if it is noticeable, move Article to Gemini Flash Lite on a paid key or disable
  Groq with `disable_llm`.
- **OpenRouter models in the pool** (`openrouter-nemotron-3-ultra`, `openrouter-laguna-s-2.1`):
  as the `fastest_of=2` second lane they turned Gemini 3.5 Flash Lite stalls into "busy"
  (7–13% of calls in bad windows). Nemotron holds the lane without text past 25 s; Laguna is
  mostly 429 on the shared free key. Resolved: `broker.get_broker()` disables them with
  `disable_llm` (`EXCLUDED_POOL_LLMS`), the no-key message lists only keys that serve a
  remaining pool model (`pool_keys()`), and `all_disabled` maps to the no-key message. A catalog
  rename shows as a warning in `test_the_excluded_pool_models_are_still_in_the_catalog`.
- **The stall rescue now rests on Groq alone.** `zai-glm-4.7-flash` behaves like Nemotron
  (200 at once, 13 of 16 answered calls had no text, 6 of them held the lane 20 s or more) and
  stays in the pool, as in echo-words. Under a simulated Gemini stall with Groq rate-limited,
  GLM was the second lane and every stalled call ended "busy" with or without the fix. Watch
  the journal's busy rate; if it stays above a few percent, disable GLM the same way.
- **llmbroker schema upgrades** drop the `llmbroker_*` tables on Koyeb: the learned model
  ordering and the journal are lost and the pool re-learns. No keys live there.
- **Catalog alias moves** (e.g. `gpt` → a new version). The knob defaults and measurements
  then describe an older model. llmbroker logs the move; re-measure with echo-words'
  `experiments/tier_screen.py`.
