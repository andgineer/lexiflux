# Replace LangChain with llmbroker: free pool, direct models, streaming

## Overview

lexiflux stops using LangChain. Every AI article goes through llmbroker:

- the default article (**Article**) asks the free-tier pool;
- every other AI article asks a named paid model directly, by default `gpt`
  (GPT-5.6 Sol) with reasoning off and priority processing: the configuration
  echo-words measured best for the "Подробнее" article on 2026-09-21;
- sidebar articles stream into the pane;
- the AI Settings page builds its key tabs from llmbroker's catalog and key hints
  instead of hard-coded provider classes;
- temperature is replaced by two per-article knobs, reasoning effort and processing
  tier, with measured defaults.

Evidence behind the model set and defaults: `../echo-words/spec/decision-llm-backend.md`,
sections "The deeper article: Sol, with reasoning off, on priority processing — 2026-09-21",
"Streamed racing with whole-answer replacement is the shipped adapter — 2026-09-06" and
"The paid tier: `gpt-5.6-luna` is the one worth reaching for".

## Decisions taken in the brainstorm

| Topic | Decision |
|---|---|
| Broker shape | One process-wide sync `llmbroker.Broker`; each request uses `broker.for_scope(f"u-{user.id}")` |
| Keys, cloud (Koyeb) | The user's own keys only. No env fallback for any key, pool or paid |
| Keys, local and Docker | The user's key if set, else env and `.env` in the repo root. `invoke rundocker` passes `--env-file .env` |
| Key migration | None. Old `AIModelConfig` rows are dropped |
| Article migration | One-time reset: every user's articles and inline-translation setting are recreated from the new defaults. Future migrations never delete user-defined articles |
| Offered models | `pool`, `gpt` (Sol), `gpt-fast` (Luna), `opus`. Sonnet, Haiku, gpt-mini, Gemini paid, Grok, DeepSeek, Mistral and Ollama are dropped |
| Knobs | Reasoning effort and processing tier, per article, with per-model defaults, only for providers where measured |
| Streaming | In v1. NDJSON over `fetch`; pool uses `fastest_of=2, wait=25` with whole-answer replacement |
| Serving | Stays WSGI (`runserver`). llmbroker gets a sync `stream()` |
| Term context | The prompt gets two plain values, the selected **word** and its **sentence**. The `[FRAGMENT]`/`[HIGHLIGHT]` marks go away. An experiment checks this before the prompt ships |
| Prompts | AI dictionary → echo-words short-article rules; new In depth → echo-words extended prompt verbatim; Origin gets the "only where you know it" rule; all prompts get language names instead of Google codes |

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

### Default articles (new users and the one-time reset)

| Title | Type | Parameters |
|---|---|---|
| Article | `AI dictionary` | `{"model": "pool"}` |
| In depth | `In depth` (new) | `{"model": "gpt", "effort": "none", "tier": "priority"}` |
| Sentence | `Sentence` | `{"model": "gpt", "effort": "none", "tier": "priority"}` |
| glosbe | `Site` | unchanged |

Inline translation: `Dictionary` / `GoogleTranslator` (unchanged default).
Any AI article type a user adds defaults to `gpt`, `none`, `priority`.

## Context (discovered in the brainstorm)

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
- `lexiflux/views/ai_settings_views.py`, `lexiflux/templates/ai-settings.html`,
  `lexiflux/templates/ai-settings-vue.js`
- `lexiflux/views/language_preferences_views.py` (line 88: `ai_models` from `chat_models`),
  `lexiflux/templates/language-preferences-vue.js`,
  `lexiflux/templates/partials/lexical_artical_modal.html` (model selects at lines 51, 70)
- `lexiflux/templates/llm-error/*.html`, `lexiflux/templates/llm-error-env/*.html` (12 files)
- `lexiflux/viewport/translate.ts`: `makeRequest` (line 148), `updateLexicalPanel` (430),
  `showSpinnerInLexicalPanel`
- `lexiflux/templates/reader.html` (article tabs, lines 155–171), `lexiflux/views/reader_views.py`
- `lexiflux/environments/{base,local,docker,koyeb}.py`, `lexiflux/lexiflux_settings.py`
  (`ui_settings_only`)
- `docker/Dockerfile` (Ollama: lines 15, 34, 41), `docker/start.sh` (line 3),
  `docker/start_ollama.sh`, `tasks.py` `rundocker` (line 304), `.dockerignore`
