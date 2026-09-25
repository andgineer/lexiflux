# Inline popup: LLM translation by default, offline Wiktionary, Google via its JSON endpoint

## Overview

The inline popup (a click on a word) currently asks `deep_translator`'s GoogleTranslator. It
scrapes `translate.google.com/m`, which Google now redirects to its "sorry" page, and it translates
the bare word, so it guesses the sense (6 of 24 bench items right). This plan replaces the popup's
translators:

- **LLM translation (default):** the free llmbroker pool translates the selected word in its
  passage and returns only the Russian (user-language) equivalent. 23 of 24 bench senses right,
  answer in about 0.6 s p50, 0.8 s p90
- **Wiktionary:** an offline dictionary built from the kaikki.org Wiktionary extracts: senses with
  user-language equivalents (English words) or English glosses (German, Serbian), lemma lookup for
  inflected forms, both Serbian scripts. 20 of 24 bench senses listed, lookup in microseconds, no
  network, no keys
- **Google:** the same Google engine through its JSON endpoint `translate.googleapis.com`, with
  dictionary alternatives for English and German. Fast (0.07 s) but context-blind and fragile
  (Google blocks client identifiers without notice)

MyMemory, Linguee, PONS and the `deep-translator` package go. For Serbian books read by a Russian
speaker, the sidebar gains a Lingea Site article next to Glosbe.

Evidence: the translator study (`scratchpad/translator/`, summarised below) and the dictionary
study (`scratchpad/dictionary/`), both 2026-09-24, on the 24 items of `experiments/context_bench.py`.

## Decisions

| Topic | Decision |
|---|---|
| Popup options | Three: LLM translation (default), Wiktionary, Google. The user picks one in Language Preferences; the choice is per language as today |
| No fallback | A popup translator never falls back to another one. If the LLM translation fails or has no answer after **3 s**, the popup shows an error alert (the existing alert style); same for Google and a missing Wiktionary entry |
| LLM translation | Free pool only (`fastest_of=2`), context = the selected word marked inside a short passage (its sentence plus the neighbouring sentences), reply = only the user-language equivalent in dictionary form; the whole unit for separable verbs and fixed expressions. Non-streaming (the popup shows the finished answer). Cached per (word, passage, languages) like the article cache. Failures are not cached |
| Wiktionary data | kaikki.org JSONL extracts, English edition (English, German, Serbo-Croatian) and Russian edition (English, German, Serbian), pruned by a management command into a separate SQLite file next to the app database (not in `db.sqlite3`), rebuilt on demand (about monthly). Licence CC BY-SA 4.0 + GFDL: every Wiktionary result shows "from Wiktionary, CC BY-SA 4.0" with a link |
| Wiktionary output | A compact list of senses: part of speech, user-language equivalents where the data has them, otherwise English glosses; the entry for the lemma of the clicked form. Russian-edition data first where an entry exists there |
| Missing Wiktionary data | The option stays selectable; the popup shows "Wiktionary data is not installed" with the import command |
| Google client | Direct HTTP to the JSON endpoint with client identifiers tried in order `dict-chrome-ex`, `gtx`, `at`; `dt=bd` alternatives shown when present (English, German); a short timeout; the existing translator error alerts on failure |
| Removed | `deep-translator` (MyMemory, Linguee, PONS, its Google scraper) |
| Defaults | Inline translation = LLM translation for new users. Single user, no existing data to migrate: the author recreates his DB (`invoke init-db`) |
| Serbian Site link | Glosbe stays the default Site article for every language (its real-world example sentences are the point). When language preferences are created for Serbian with Russian as the user language, a second Site article, Lingea (`https://recnici.lingea.rs/rusko-srpski/{term}`, Latin script: Cyrillic terms are transliterated), is added after Glosbe: it resolves inflected Serbian forms and separates homonyms, which Glosbe's page does not |

### Measurements behind the decisions (2026-09-24, 24 items, en/de/sr → ru)

| Option | Right sense | Latency | Notes |
|---|---|---|---|
| LLM pool, word in its passage | 23 / 24 (sense chosen) | 0.63 / 0.81 s (p50 / p90) | quota: Groq about 1,000 requests a day, Gemini about 500, shared with the sidebar articles |
| Wiktionary (both editions) | 20 / 24 listed | offline | Russian for English words; English glosses for many German and Serbian senses |
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

## Risks

- **Pool quota** is shared with the sidebar articles; heavy reading days could exhaust Gemini's
  about 500 requests. Then the popup shows errors until the next day (no fallback, by decision)
- **Google blocks identifiers** without notice; the option then shows errors
- **Wiktionary size**: the English-edition extract is 3 GB to download; the pruned file size is
  measured in Phase 2. Docker: the data is not in the image; the command runs inside the container
- **Serbian in Wiktionary** is mostly English glosses; Lingea (sidebar) covers Russian equivalents
