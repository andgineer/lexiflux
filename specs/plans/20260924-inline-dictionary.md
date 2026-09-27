# Inline popup: LLM translation by default, online Wiktionary, Google via its JSON endpoint

## Overview

The inline popup (a click on a word) currently asks `deep_translator`'s GoogleTranslator. It
scrapes `translate.google.com/m`, which Google now redirects to its "sorry" page, and it translates
the bare word, so it guesses the sense (6 of 24 bench items right). This plan replaces the popup's
translators:

- **LLM translation (default):** the free llmbroker pool translates the selected word in its
  passage and returns only the Russian (user-language) equivalent. 23 of 24 bench senses right,
  answer in about 0.6 s p50, 0.8 s p90
- **Wiktionary:** a local lemmatiser plus the kaikki.org per-word Wiktionary pages, fetched online:
  senses with user-language equivalents (English words, and every word in the Russian edition) or
  English glosses, lemma lookup for inflected forms, both Serbian scripts. 21 of 24 bench senses
  listed, about 0.13 s p50, nothing installed, no keys. (Phase 2 built it offline first; Phase 6
  replaces that with the online lookup, because users must never run a data import)
- **Google:** the same Google engine through its JSON endpoint `translate.googleapis.com`, with
  dictionary alternatives for English and German. Fast (0.07 s) but context-blind and fragile
  (Google blocks client identifiers without notice)

MyMemory, Linguee, PONS and the `deep-translator` package go. For Serbian books, the sidebar gains a
Lingea Site article next to Glosbe for every reader language Lingea covers.

Evidence: the translator study (`scratchpad/translator/`, summarised below) and the dictionary
study (`scratchpad/dictionary/`), both 2026-09-24, on the 24 items of `experiments/context_bench.py`;
the online-Wiktionary study (`scratchpad/hybrid/`, 2026-09-25/26: bench, 45 inflected forms, Alice's
200 most frequent words, 20 contractions and archaic forms, latency, 1,309 real requests).

Research directories (read-only):
`/private/tmp/claude-501/-Users-andrei-sorokin2-projects-lexiflux/c28e1697-199b-43f9-8f46-671dd8a20d4d/scratchpad/{translator,dictionary}`,
`/private/tmp/claude-501/-Users-andrei-sorokin2-projects-lexiflux/03fa7c10-fa32-4e88-b4f5-b1eaea141c0d/scratchpad/hybrid`.

## Decisions

| Topic | Decision |
|---|---|
| Popup options | Three: LLM translation (default), Wiktionary, Google. The user picks one in Language Preferences; the choice is per language as today |
| No fallback | A popup translator never falls back to another one. If the LLM translation fails or has no answer after **3 s**, the popup shows an error alert (the existing alert style); same for Google and a missing Wiktionary entry |
| LLM translation | Free pool only (`fastest_of=2`), context = the selected word marked inside a short passage (its sentence plus the neighbouring sentences), reply = only the user-language equivalent in dictionary form; the whole unit for separable verbs and fixed expressions. Non-streaming (the popup shows the finished answer). Cached per (word, passage, languages) like the article cache. Failures are not cached |
| Wiktionary data | Online, nothing installed: the clicked word is lemmatised locally (simplemma, a pip dependency; English, German, Serbian in both scripts), then the kaikki.org per-word pages of the word and its lemma are fetched from the Russian and the English Wiktionary editions in parallel. No local dictionary file, no import command. Licence CC BY-SA 4.0 + GFDL: every Wiktionary result shows "from Wiktionary, CC BY-SA 4.0" with a link |
| Wiktionary output | A compact list of senses: part of speech, user-language equivalents where the data has them, otherwise English glosses; the clicked word's own entry and the entry of its lemma. For a Russian reader, Russian-edition data first. A form, contraction or archaic word the lemmatiser leaves unchanged follows its own "form of" link to the lemma |
| Wiktionary unreachable | kaikki.org down, slow or refusing: the popup shows the translator network-error alert ("Wiktionary (kaikki.org) is not reachable"); no page for the word: the "no translation" alert. Failures are never cached |
| Google client | Direct HTTP to the JSON endpoint with client identifiers tried in order `dict-chrome-ex`, `gtx`, `at`; `dt=bd` alternatives shown when present (English, German); a short timeout; the existing translator error alerts on failure |
| Removed | `deep-translator` (MyMemory, Linguee, PONS, its Google scraper) |
| Defaults | Inline translation = LLM translation for new users. Single user, no existing data to migrate: the author recreates his DB (`invoke init-db`) |
| No manual steps | A lexiflux user never runs a command to install or refresh data. Everything a translator needs is fetched automatically or ships with the app's dependencies |
| Vocabulary history | The translation saved for a looked-up word (and exported to Anki) is always the LLM translation of the word in the passage it was looked up in, whatever the popup's translator. With LLM translation as the popup, its answer is saved. With Wiktionary or Google, the popup shows its own answer at once and the LLM translation fills the history in the background; a context-free dictionary never chooses the saved sense. Until the LLM answer arrives, or if the pool fails, a new entry holds the translator's first line and is retried on the word's next lookup; an entry that already has an LLM translation keeps it |
| Serbian Site link | Glosbe stays the default Site article for every language (its real-world example sentences are the point). A Serbian book whose reader's language Lingea covers (36 `<language>-srpski` dictionaries) gets a second Site article, Lingea (`https://recnici.lingea.rs/{toLangLingea}-srpski/{termLatin}`: the user language in Lingea's naming, Cyrillic terms transliterated to Latin), after Glosbe: it resolves inflected Serbian forms and separates homonyms, which Glosbe's page does not |

### Measurements behind the decisions (2026-09-24, 24 items, en/de/sr → ru)

| Option | Right sense | Latency | Notes |
|---|---|---|---|
| LLM pool, word in its passage | 23 / 24 (sense chosen) | 0.63 / 0.81 s (p50 / p90) | quota: Groq about 1,000 requests a day, Gemini about 500, shared with the sidebar articles |
| Wiktionary online (lemmatiser + kaikki.org pages, measured 2026-09-25/26) | 21 / 24 listed (dictionary form), 19 / 24 from the clicked text | 0.13 / 0.26 s (p50 / p90) | inflected forms 42 / 45; the first entry is the word or its lemma for all of Alice's 200 most frequent words (a head-word check, not a sense check); contractions and archaic forms 20 / 20. Saved history translation (hand-judged, 50 Alice words in their first passage): Wiktionary's first sense 24 / 50, the LLM translation in context 47 / 50 |
| Google `dt=bd` | 15 / 24 listed, 6 / 24 as the single answer | 0.07 s | no Serbian dictionary data |
| MyMemory | 3 / 24 | 0.42 s | dropped |