- `requirements.in` (lines 13–23), `requirements.koyeb.in` (lines 24–31)
- `tests/profile_llm.py`, `llm_benchmark.json`: the old profiler, superseded by the echo-words research
- `experiments/lexical_articles.ipynb`
- Docs: `docs/src/en/aimodels.md`, `docs/src/en/docker.md`

llmbroker (`../llmbroker`, v1.10.5):
- `src/llmbroker/sync.py`: sync `Broker`/`LLMs` over a background loop thread, no `stream()`
- `src/llmbroker/broker/broker.py`: `for_scope` (line 249) caches a `KeyRing` per scope;
  `rebuild` (267) is the only re-read
- `src/llmbroker/broker/keyring.py`: "The keys of one scope, read once and held until the
  pool is rebuilt"
- `src/llmbroker/broker/curated.py`: `curated_pool()`, `curated_paid()` (`CuratedModel.provider.id`),
  `curated_providers()` (`key_help`, `label`)
- `src/llmbroker/protocols/secrets.py`: `SecretsProtocol.resolve`, optional `refs(prefix)`
- `src/llmbroker/standalone/secrets.py`: `Secrets(env_file)`, env first, then the file
- `downstream.toml`: hosts checked on every llmbroker change

## Phase 0 — llmbroker: sync streaming and per-scope key refresh

Done in `../llmbroker`; lexiflux cannot stream under WSGI without it.

- [ ] Sync `stream()` on `Broker`, on the scoped `LLMs` (`for_scope`) and on the sync
  `DirectClient`, with the same arguments as the async ones (`operation`, `wait`,
  `fastest_of`, `stream_selection_window`; `params` on direct). It returns a sync iterator
  of text deltas that runs the async stream on the broker's loop thread and hands
  deltas back through a thread-safe queue
- [ ] The sync iterator raises the same exceptions at the same points:
  `StreamReplacementError` (with `.replacement`), `StreamInterruptedError`,
  `NoLLMAvailableError`, `MissingKeyError`, `AuthError`, `RateLimitError`
- [ ] Closing the iterator early (`close()` / garbage collection / `GeneratorExit` in the
  consumer) cancels the underlying async stream, so an aborted HTTP response stops the
  provider call
- [ ] Per-scope key refresh: a call on `AsyncBroker` and the sync `Broker` that drops one
  scope's cached `KeyRing`, so the next `for_scope(scope)` re-reads that scope's keys.
  Proposed name `forget_scope(scope)`; final name follows llmbroker's conventions. Record
  it in `specs/reference/decisions.md` next to `the-broker-is-the-installation-a-caller-is-a-scope`
- [ ] Tests in llmbroker for the sync stream (deltas, replacement, interruption, early
  close cancels) and for `forget_scope` (a changed key is used on the next call; other
  scopes keep their rings)
- [ ] Docs: `docs/src/en/async.md` and `docs/src/en/direct.md` stop saying streaming is
  async-only; `docs/src/en/server.md#multiuser` documents `forget_scope`
- [ ] Add lexiflux to `downstream.toml` as a host (after Phase 2 lands, so its tests exist)
- [ ] Release a new llmbroker version to PyPI

Verify: `cd ../llmbroker && source ./activate.sh && invoke test && invoke downstream`

## Phase 1 — Experiment: word + sentence context for the default article

Runs on llmbroker 1.10.5 (async API). Can run in parallel with Phase 0. It decides the
wording of the new AI dictionary prompt before Phase 3 ships it.

Harness: `experiments/context_bench.py` (outside CI; `experiments/` is in `.dockerignore`).

- [ ] Items: 24, eight each of English, German, Serbian (Cyrillic and Latin mixed), target
  language English. Each item is a real sentence (from `tests/resources` books where one
  fits) plus the selected word ids, covering:
  - polysemy where the sense in the sentence is not the most common one
    (en `spring`/`fine`, de `Schloss`/`Bank`, sr `град` hail, `коса` scythe)
  - a word repeated in its sentence in different senses (the one case the marks disambiguate)
  - a separable or reflexive verb with only one piece selected (de `steht` in `Er steht um sieben auf`, sr `се`)
  - a multi-word selection
  - a sentence NLTK cuts short (abbreviation, dialogue line) where the neighbouring
    sentence carries the sense
