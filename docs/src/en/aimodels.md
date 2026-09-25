# AI Models

Lexiflux uses AI models to write the articles in the `Sidebar`
(you open it with the blue binocular icon).

The inline translation (the popup that opens in the text when you click a word) also uses AI
by default, see [Inline translation](#inline-translation).

To configure the Sidebar and inline translation see [Dictionary & AI Insights Settings](http://localhost:6100/language-preferences/).
There are separate settings for each language, so you can configure
different settings for different languages.

## Article types

### Written by AI
- **AI dictionary** (the default `Article` tab): a short dictionary article about the selected
  word or phrase, leading with the sense it has in the sentence you are reading.
- **In depth**: a longer article about the whole unit the selection belongs to (a phrasal
  verb, a separable verb, an idiom), with examples.
- **Sentence**: a translation of the whole sentence.
- **Translate**: a translation of the selection in the sense it has in the sentence.
- **Explain**: an explanation of the selection in your language, without translating it.
- **Lexical**: a full lexical article with meanings, grammar and forms tables.
- **Origin**: where the word comes from, only where the model knows it.

The AI receives two things: the selected word or phrase and the sentence it stands in.
When that sentence is very short (under six words), the sentences around it are added.

Sidebar articles appear while the AI is still writing them.

#### Custom AI
With type "AI" you can write your own prompt. It can use the placeholders `{word}`,
`{sentence}`, `{text_language}` and `{user_language}`.

### Dictionary
One of the three translators described in [Inline translation](#inline-translation):
`LLM translation`, `Wiktionary` or `Google`. In the Sidebar a Wiktionary article shows the
whole list of senses.

### Site
You define what a URL to open and with which parameters.
This is useful for a good translator that does not have an API, like glosbe.com.

The URL can use these placeholders:

- `{term}`: the selected word or phrase
- `{termLatin}`: the same, with Serbian Cyrillic written in Latin letters (for sites that
  only take Latin script)
- `{lang}`, `{langCode}`: the book language name and code
- `{toLang}`, `{toLangCode}`: your language name and code
- `{toLangLingea}`: your language as the Serbian dictionaries at recnici.lingea.rs name it
  (`englesko`, `rusko`, ...). If Lingea has no dictionary from your language, the article
  says so instead of opening a link

Most of them should be opened in an external window, but some of them can even be opened inside the Sidebar.

This is controlled by the `open in new window` parameter.

Every language gets a `glosbe` Site article. Serbian books also get `lingea` (Lingea's
dictionaries into Serbian at recnici.lingea.rs) when Lingea has a dictionary from your language:
36 languages, among them English, German and Russian. It finds the dictionary form of an
inflected Serbian word and separates words that are spelled the same.

## Inline translation

Click a word and its translation opens right in the text. In
[Dictionary & AI Insights Settings](http://localhost:6100/language-preferences/) you pick,
for each book language, which translator answers there:

| Translator | What you see | Speed |
|---|---|---|
| LLM translation (default) | One translation, in the sense the word has in the sentence you are reading. For a separable verb or a fixed expression, the whole unit | About 0.6 s, at most 3 s |
| Wiktionary | The dictionary entry: part of speech and the list of senses. For English words, translations into your language; for German and Serbian often English definitions | Instant, works offline |
| Google | Google Translate's translation, plus its alternatives by part of speech for English and German | About 0.3 s, sometimes up to a second |

On 24 test words in English, German and Serbian, translated into Russian, the LLM
translation picked the right sense for 23. Wiktionary listed it for 20 and Google for 15
(and gave it as the translation for 6).

- **LLM translation** uses the free pool (see [Models](#models) and [Keys](#keys)). It shares
  the free daily quota with the Sidebar articles. If no answer comes within 3 seconds, the popup
  says the models are busy; click again to retry.
- **Wiktionary** needs its data imported once, see below. It works for books in English,
  German and Serbian (and Croatian, Bosnian). It finds the dictionary form of an inflected word
  and Serbian words in both scripts. Every answer links to the Wiktionary page and its licence,
  CC BY-SA 4.0.
- **Google** translates the word without its sentence, so for a word with several meanings it
  may pick the wrong one. Google may stop answering without notice.

If the chosen translator fails, the popup shows what went wrong. It never switches to another
translator on its own.

### Wiktionary data

The Wiktionary data is not included in Lexiflux. Import it once with the `import-wiktionary`
command; later run it again (for example monthly) to get fresher data.

- **Running from source**: `./manage import-wiktionary` in the Lexiflux folder.
- **Docker**: `docker exec -it lexiflux ./manage import-wiktionary`.

The command downloads about 3.2 GB from [kaikki.org](https://kaikki.org/) (the English and
Russian Wiktionary), builds a dictionary file of about 230 MB next to the database, and
deletes the downloads. It takes about three minutes on a fast connection and needs about
3.5 GB of free disk space while it runs. An interrupted download continues where it stopped.
Readers keep using the old dictionary until the new one is ready.

- `--keep-downloads` keeps the downloaded files, so the next import skips the download if
  kaikki.org has nothing newer.
- `--translations ru,de`: the languages to keep translations of English words for. By default,
  Russian plus every "your language" in the Language Preferences.

## Models

Every AI article picks one of these models:

| Model | Cost | What to expect |
|---|---|---|
| Free pool | free | Several free-tier models; Lexiflux asks two at once and shows the faster answer. Text usually starts in about a second. Used by the default `Article` |
| GPT-5.6 Sol | about $0.035 per In depth article | The best quality for the price and fast: text starts in under a second. The default for every other AI article |
| GPT-5.6 Luna | about $0.003 per In depth article | Ten times cheaper than Sol, but slower to start and with more mistakes |
| Claude Opus | about $0.06 per In depth article | The most accurate, but text starts only after 15–30 seconds |

The numbers were measured on 24 words in English, German and Serbian.

### Reasoning effort and processing tier

For the paid models the article editor shows two more settings:

- **Reasoning effort**: how long the model thinks before it writes. The defaults are the
  settings that measured best on dictionary articles: `none` for Sol, `low` for Luna and Opus.
- **Processing tier** (OpenAI only): `priority` costs about twice as much and answers about
  three times faster. Sol and Luna default to it.

`Model default` sends nothing and lets the provider decide.

## Keys

You do not enter API keys in Lexiflux. Whoever runs Lexiflux puts the keys in its
environment, and every user of that Lexiflux uses them.

- **Free pool**: needs at least one of `GROQ_API_KEY`, `GEMINI_API_KEY`, `ZAI_API_KEY`.
  Each is a free key; more keys make the pool faster and more reliable. Lexiflux does not use
  `OPENROUTER_API_KEY`: the pool leaves out the OpenRouter models because with them more
  Articles ended in "busy". `llmbroker env freetier` prints the keys with a link to get each one (it
  also lists OpenRouter).
- **GPT-5.6 Sol and Luna**: `OPENAI_API_KEY` (paid).
- **Claude Opus**: `ANTHROPIC_API_KEY` (paid).

Where the keys go:

- **Running from source**: in a `.env` file in the Lexiflux folder, or in the environment.
- **Docker**: pass them to `docker run`, see [Docker](docker.md#ai-keys).
- **A hosted server**: in the server's environment variables (secrets).

If a key is missing, the article says which key it needs and where to get it.