## Context

- `lexiflux/language/translation.py`: `Translator`, `AVAILABLE_TRANSLATORS` (deep_translator
  Google, MyMemory, Linguee, Pons), `get_translator`
- `lexiflux/views/lexical_views.py`: `get_lexical_article` (Dictionary branch),
  `_dictionary_article`, `_dictionary_error`, `_safe_dictionary_article`, `translate` (inline
  popup), `_article_events` (sidebar stream), `term_context` use
- `lexiflux/templates/translator-error.html`, `lexiflux/templates/llm-error.html`
- `lexiflux/language/llm.py`: `ArticleRequest`, `generate_article`, the article cache, `llms_for`
- `lexiflux/language/term_context.py`: `term_context` (word, sentence, spans; short-sentence
  extension)
- `lexiflux/models.py`: `LexicalArticleType.DICTIONARY`, `LEXICAL_ARTICLE_PARAMETERS["Dictionary"]
  = ["dictionary"]`, `LexicalArticle.clean()` (Dictionary branch), `LanguagePreferences`
- `lexiflux/language_preferences_default.py`: `DEFAULT_INLINE_TRANSLATION`,
  `DEFAULT_LEXICAL_ARTICLES` (the Glosbe Site article), `create_default_language_preferences`
- `lexiflux/views/language_preferences_views.py` and `language-preferences-vue.js`: the inline
  translation editor (dictionary select)
- `lexiflux/viewport/translate.ts`: inline popup rendering (`updateTranslationSpan`, error HTML)
- `requirements.in`: `deep-translator`, `googletrans` (kept: `detect_language_googletrans.py`)
- Research scripts to reuse: `scratchpad/translator/` (`reliability.py`, `pool_bench_passage.py`,
  the pool prompt), `scratchpad/dictionary/` (`dict_bench.py`, `pruned.sqlite` trial,
  `surface_forms.txt`)

## Phase 1 — Google through the JSON endpoint

- [x] New Google client in `lexiflux/language/translation.py` (httpx): `translate_a/single` with
  `sl`, `tl`, `dt=t` and `dt=bd`; client identifiers tried in order `dict-chrome-ex`, `gtx`, `at`,
  moving on only on HTTP 429/403 or a non-JSON answer; timeout 3 s
- [x] Output: the translation plus, when present, the `dt=bd` alternatives grouped by part of speech
- [x] Failures raise the errors the existing alert mapping understands (rate limit, network, no
  translation)
- [x] Tests over `httpx.MockTransport`: identifier rotation, alternatives parsing, each failure kind

## Phase 2 — Offline Wiktionary

- [x] Management command `import-wiktionary` (next to the `import-*` commands): downloads the six
  kaikki.org extracts (streamed, resumable if cheap), prunes each entry to lemma, language, part of
  speech, senses (English gloss, user-language translations with their sense label), form-of links
  and inflected forms, and writes a separate SQLite file (path from a setting, default next to the
  app database; gitignored; excluded from Docker builds). Rebuild replaces the file atomically
- [x] Lookup module in `lexiflux/language/` (for example `wiktionary.py`): surface form → lemma(s)
  through the forms index; Serbian Cyrillic ↔ Latin transliteration so either script finds the
  entry; entries from the Russian edition first, then the English edition; returns structured senses
- [x] Rendering: a compact HTML list (part of speech, equivalents or glosses), user-language
  equivalents first, then English glosses; the attribution line with a link
- [x] Missing data file → the "not installed" alert with the command
- [x] Tests on a tiny JSONL fixture: import, lemma lookup from an inflected form (en, de, sr in both
  scripts), multi-word entries, missing entry, missing data file, attribution present
- [x] Measure: the real import's size and time (report them); lookup latency

Done notes (2026-09-24):