- [ ] Arms:
  - **A**: current `AI dictionary.txt` prompt, current marked passage (`mark_term_and_sentence`
    with 10 context words)
  - **B**: new prompt (echo-words short-article rules, see Phase 3), marked passage
  - **C**: new prompt, `word` + `sentence`
- [ ] Hold the model fixed across arms: declare the pool's two workhorses,
  `google-gemini-3.5-flash-lite` and `groq-gpt-oss-120b`, as custom `LLMConfig`s from
  `curated_pool().configs` under their own names and call them with `direct()`. Run each
  arm on both. Also run arm C once through the real pool (`stream`, `fastest_of=2`, `wait=25`)
  as a production-shaped smoke
- [ ] Record per answer: text, model, first-delta and whole-answer latency, length
- [ ] Blind review as in echo-words: one fresh reviewer (Claude subagent) per four words
  of one language, scoring every arm's answer to a word side by side under labels drawn
  afresh per word, anchored 5 = nothing false and useful, 2 = a serious error in the core,
  1 = several. Each reviewer also records per answer:
  - leads with the sense used in the sentence (yes/no)
  - heads the selected unit's lemma, or the whole separable/reflexive unit (yes/no)
  - every serious error, quoted
  - contract: only `<b>`, `<i>`, `<table>`, `<tr>`, `<td>`; no Markdown or code fences;
    written in the target language
- [ ] Decision rule: ship **C** unless **B** beats it on context-sense hits or serious
  errors with a 95% paired bootstrap interval excluding zero. **A** vs **B** is reported as
  the value of the prompt change alone. If B wins only on the repeated-word class, ship C
  and add the occurrence index to the prompt (e.g. `the second "saw"`) as a follow-up
- [ ] In depth smoke on `gpt`, none, priority: 6 items with the `context_note` form, to
  confirm the HTML contract and length in lexiflux's pane (≈ $0.25)
- [ ] Write the result, with the numbers, into `specs/ai-articles.md` (Phase 7)

Verify: `source ./activate.sh && python experiments/context_bench.py --arms A,B,C --out experiments/context_bench.json`

## Phase 2 — Dependencies and the broker module

- [ ] `requirements.in` and `requirements.koyeb.in`: remove `langchain`, `langchain-community`,
  `langchain-core`, `langchain-openai`, `langchain_anthropic`, `langchain_google_genai`,
  `langchain_mistralai`, `langchain_ollama`, `openai`, `ollama`; add `llmbroker>=<Phase 0 version>`
- [ ] `source ./activate.sh && invoke reqs`; Koyeb env: `source .venv-koyeb/bin/activate && uv pip install -r requirements.koyeb.txt`
- [ ] New `lexiflux/language/broker.py`:
  - `get_broker() -> llmbroker.Broker`: lazily created once per process, `direct=` the
    aliases of the offered models, `secrets=LexifluxSecrets()`; closed at process exit
  - `llms_for(user) -> LLMs`: `get_broker().for_scope(f"u-{user.id}")`
  - `forget_user_keys(user)`: calls the Phase 0 per-scope refresh
- [ ] `LexifluxSecrets` implements `SecretsProtocol.resolve` and `refs(prefix)`, **async,
  using Django's async ORM** (`afirst`, async iteration). It runs on the broker's loop
  thread, where the sync ORM raises `SynchronousOnlyOperation`:
  - `u-<id>/<REF>` → that user's stored key for `<REF>`
  - bare `<REF>` → `llmbroker.Secrets(BASE_DIR / ".env").resolve(ref)` when
    `settings.LLM_KEYS_FROM_ENV` is true, else missing (follow the protocol's missing-key convention)
  - `refs("u-<id>/")` → that user's stored refs, one query
- [ ] `LLM_KEYS_FROM_ENV`: `True` in `environments/local.py` and `environments/docker.py`,
  `False` in `environments/koyeb.py`
- [ ] New `lexiflux/language/ai_models.py`: the offered-model table and knob vocabulary
  above; `request_params(model, effort, tier) -> dict`; `default_knobs(model)`;
  `provider_of(model)` read from `curated_paid()` by alias. A catalog alias that
  disappears makes that option unavailable, and its articles show the retired-model message

## Phase 3 — Context, prompts and article generation

- [ ] New `term_context(page, term_word_ids) -> TermContext(word, sentence)` (in
  `lexiflux/language/`), using `page.words` and `page.word_sentence_mapping`: the sentence
  is the span of all words whose sentence id lies between the first and last selected
  word's sentence ids, HTML-stripped with `extract_content_from_html`. Also returns the
  offsets `get_context_for_translation_history` needs
- [ ] Rewrite `get_context_for_translation_history` on those offsets. The stored format
  (`TranslationHistory.CONTEXT_MARK` around the sentence and in place of the term, ≥10
  context words expanded to full sentences) stays identical; a test pins it
- [ ] Prompts in `lexiflux/resources/prompts/`, with placeholders `{word}`, `{sentence}`,
  `{text_language}`, `{user_language}` (language **names** from `Language.name`):
  - `AI dictionary.txt`: echo-words `_INTRO` + `_SELECTED_ARTICLE` + `_FORMAT_RULES`
    from `../echo-words/src/echo_words/prompt.py`, without the `===CARD===` JSON parts;
    the request line in the form Phase 1 selected
  - `In depth.txt`: echo-words `_EXTENDED_PROMPT` verbatim, `bound` = 4000 characters,
    `context_note` = `The word was met in this context: "{sentence}"`
  - `Origin.txt`: replace "Time period of first known use" with echo-words rule 5 ("Origin
    only where you know it … leave it out")
  - `Sentence.txt`: takes `{sentence}` only
  - `Translate.txt`, `Explain.txt`, `Lexical.txt`: rewritten from marks to `{word}` +
    `{sentence}`, otherwise unchanged
  - custom `AI` type: system = user's prompt, user message = word + sentence
- [ ] Rewrite `lexiflux/language/llm.py` without LangChain:
  - `ArticleRequest(article_type, model, effort, tier, prompt, word, sentence,
    text_language, user_language, user)` built by the view
  - `stream_article(req) -> Iterator[ArticleEvent]` for sidebar articles:
    - `pool` → `llms_for(user).stream(prompt, operation=article_type, fastest_of=2, wait=25)`;
      on `StreamReplacementError` emit `replace(exc.replacement.text)`
    - direct → `llms_for(user).direct(model).stream(prompt, params=request_params(...))`
    - on `StreamInterruptedError` after text: emit the error event, keep the text
  - `generate_article(req) -> str` for the inline popup (`lexical_article=0`): same
    routing via `ask`
  - Finished-article cache: key = (user id, article type, prompt text, model, effort,
    tier, word, sentence, languages), a bounded dict; a hit replays as one `delta`. Only
    complete answers are cached
- [ ] Delete: `mark_term_and_sentence`, `_extract_sentence`, `_remove_word_marks`,
  `_remove_sentence_marks`, `TextOutputParser`, `find_nth_occurrence`, `detect_term_words`,
  `_get_or_create_model`, `AI_MODEL_API_KEY_ENV_VAR`, `AIModelSettings`, `safe_float`,
  `lexiflux/language/sentence_extractor_llm.py`, `lexiflux/resources/chat_models.yaml`,
  `tests/profile_llm.py`, `llm_benchmark.json`, `tests/test_sentence_extractor_llm.py`
- [ ] Errors: `llmbroker` exceptions → `ArticleError(kind, html)` rendered from one
  template `lexiflux/templates/llm-error.html`:
  - `NoLLMAvailableError(reason="no_keys")` → "The free pool needs at least one key" +
    each pool key's llmbroker `help` (Markdown link rendered) + link to its AI Settings tab
  - `MissingKeyError` → the provider's `key_help` + tab link
  - `AuthError` → "key rejected by <provider label>" + tab link
  - `RateLimitError`, `NoLLMAvailableError(reason="timeout")` → "busy, retry in N s" from
    `retry_after`/`retry_at` when present
  - `StreamInterruptedError` → "answer cut off, retry"
  - unknown model (dropped alias or dropped option) → current retired-model message
  - anything else → generic message with the exception text
  - When `LLM_KEYS_FROM_ENV` is true the key hints also name the env var and `.env`
- [ ] Delete `lexiflux/templates/llm-error/` and `lexiflux/templates/llm-error-env/`,
  `get_llm_errors_folder`, `AIModelError`

## Phase 4 — Data model and the one-time reset migration

- [ ] `LexicalArticleType`: add `IN_DEPTH = "In depth"`; `LEXICAL_ARTICLE_PARAMETERS`: AI
  types take `model`, `effort`, `tier` (`AI` also `prompt`)
- [ ] `LexicalArticle.clean()`: `model` must be an offered option; `effort`/`tier` must be
  in the model provider's vocabulary or absent; `pool` takes neither
- [ ] New model `ProviderKey(user FK, api_key_ref, value)`, `unique_together (user, api_key_ref)`;
  delete `AIModelConfig` and `SUPPORTED_CHAT_MODELS`
- [ ] `DEFAULT_LEXICAL_ARTICLES` = the default-articles table above
- [ ] Migration `0023_...`:
  - schema: create `ProviderKey`, delete `AIModelConfig`, alter `LexicalArticle.type` and
    `LanguagePreferences.inline_translation_type` choices
  - `RunPython`: delete every `LexicalArticle`; for every `LanguagePreferences` create the
    default articles and set inline translation to `Dictionary`/`GoogleTranslator`. The
    defaults are **copied into the migration file**, not imported, so a later change
    to `DEFAULT_LEXICAL_ARTICLES` cannot change what this migration did
  - reverse: no-op (documented as irreversible for data)
- [ ] Comment at the top of the `RunPython` function: this reset is the only migration
  allowed to delete user-defined articles

## Phase 5 — Views and UI

AI Settings:
- [ ] `ai_settings_api` GET returns one entry per distinct `api_key_ref`, in this order:
  pool keys from `curated_pool().keys` (sorted by their `value` extra, high first), then the
  providers of the offered direct models from `curated_providers()`. Each entry has the
  title (provider `label`, or the ref without `_API_KEY` for pool keys), help HTML, which
  models it pays for ("Free pool", "GPT-5.6 Sol", …) and status `yours` / `env` (only when
  `LLM_KEYS_FROM_ENV`) / `missing`. The key value is never returned
- [ ] POST saves `{api_key_ref: value}`, where an empty value deletes, then calls
  `forget_user_keys(user)`
- [ ] Rewrite `ai-settings.html` / `ai-settings-vue.js`: tabs from the GET list, one
  password field per tab, status badge, no temperature, no hard-coded provider text.
  `?tab=` takes an `api_key_ref` (error-message links use it)

Article editor:
- [ ] `language_preferences_views.py`: `ai_models` = offered models with title, provider,
  knob vocabulary and default knobs (from `ai_models.py`)
- [ ] `lexical_artical_modal.html` + `language-preferences-vue.js`: after the model
  select, show "Reasoning effort" and "Processing tier" selects only when the provider
  has them; changing the model resets knobs to its defaults; tier `priority` shows the
  note "about 2× the price, about 3× faster (measured on Sol)"; article cards show model
  + knobs

Streaming:
- [ ] New view `translate_stream` at `/translate/stream`, same GET params as `/translate`,
  for sidebar articles of **every** type: `StreamingHttpResponse(content_type="application/x-ndjson")`
  with headers `Cache-Control: no-cache`, `X-Accel-Buffering: no`. Events, one JSON
  object per line:
  `{"event":"delta","text":…}`, `{"event":"replace","text":…}`,
  `{"event":"error","html":…}`, `{"event":"site","url":…,"window":…}`, `{"event":"done"}`.
  Site and Dictionary articles emit one event and `done`
- [ ] `/translate` keeps serving the inline popup (`lexical_article=0`) as JSON, through
  `generate_article`
- [ ] `translate.ts`: sidebar panels call `/translate/stream`, read `response.body.getReader()`
  with `TextDecoder`, split on newlines; spinner until the first event; `delta` appends
  to a buffer and sets `innerHTML`; `replace` resets the buffer; `error` renders the HTML;
  `site` goes through the existing Site handling; `done` marks the panel updated. An
  `AbortController` per panel aborts when the selection changes or the panel is re-requested
- [ ] `npm run build` / `invoke buildjs`

## Phase 6 — Keys from `.env`, Docker, Ollama removal

- [ ] `tasks.py` `rundocker`: add `--env-file .env` when `.env` exists
- [ ] `.dockerignore`: add `.env`, as a guard in case a future `COPY . .` is added
- [ ] `docker/Dockerfile`: remove `OLLAMA_LOAD_MODEL`, the Ollama binary copy and
  `start_ollama.sh`; `docker/start.sh`: remove the Ollama start line; delete
  `docker/start_ollama.sh`
- [ ] Docs: `docs/src/en/docker.md` (`--env-file .env`, Ollama section removed),
  `docs/src/en/aimodels.md` rewritten: free pool, the three direct models with their
  measured trade-offs, knobs, where keys go (AI Settings; `.env` locally and in Docker;
  `llmbroker env freetier` prints the pool key names and links). Other `docs/src/*`
  languages if they have these pages
- [ ] `README.md`: key setup line

## Phase 7 — Tests, spec, verification

- [ ] `tests/test_term_context.py`: single word, multi-word, selection across a sentence
  boundary, first/last word of page; translation-history context format unchanged
- [ ] `tests/test_ai_models.py`: `request_params` for every provider/knob combination;
  defaults per model; invalid knob rejected by `LexicalArticle.clean()`
- [ ] `tests/test_secrets.py`: scoped key found; bare ref from env/`.env` only when
  `LLM_KEYS_FROM_ENV`; Koyeb settings never read env; `refs(prefix)`; runs under the
  async ORM
- [ ] `tests/test_llm.py` rewritten over a fake llmbroker (`deltas`, `StreamReplacementError`,
  `StreamInterruptedError` after text, each error kind → message); cache hit replays one
  `delta`; the prompt contains the language names and word + sentence
- [ ] `tests/test_view_translate.py`: `/translate/stream` event sequences for AI, Site and
  Dictionary types; inline `/translate` unchanged
- [ ] `tests/test_view_ai_settings.py`: tab list follows a stubbed catalog (adding a pool
  key adds a tab); save / delete; `forget_user_keys` called on save; values never returned
- [ ] `tests/test_llmbroker_contract.py` (modelled on echo-words' file of the same name):
  the installed catalog carries `gpt`, `gpt-fast` and `opus` with providers `openai`,
  `openai` and `anthropic`; every pool key has a non-empty `help`; sync `stream()` and
  per-scope key refresh exist
- [ ] Migration test: users with custom articles and an LLM inline translation end up
  with exactly the defaults
- [ ] `tests/test_default_languages_preferences.py`, `tests/test_view_language_preferences.py`:
  new defaults, knobs in parameters
- [ ] Jest: NDJSON reader: split lines across chunks, `replace`, `error`, abort on a new selection
- [ ] Selenium (`tests/test_e2e_reader_page.py` and page models): new default tabs
- [ ] `specs/ai-articles.md` (new; decisions and business rules only, per the global spec
  rules): pool for the default article, Sol none+priority for the others and why (echo-words
  numbers), the offered model set and what was left out and why, keys per user in cloud
  and env fallback locally, streaming, word + sentence context with the Phase 1 result,
  "migrations never delete user-defined articles"
- [ ] `CLAUDE.md`: replace "LangChain-based chat models" and `chat_models.yaml` mentions

Verification:
```
source ./activate.sh && invoke pre
source ./activate.sh && invoke test
npm test
source ./activate.sh && invoke buildjs
source ./activate.sh && invoke selenium
```

Manual:
- `invoke run` with `.env` holding a pool key and `OPENAI_API_KEY`: Article streams from
  the pool, In depth streams from Sol, and text appears in about a second
- Remove the pool key from `.env`, restart: Article shows the no-key message with the
  four pool-key links; the link opens the right tab
- Save a pool key in AI Settings without restarting: the next click works
- Switch selection while In depth streams: the request is aborted (server log shows the
  stream closed)
- `invoke docker && invoke rundocker`: same as the first check, keys from `--env-file`
- Koyeb staging (`LEXIFLUX_ENV=koyeb`): no key read from env; streaming is not buffered by
  Koyeb's proxy (text arrives progressively)

## Risks and open checks

- **Koyeb's edge proxy buffering NDJSON.** Checked in the Koyeb manual step. If it buffers,
  try a padding first chunk, then SSE framing over the same `fetch` reader.
- **`runserver` threads.** Each streaming request holds a thread for 3–10 s (up to about
  30 s on `opus`). Fine for current load; gunicorn with threads is the fallback.
- **Catalog alias moves** (e.g. `gpt` → a new version). The knob defaults and measurements
  then describe an older model. llmbroker logs the move; re-measure with echo-words'
  `experiments/tier_screen.py`.
- **Pool latency without echo-words' prompt size.** The pool numbers come from
  echo-words' short article plus card JSON. The Phase 1 production-shaped smoke confirms
  them for lexiflux's prompt.