- kaikki.org deprecated the per-language files (wiktextract issue #1178) and tells users to filter
  the raw edition dumps by `lang_code`, so the command downloads the two raw dumps
  (`dictionary/raw-wiktextract-data.jsonl.gz`, `ruwiktionary/raw-wiktextract-data.jsonl.gz`) and
  keeps the six language subsets. Downloads go to `wiktionary-downloads/` next to the data file,
  resume with `Range`/`If-Range`, are reused with `--keep-downloads` while the ETag is unchanged,
  and are deleted after a successful build otherwise
- Measured: download 3,208 MB (2,901 + 307) in 70 s, build 122 s (194 s wall, 222 MB peak RSS),
  `wiktionary.sqlite3` 228 MB (1.12 M entries, 1.66 M form links); lookup 0.15 / 0.21 ms
  (p50 / p90, SQLite open included), lookup + HTML 0.22 / 0.48 ms
- The translator is registered as `Wiktionary` in `AVAILABLE_TRANSLATORS` and returns
  `HtmlTranslation` (trusted HTML + the plain first sense for the history); the views pass it
  through unescaped (`"html": true` in the popup JSON)
- Translations of English words are kept for Russian plus the user languages in Language
  Preferences (`--translations` overrides)

## Phase 3 — LLM translation for the popup

- [x] New prompt `lexiflux/resources/prompts/Inline translation.txt` from the study's prompt:
  translate the marked word or phrase into the user language in the sense it has in the passage;
  the whole unit for separable verbs and fixed expressions; reply with only the translation in
  dictionary form
- [x] Context: the selected word marked inside its sentence plus the previous and next sentence
  (from `term_context`'s spans)
- [x] Call: the free pool, `fastest_of=2`; a hard **3 s** limit on the whole answer. On timeout or
  any llmbroker error → an error alert (reuse the `ArticleError` mapping and templates), never
  another translator
- [x] Cache complete answers per (word, passage, languages); never cache failures
- [x] Tests over the fake llmbroker: answer shown, timeout at 3 s gives the alert, error kinds,
  cache hit, prompt contains the marked word and passage and the language names

Done notes (2026-09-25):

- The prompt is the study's pool prompt word for word (it still says "in the sense it has in
  this sentence" and labels the passage `Text:`), with the languages as placeholders. The marks
  are `⟦ ⟧`; `TermContext.passage` carries the marked passage for every request
- Translators now take a `Term` (word, marked passage, user) instead of the bare word, so the LLM
  translator fits the same registry entry shape: `AVAILABLE_TRANSLATORS["LLMTranslation"]`,
  label "LLM translation" (not the default yet, not first in the list). Views pass language names
  as stored (`English`, not `english`); Google and Wiktionary map them to codes, the LLM
  translation puts them into the prompt as they are
- Each translator owns its cache: Google per word inside the client, the LLM translation in the
  article cache keyed (word, passage, languages) without the user, Wiktionary none. The
  `Translator` wrapper no longer caches
- The pool call is `ask(fastest_of=2, wait=3)` run in a daemon thread and abandoned at 3 s:
  llmbroker's `wait` bounds its first pass but not the second pass it makes after re-reading
  keys on exhaustion. A timeout renders the "busy" alert; a late answer is dropped, not cached
- One error path: `_dictionary_error` passes an `ArticleError` through (kind + `llm-error.html`)
  and maps every other translator failure to `translator-error.html`. An empty answer is the
  translator "found no translation" alert
- The editor's Dictionary check constructs the translator instead of translating "test", so
  saving an LLM translation spends no pool call
- Real free pool (2026-09-25, lexiflux's `.llmbroker` store; its `disabled.yml`, model list and
  free-tier preset are identical to echo-words'): all 24 bench items answered, 23 / 24 senses
  right (`sr-grad` → "город"), 0.59 / 0.78 s p50 / p90, max 0.86 s; Groq and Gemini each won 12
  races. An earlier 14-item round: 12 / 14 (`de-aufstehen` answered in German "aufstehen", as
  Gemini Flash Lite also did once in the study; `en-make-out` → "расслышать"), p90 0.73 s.
  lexiflux's sentence splitter cuts at `?”` and `св.`, so 2 of 24 passages end one sentence
  earlier than the study's hand-made ones; both were still answered right

## Phase 4 — Options, defaults and the editor

- [x] Translator registry with three options (LLM translation, Wiktionary, Google); the Dictionary
  article type's `dictionary` parameter selects one; validation in `LexicalArticle.clean()` and the
  editor's list follow the registry
- [x] `DEFAULT_INLINE_TRANSLATION` = LLM translation
- [x] Sidebar Dictionary articles use the same registry (Wiktionary's sense list is useful there too)
- [x] Serbian + Russian: a Lingea Site article is added after Glosbe (Glosbe unchanged); a `{term}`
  for Lingea is transliterated to Latin (a URL placeholder or a Lingea-specific rule; choose the
  simpler)
- [x] Remove `deep-translator` from `requirements.in`; recompile without `--upgrade`; remove every
  import and test of MyMemory, Linguee, PONS

Done notes (2026-09-25):

- Registry keys, in order: `LLMTranslation` ("LLM translation"), `Wiktionary`, `Google`
  ("Google"). The editor shows the labels (also in generated article titles); saved preferences
  and Dictionary articles with any other key fail validation (`validate_dictionary` in
  `models.py`, used by `LexicalArticle.clean()` and `LanguagePreferences.clean()`)
- The editor's save check rejects an unknown key and a pair a translator reports as unsupported
  (`TranslatorError` kind `unsupported`, raised by the constructors: Google for a language outside
  its list, Wiktionary for a book language without data). No translation, pool call or network
  call is made
- Lingea uses a new Site URL placeholder `{termLatin}`: the term with Serbian Cyrillic in Latin
  (Wiktionary's transliteration table, extended with capitals: `serbian_latin`). The placeholder
  is listed in the Site editor hint and the Lingea URL in the predefined URLs
- Lingea is not Russian-only: `https://recnici.lingea.rs/{toLangLingea}-srpski/{termLatin}`.
  The Site URL placeholder `{toLangLingea}` is the user language as Lingea's slug adjective
  (`LINGEA_LANGUAGES` in `language_preferences_default.py`: the 36 dictionaries into Serbian,
  `englesko`, `nemacko`, `rusko`, ...; `zh`, `zh-CN`, `zh-TW` → `kinesko`). A user language
  outside that map gives the Site article's error event ("Lingea has no Georgian–Serbian
  dictionary") instead of a link (`_site_link` in `lexical_views.py`). The placeholder is in the
  editor hint; the predefined URL and the default article use it
- The rule (`add_language_pair_articles`): a Serbian book gets the Lingea article after Glosbe
  for any user language in `LINGEA_LANGUAGES`. Applied when preferences are created (the default
  Serbian ones, only once the user has a language, and copies), and at the user's first language
  choice in the user modal, because preferences created before the user had a language got
  English as a placeholder. Copies to other languages skip the Lingea article
- The inline translation cannot be a Site: `save_inline_translation` rejects it ("A Site cannot
  be the inline translation"), because the popup has no URL handling and `translate()` failed
  with a KeyError on the Site link
- Wiktionary history text drops leading Russian-edition usage labels (`экон.`, `с.-х.`,
  `поэт., перен.`; a label before `от` stays: `сокр. от ...`): 27,473 of 163,000 Russian-edition
  first senses in the real data. The HTML sense list keeps them
- `httpx` is listed in `requirements.in` and `requirements.koyeb.in`; `deep-translator` is gone
  from both and from the compiled files (recompiled without `--upgrade`: no other version moved)

## Phase 5 — Tests, spec, docs, verification

- [x] Playwright (`tests/e2e_playwright/`): the popup shows the LLM translation (fake pool); the
  Wiktionary sense list with attribution (fixture data); the error alert after the 3 s timeout (fake
  pool that stalls); Google alternatives (mocked endpoint)
- [x] `specs/inline-translation.md` (decisions and business rules only): the three options and why,
  default, no fallback and the 3 s limit, Wiktionary source, licence and attribution, Lingea for
  Serbian next to Glosbe, the measurements
- [x] Docs: `docs/src/{en,ru}` (the translators, the Wiktionary import command), README, `CLAUDE.md`
- [x] Verification: `invoke pre`, `python -m pytest tests`, `npm test`, `invoke buildjs` (never
  `invoke test` / `invoke selenium` from sessions: they open browser tabs)
- [x] Manual, in the browser on the local server: import the real Wiktionary data; click words in
  English, German and Serbian (both scripts) books with each option; the popup timing; the error
  after a stalled pool

Done notes (2026-09-25):

- `tests/e2e_playwright/test_playwright_inline_popup.py` runs the real translators behind the
  popup (it overrides the conftest's autouse fake translator): the default LLM translation over
  a fake pool (prompt carries the marked passage), the busy alert when the fake pool stalls
  (arrives between 3.0 s and 5.5 s after the click), the Wiktionary sense list with its
  attribution built from the fixture JSONL, the attribution still in view under a 40-sense
  list, and Google alternatives through `httpx.MockTransport` swapped into the registry. The
  module has its own book: the reader caches page HTML by book code, so rewriting the shared
  book's page showed the other tests' text in the full run
- Fixed on the way: the Wiktionary popup centred its sense text away from the list numbers and
  scrolled the attribution out of view with the senses. The entries now sit in their own
  scroll box, left-aligned, with the attribution below it
- Manual check on a scratch server (port 8917, scratch database, the repo's real
  `wiktionary.sqlite3` from Phase 2, real pool and real Google), headless Chromium, 21 words in
  four books (English, German, Serbian Latin and Cyrillic) per option. Sense right as the
  answer / listed: LLM translation 20 / 21 (misses the idiom `reinen Wein eingeschenkt`),
  click to answer 0.89 / 1.24 s p50 / p90, max 2.30 s; Wiktionary 16 / 21 listed (no entry for
  `pevala`, no `aufstehen` from `steht`, no `make out` from `make`), 0.19 s; Google 9 / 21 as
  the translation, 13 / 21 listed, 0.28 / 0.89 s. The sidebar Wiktionary article works in all
  three languages; the Serbian preferences of a Russian reader got the lingea tab (English and
  German did not), and `Кључ` opened `https://recnici.lingea.rs/rusko-srpski/Klju%C4%8D`
  (HTTP 200, "ключ"). The 3 s stall was checked by the Playwright test, not the real pool

## Phase 6 — Online Wiktionary (replaces the offline data)

The offline file, its importer and every manual step go. The lookup code of Phase 2 (pruning of a
kaikki record, entry building, ranking, HTML rendering, attribution, history summary) stays and is fed
by per-word pages instead of SQLite rows. The research prototype is `scratchpad/hybrid/hybrid.py` and
`kaikki.py` (URL building, fetching); its recorded pages are in `scratchpad/hybrid/cache/`.

- [x] **Remove the offline path:** the `import-wiktionary` command, the download/build/atomic-swap
  code, the `WIKTIONARY_DATABASE` setting (base and test settings), the `.gitignore`/`.dockerignore`
  entries, the "not installed" error kind and its alert text, the import docs (`docs/src/{en,ru}`
  aimodels/docker, README, CLAUDE.md), the import tests, and the local `wiktionary.sqlite3` (a
  generated 227 MB file, gitignored; delete it at the end). Keep the pruning function that turns a
  kaikki JSON record into entry/senses/links, moved next to the lookup
- [x] **Lemma:** `simplemma` in `requirements.in` and `requirements.koyeb.in` (recompile without
  `--upgrade`, as Phase 4). Languages `en`, `de`, `hbs`; loaded lazily per language. Serbian: lemmatise
  the Latin transliteration (simplemma knows more Latin forms: `protiče` → `proticati`, `протиче`
  unchanged), with Wiktionary's pitch accents stripped first (`kȍsu` → `kosu`, also for the page
  URLs). German keeps its case; English and Serbian clicks are lowercased before lemmatising. A
  lowercase click whose lemma differs from it only in case looks up the lowercase word (`robin`,
  not simplemma's `Robin`); a capitalised click keeps simplemma's spelling (`I`, `I'm`). The
  click's place in its sentence comes from `Term.passage` (the word marked ⟦ ⟧), which
  `WiktionaryTranslator` passes to `lookup(..., passage)`: `sentence_start()` is True when the
  text before ⟦ is empty or ends in `.`, `!`, `?`, `…` or `:` plus optional quotes/dashes
  (`SENTENCE_START`), False otherwise, None without a mark (then English/Serbian behave as at a
  sentence start, German as mid-sentence). Both the popup and the sidebar pass the passage. Only the
  book languages that have kaikki data (en, de, sr/hr/bs via Serbo-Croatian); other book languages
  raise the unsupported-language translator error as today
- [x] **URLs:** English edition `https://kaikki.org/dictionary/<Language>/meaning/<c1>/<c1c2>/<word>.jsonl`
  (`English`, `German`, `Serbo-Croatian`); Russian edition
  `https://kaikki.org/ruwiktionary/<Language>/meaning/<c1>/<c1c2>/<word>.jsonl` (`Английский`,
  `Немецкий`, `Сербский`, percent-encoded). `<c1>`/`<c1c2>` are the first one/two characters after
  escaping; a one-letter word repeats itself (`a/a/a.jsonl`, `I/I/I.jsonl`); escaping `.` → `_dot_`,
  `/` → `_slash_`; spaces, apostrophes and non-ASCII letters are only percent-encoded. Page names are
  case-sensitive. Serbian: the Latin page in the English edition, the Cyrillic page in the Russian
  edition (the Russian edition's Cyrillic pages are fuller). A Croatian book (`hr`) uses the
  Russian edition's `Хорватский` section with the Latin page (`CROATIAN` section key in
  `EDITION_LANGUAGE_NAMES`, `page_word`; `_Pages.section`); Bosnian stays on `Сербский`. The
  prototype's `kaikki.py` has the verified builder
- [x] **First round:** the clicked form and its lemma (deduplicated), each from both editions, in
  parallel (at most 4 requests). The Russian edition only for a Russian reader (as the offline code);
  for a Russian reader its entries come first. English-edition translations are filtered by the user
  language at lookup (any user language; Serbian/Croatian/Bosnian users → `sh`, as Phase 2's fix)
- [x] **Follow-up round:** only when the lemmatiser returns the word unchanged and the word's own
  English-edition page links to a lemma: follow `form_of` links under any tag except `dialectal`,
  `initialism`, `acronym`, `misspelling`; follow `alt_of` links only for contractions. At most 3
  targets, both editions, in parallel (4 % of real clicks). Show the word's own senses, then its
  "form of" line, then the lemma's entries. Checks: I'm, you're, 'tis (selected across the
  apostrophe; a single click sends one side of it), liveth, wouldst, Curiouser reach an entry; "she" and "be" lead with their own entries; a sentence-initial "Still" leads with
  the adverb, not a surname
- [x] **HTTP:** one `httpx.Client` per process, HTTP/1.1 keep-alive kept 60 s
  (`httpx.Limits(keepalive_expiry=60)`; httpx's default 5 s closed it between clicks);
  requests of a round in
  parallel; about 2 s per request and the whole click within the popup's 3 s limit; a User-Agent
  naming lexiflux and its repository URL
- [x] **Cache:** the pruned record per page URL, 404s included (18 % of requests, repeated for
  inflected forms), kept 30 days, in the existing database-backed cache (as the LLM translation's
  answers). Never cache timeouts, connection errors, 5xx or 429
- [x] **Popup outcomes:** entries → the sense list with attribution; every page 404 → the "no
  translation" alert; kaikki.org unreachable (timeout, connection error, 5xx, 429) and no entries →
  the translator network-error alert worded "Wiktionary (kaikki.org) is not reachable"; one edition
  failing while the other has entries → show those entries, cache nothing for the failed page
- [x] **Tests:** `httpx.MockTransport` serving recorded pages (copy the needed ones from
  `scratchpad/hybrid/cache/` into `tests/resources/wiktionary/`, replacing the dump fixtures):
  lemma from inflected forms (en, de, sr both scripts), URL escaping cases, both editions and their
  order, the follow-up round cases above, 404 caching, no caching of failures, one edition failing,
  all failing, attribution present, history summary. An opt-in real-network smoke test (marker like
  `real_llm`, e.g. `real_net`) fetching "be" from both editions, because a changed layout would
  otherwise look like "no entry" everywhere. Playwright: the Wiktionary popup over the mocked pages
- [x] **Spec and docs:** `specs/inline-translation.md` (Wiktionary is online: lemmatiser + kaikki.org,
  nothing installed, Russian edition first for a Russian reader, outcomes, the measurements of the
  online study), `docs/src/{en,ru}`, README, CLAUDE.md: no import command anywhere
- [x] **Verification:** the Phase 5 gate (`invoke pre`, `python -m pytest tests`, Playwright,
  `npm test`, `invoke buildjs`); the process's memory with the German lemmatiser loaded, reported
  (Koyeb free instance is 512 MB); a headless-browser check on a scratch server with the real
  network: English, German, Serbian (both scripts) words through the Wiktionary popup and the
  sidebar Dictionary article, timings reported

Done notes (2026-09-26):

- The cache is a new table (`WiktionaryPage`, migration 0024), keyed by page URL and the
  Wiktionary code of the user language: lexiflux had no database-backed cache (the LLM
  translation's answers live in an in-process LRU, `CACHES` is LocMem), and English-edition pages
  are pruned to the user language's translations. Rows older than 30 days are ignored on read and
  deleted on the next write. A 200 answer without JSON lines counts as a failure, not a missing
  word, and is not cached
- simplemma runs with `low_memory=True`: identical lemmas on 140,000 dictionary words (plus
  20,000 unknown and 20,000 capitalised) per language, 12–15 µs a word instead of 1.4–2.0 µs.
  App process (all modules imported) 148 MiB; + English 3, + German 26, + Serbo-Croatian 8 →
  186 MiB (without it +30 / +141 / +37 → 357 MiB). Load 0.11 / 0.53 / 0.26 s at the first word
- The follow-up rule is the prototype's: `form_of` links skipped under `dialectal`, `initialism`,
  `acronym` and the pruning's noise tags (`misspelling`, `pronunciation-spelling`,
  `eye-dialect`); an `abbreviation` sense is followed only when it is a contraction
- Added: a name round. When every first-round page is missing or empty and the lookup
  lowercased the clicked text (English, Serbian), the page of the text as written is fetched
  ("London" → Лондон). It runs only when the lowercase lookup found nothing, so no measured
  result changes
- Names: a name reached through the lemma or a link (mostly a surname, "august" → "August")
  is shown only when nothing else is found. When ranking leaves nothing, the same first-round
  pages are ranked again with those names allowed, before the name round: "Beogradu" →
  Beograd "Belgrade", "Evrope" → Evropa "Europe", "Deutschlands" → Deutschland "Germany"
- German capitals: in mid-sentence (and without a passage) a capitalised German click that finds
  no entries, or only names, looks up the lowercase spelling (and its lemma) in one more round
  and those entries come first ("Schön" → schön); capitalised nouns ("Schloss", "Bank", "Gut")
  find their own entries and make no extra request. At a sentence start: when the lemmatiser's
  words include a lowercase one, `wanted` is the lowercase spelling and it leads, ranking only
  ("Ich" → ich, "Aber", "Nichts", "Es", "Wenn"); when every entry is capitalised, the lowercase
  round runs (words already fetched are skipped) and leads ("Gut, dass …" → gut), unless no
  lowercase entry is the lowercase word itself, i.e. it is only a form of another lemma: then
  the lowercase entries follow ("Schloss" at a sentence start → Schloss, then schließen)
- English and Serbian capitals in mid-sentence: the typed spelling joins the first round as its
  own candidate (`written`; its names are kept like candidate 0's), unless the lemmatiser's
  words already have that page. It leads (`wanted = typed`) for Serbian always, and for English
  when its English-edition entries have translations into the user language (`_translated`):
  "China" → Китай, "May" → май, "March" → март, "Turkey" → Турция. Otherwise it follows the
  lowercase entries: "the King" → король, then King (a surname), and likewise Queen, Rabbit,
  Hatter, Duchess, Cat, Mouse in Alice, whose as-written pages are surnames, places or the
  Chinese zodiac. The name round is skipped when the typed spelling was already fetched
- Link following compares spellings the way the first round deduplicates them: exactly for
  German (so "Tanzen" follows its link to "tanzen"), case- and accent-insensitively otherwise
- Regression checks (recorded pages in the fixture, and on the real network): robin (the bird;
  Robin the name), august (the adjective), Beogradu, Evrope, Deutschlands, Tanzen, Gehen, kȍsu,
  Schön; unchanged: Schloss, Bank, Gut. A kaikki record of an unexpected shape fails only its
  page (not cached; the round's good pages are kept and cached); futures still queued at the
  deadline are cancelled. Re-measured after these fixes on the real network (644 requests,
  555 × 200, 89 × 404): bench 21 / 24 and 19 / 24, inflected 42 / 45, Alice 200 / 200,
  contractions 20 / 20; the only changed output is "Haken", which now also follows its
  gerund link to "haken" after its noun entries. Gate: `python -m pytest tests` 903 passed /
  20 skipped, Playwright 20 passed / 1 skipped, `-m real_net` 1 passed
- User languages whose Google code differs from Wiktionary's: a Norwegian reader (`no`) gets the
  `no`, `nb` and `nn` translations, a Filipino reader (`fil`) the `fil` and `tl` ones, a Chinese
  reader (`zh-CN`, `zh-TW` → `zh`) the `zh` and `cmn` ones (most Mandarin translations are filed
  as `cmn`: 215 of 314 entries with Chinese in the recorded pages had only `cmn`), a Kurdish
  reader (`ku`, Kurmanji) the `ku` and `kmr` ones (`TRANSLATION_CODES`, applied where
  English-edition translations are filtered; the cache key stays the reader's code)
- The deadline (2.8 s, the rest of the popup's 3 s) starts before lemmatisation; each request
  gets `min(2 s, time left)`; futures not done at the deadline count as failed and their late
  answers are dropped. The network alert reads "{label} is not reachable." for every translator
  (Google's says "Google is not reachable." now); `TranslatorError.service` names kaikki.org
- Tests: `tests/kaikki.py` serves 122 recorded pages (`tests/resources/wiktionary/
  kaikki_pages.jsonl`, trimmed to word, pos, senses' glosses/tags/links and ru/de/sh
  translations, plus nb/nn/tl/kmr on `spring` and cmn on `king`; 160 KB); `springs`, `London`,
  the regression checks' pages and the sentence-position and Croatian pages were recorded
  fresh. An autouse fixture
  refuses real kaikki.org requests; `tests/test_wiktionary_real_net.py` (`-m real_net`,
  `LEXIFLUX_REAL_NET=1`) fetches "be" from both editions
- Reproduction of the study through the real code (2026-09-26): on the recorded pages, output
  identical to the prototype for all 293 inputs and 20 contractions; on the real network, again
  identical (642 requests, 553 × 200, 89 × 404, no failure): bench 21 / 24 (dictionary form),
  19 / 24 (clicked text), inflected 42 / 45 listed, Alice 200 / 200 word or lemma first,
  contractions 20 / 20. Latency, 109 clicks with nothing cached, one kept-alive client: p50
  0.130 s, p90 0.212 s, max 0.726 s (prototype 0.128 / 0.259 / 0.986)
- Headless Chromium on a scratch server, real kaikki.org, Russian reader, 26 words in four
  books (English, German, Serbian Latin and Cyrillic): every word got entries. Click to popup:
  first word of a language 0.78 s (English), 0.83 s (German), 0.52 s (Serbian), others 0.19–0.38
  s, cached 0.19 s (0.15 s of it is the view itself). Sidebar Wiktionary article in all four books
  0.83 s. Server RSS 150 MiB at start, 204 MiB with all three lemmatisers loaded
- Gate: `invoke pre` clean (pyrefly 0 errors), `python -m pytest tests` 887 passed / 20 skipped,
  Playwright 20 passed / 1 skipped, `npm test` 107 passed, `-m real_net` 1 passed. The repo's
  `wiktionary.sqlite3` is deleted
- Review round 3 (2026-09-26): Chinese and Kurdish translation codes, keep-alive 60 s, sentence
  position, the Russian edition's Croatian section (all above); the timeout test now checks the
  timeout each request carries (≤ 2 s; the client has no default of its own). Checks on the
  recorded pages (tests) and the real network: "China", "May", "March", "Turkey" in
  mid-sentence lead with Китай, май, март, Турция; at a sentence start (and without a passage)
  they stay china, may, march; "the King" → король, then King. German at a sentence start:
  "Ich" → я, "Aber" → но, "Nichts" → ничего, "Es" → оно, "Wenn" → когда (no extra request),
  "Gut, dass" → хороший (one more round), "Schloss" at a sentence start → замок, then
  schließen; in mid-sentence "das Ich", "das Gut", "das Schloss" are unchanged and make no
  extra request. Croatian "mlijeko" → молоко (`Хорватский`); 13 of 16 common Croatian words
  have a `Хорватский` page, 7 a `Сербский` one. Harness rerun on the real network with the
  new code (no passage, as before; 644 requests, 555 × 200, 89 × 404, no failure): output
  identical to the previous real run, bench 21 / 24 and 19 / 24, inflected 42 / 45, Alice
  200 / 200, contractions 20 / 20. With realistic passages (bench passages, the inflected forms
  in their source sentences, Alice's words at their first occurrence): the same counts, and
  the only changed output is Kafka's sentence-initial "Seine", which now leads with sein
  (lemma first 42 / 45 instead of 41). Alice's 40 most frequent mid-sentence capitals
  (1,158 occurrences): letting every as-written page lead would have put a surname, a place or
  a letter-case variant first for 19 of them (542 occurrences, e.g. Queen, King, Turtle, Mock,
  Hatter, Rabbit, Duchess) and a surname into the vocabulary summary for 232; with the
  translation rule only translated names lead (March, English, Bill, William, Dinah,
  Cheshire, Majesty). Latency (real network, nothing cached, lexiflux's client): back to back
  0.08 s p50 / 0.21 s p90, 20 s apart 0.13 / 0.22 s (15 clicks each; with the old 5 s expiry a
  click after 10 s idle took 0.27 s); first word of a language in a fresh process 0.40 s
  (English), 0.49 s (Serbian), 0.76 s (German)

## Phase 7 — Saved sense from context; sentence starts from the book's structure

Why: four review rounds on Phase 6 each found another entry-order edge (case, names, sentence
position), and each one mattered because the vocabulary history saved the first sense of a
context-free dictionary. On Alice's 200 most frequent words at least 12 saved a wrong sense (see →
престол, felt → войлок, might → мощь, even → чётный; about 635 occurrences). The acceptance measure
("the first entry is the word or its lemma") could not see it. Review: `scratchpad/reviews/review-v2-4.md`.

- [x] **History from LLM translation in context** (the Decisions row "Vocabulary history"): in the
  `translate` view, when the popup's translator is Wiktionary or Google, start the LLM translation of
  the same term and passage (the existing inline LLM path and its cache, free pool, the 3 s limit) in
  the background after the popup's answer is ready; do not delay the popup response. When it succeeds,
  write its answer into the history entry. Record whether an entry's translation came from the LLM
  (an auto-generated schema migration is fine; single user, no data migration). A new entry gets the
  translator's first line until then; an entry that already has an LLM translation keeps it while the
  new one runs; a failed or timed-out LLM call changes nothing and is retried on the word's next
  lookup. With LLM translation as the popup, behaviour is unchanged (its answer is saved and marked as
  LLM). Background work closes its DB connection; tests run it synchronously (a setting or an
  injectable runner), never with real threads racing the test DB
- [x] **Sentence starts from the book's structure:** the marked passage keeps a line break where a
  block element (heading, paragraph, list item, table cell, `<br>`) ended, so a heading never joins
  the next sentence; `sentence_start` treats a line break as a sentence end; `,` or `;` followed by an
  opening quote (`“ „ « ‹ › ‘ " '`) starts a sentence (dialogue: `He asked, “Will you come?”`); the
  English abbreviations Mr., Mrs., Ms., Dr., St. and the German z. B., d. h., Hr., Fr., Dr. do not end
  a sentence. The LLM prompt keeps working with the line breaks (check the passage it receives)
- [x] **Positional regression set** in the fixture tests (recorded pages): dialogue after a comma
  ("Will", "May"), the first word after an English heading ("A" in Alice ch. VIII) and after a German
  heading ("Ich", "Es"), "Mr. Bennet", "Mrs. May", mid-sentence "China", sentence-start "Gut, dass",
  nested German quotes ‹ ›; plus a test that the sidebar Dictionary article passes the passage
- [x] **Cheap cleanups from the last review:** drop Russian-edition senses that are only "вариант X"
  pointers (as the English edition's `alt_of` pruning); NFC-normalise the clicked text before building
  page URLs; pin `keepalive_expiry` in a test and restore httpx's default connection caps if the
  change dropped them; fix the spec's click-count sentence and the "now leads" wording
- [x] **Measures renamed and a real one added:** the spec and plan call the Alice check what it is
  ("the first entry is the word or its lemma", 200/200). New measure: the saved history translation
  for 50 Alice words in their first occurrence's passage (the 12 known wrong ones plus 38 others from
  the top 200), judged by hand for fitting the book's sense, before (first sense of Wiktionary) and
  after (LLM in context, real free pool). Keep the judgments in `scratchpad/p7/` and report the counts
  broken down by which pool model answered; state the result in the spec
- [x] **Spec and docs:** `specs/inline-translation.md` (the vocabulary-history rule, sentence starts,
  the renamed and the new measure), `docs/src/{en,ru}` where the history or Anki export is described
- [x] **Verification:** the Phase 5 gate; rerun the `p6/` harness (no drops: bench 21/24 and 19/24,
  inflected 42/45, lemma-first 200/200, contractions 20/20); a headless-browser check on a scratch
  server: with Wiktionary as the popup, click a few words and confirm the history rows end up with the
  LLM translation (and that the popup did not wait for it)

Done notes (2026-09-26):

- History: `TranslationHistory.translation_from_llm` (migration 0025). In `translate`,
  `_remember` writes the entry (get_or_create, one save); `_is_dictionary` (Wiktionary, Google)
  decides whether `_history_from_llm` runs through `in_background`: a daemon thread per lookup
  that calls `ask_inline_translation` (the popup's LLM path without the alert mapping of
  `translate_inline`: its cache and its 3 s limit), writes the first line of a non-empty answer
  and closes its DB connection. A pool failure in `POOL_UNAVAILABLE_ERRORS` (no keys, busy, rate
  limit, timeout) logs one warning line "History translation of 'word' failed: <error>"; any
  other exception logs the same message with its traceback. The view skips the background call
  when `_translated_in` holds: the entry's translation is from the LLM and its `context` equals
  this lookup's history context (the user language was checked by `_remember`), so a re-lookup
  in the same passage asks nothing after a restart. To keep that pairing true, a kept LLM
  translation also keeps the entry's `context` and `book`; the background write sets them with
  the new translation. Setting
  `HISTORY_TRANSLATION_IN_BACKGROUND` (True in `environments/base.py`, False in
  `tests/django_settings.py`, so tests and the Playwright live server run it inline). Two rules
  beyond the item: an LLM translation is kept only while the entry's user language is unchanged
  (after a user-language switch the dictionary line replaces it until the new LLM answer), and
  the background write applies only while the entry's `last_lookup` is the one of its lookup,
  so a late answer for an earlier passage never replaces a later lookup's. An AI article as the
  popup saves its answer as before (not marked LLM, no background call)
- Line breaks: `text_with_line_breaks` in `term_context.py` builds the marked passage. The
  source's own whitespace is collapsed first, then block tags (p, div, h1–h6, li, ul, ol, tr, td,
  th, table, blockquote, section, article, pre, hr) and runs of two or more `<br>` become a line
  break. A single `<br>` stays a space: the plain-text importer turns every line of the file
  into `<br/>`, so in Gutenberg texts it is a wrapped line (Alice: 232 capitals in mid-sentence
  start a wrapped line and would have counted as sentence starts). `TermContext.sentence` (the
  AI articles' context) and the history context are unchanged
- `SENTENCE_START`: a line break is a sentence end; `‹ ›` added to the quote class; `, ` or `; `
  plus an opening quote (`“ „ « » ‹ › ‘ ‚ " '`) that touches the word starts a sentence. The
  quote must touch the word so that a straight closing quote is not read as opening
  (`"Come," Tom said` stays mid-sentence). `»` and `‚` are added to the item's list (German
  `sagte er, »Ich …`, nested `‚…‘`). `ABBREVIATION` (Mr, Mrs, Ms, Dr, St, Hr, Fr, z. B./z.B.,
  d. h.) applies to every book language, and a line break after one still ends the sentence
- Regression set (`test_the_words_place_in_the_book_decides_what_leads`, through a real
  `BookPage` and `term_context`): Will → will, May → may (dialogue), A → a article (Alice
  ch. VIII as plain text and as HTML), Ich → ich, Es → es (German headings), Mr. Bennet →
  bennet then Bennet, Mrs. May → May (май, the mid-sentence name rule), China → Китай, Gut, dass
  → gut, nested › Ich → ich; for English it also checks that the as-written page is fetched
  exactly in mid-sentence. With the Phase 6 rules on the same pages, 8 of the 11 led with
  another entry (Will: "английская фамилия", May: май, A: "Т" twice, Ich: "das Ich" twice, Es:
  the note E-flat, Mrs. May: the modal verb) and Mr. Bennet lacked the surname. New recorded pages: a, A, Will, Bennet, bennet (both
  editions, 404s not stored). `test_sidebar_article_reads_the_words_place_in_its_sentence`
- Cleanups: `RUSSIAN_VARIANT_OF` drops Russian-edition senses "вариант X" (also after a usage
  label: "устар. вариант tale"); "вариант артикля a перед гласными" and longer glosses stay.
  `_typed` NFC-normalises. `http_client` passes `max_connections=100,
  max_keepalive_connections=20` with the 60 s expiry (test on the `httpx.Limits` it builds).
  Spec: 109 clicks, the two 15-click runs named, "now leads" gone
- Measure (`scratchpad/p7/`: `measure.py`, `items.json`, `judgments.json`): Alice imported with
  `import-text`, each word's first occurrence after the table of contents, the passage from
  `term_context`. Before (Phase 6 code, Wiktionary summary) 24 / 50 fit the book's sense (0 of
  the 12 known); after (LLM translation, real pool, lexiflux's `.llmbroker`, whose
  `disabled.yml`, `model-list.toml` and presets equal echo-words') 47 / 50 (11 of 12). By model:
  Groq GPT-OSS 120B 40 / 41, Gemini 3.5 Flash Lite 7 / 9. 13 of the 47 fitting answers translate
  a phrase the word belongs to (feet → встать, at → удивиться, make → разглядеть, be → стоить,
  down and went → спуститься, look → осмотреться, getting → вставать, looking → странно
  выглядящий, out → необычно, go → пройти, even → даже если, found → оказаться); for about 10
  (all but even, go and looking) the line does not translate the word itself, and its reverse
  Anki card reads "встать → feet". Counting those as misses gives about 37 / 50, against
  Wiktionary's first sense at 24 / 50 (for feet, down, went, look and be, Wiktionary's first
  sense fit). Decision (review v3-1, P1 option 2): the behaviour stays, the spec's measure says
  so. Misses: would → "быть стоющим"
  (Gemini), the (chapter title) → "в" (Gemini), court (trial) → "двор" (Groq). At about 35
  requests a minute 46 answered within 3 s; 4 failed on the free tiers' per-minute limits (Groq
  30 RPM and tokens per minute, Gemini 429 with a 60 s cooldown) and all 4 answered on a retry
  a minute later at one request per 6 s. The Phase 7 Wiktionary summary differs from Phase 6's
  only for "heard" (слышать instead of "вариант hair")
- Harness (`scratchpad/p7/harness/`): p6 harness, recorded pages and real kaikki.org (644
  requests, 555 × 200, 89 × 404, no failure), identical output: bench 21 / 24 and 19 / 24,
  inflected 42 / 45, word or lemma first 200 / 200, contractions 20 / 20; against round 4 the
  only changes are dropped "вариант X" entries (see, bear, they, one, do, heard, …). The r4
  passage harness: the same counts, no sentence-position change on its passages
- Headless check (`scratchpad/p7/browser/`, the Phase 6 books, Russian reader, Wiktionary popup,
  real kaikki.org and real pool, 26 words fresh then cached): click to popup, Phase 6 code vs
  Phase 7, fresh p50 0.250 / 0.258 s, p90 0.373 / 0.367 s; cached p50 0.192 / 0.190 s. At popup
  time every fresh row still held Wiktionary's line (the popup did not wait); 4 s after the
  round all 26 rows held the LLM translation (saw → видел, bank → берег, make → разглядеть,
  steht → вставать; eingeschenkt → "вылить чистую воду", a literal miss of "reinen Wein
  einschenken")
- Gate: `invoke pre` clean (pyrefly 0 errors), `python -m pytest tests` 1011 passed / 20 skipped,
  Playwright 21 passed / 1 skipped (after `invoke buildjs`; TypeScript untouched, so no
  `npm test`), `-m real_net` 1 passed
- Review v3-1 fixes: the Wiktionary and Google popup tests that assert the dictionary line in the
  history make the pool fail explicitly with no keys and say so in their names (the China test
  also fails it explicitly); the Playwright
  Wiktionary and Google popup tests take `fake_pool`, so no test reaches the autouse
  `no_real_llm_calls` guard through the background call. Gate: `invoke pre` clean,
  `python -m pytest tests` 1019 passed / 20 skipped, Playwright 21 passed / 1 skipped

## Risks

- **Pool quota** is shared with the sidebar articles and, when the popup uses Wiktionary or Google,
  with the background history translation (a race of two pool models, so one request from each, per
  looked-up word in a passage without its LLM translation and not in the cache); heavy
  reading days could exhaust Gemini's about 500 requests. Then the LLM popup shows errors and new
  history entries keep the dictionary's first line until a later lookup (no popup fallback, by
  decision)
- **Google blocks identifiers** without notice; the option then shows errors
- **kaikki.org** is one volunteer-run host with no API contract; an outage or a layout change breaks the
  Wiktionary option (error alerts; cached words keep working). An unknown path answers 404 like a missing
  word, so a layout change looks like "no entry": an opt-in real-network smoke test guards it
- **Lemmatiser memory**: simplemma's low-memory mode adds about 3 MB (English), 26 MB (German), 8 MB
  (Serbian) per loaded language (its default mode 30 / 141 / 37 MB); loaded lazily per language. The app
  process measured 186 MiB with all three, Koyeb's free instance has 512 MB
- **Privacy**: every uncached Wiktionary click sends the word to kaikki.org
- **Serbian in Wiktionary** is mostly English glosses; Lingea (sidebar) covers Russian equivalents
