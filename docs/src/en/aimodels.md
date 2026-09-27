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
`LLM translation`, `Wiktionary` or `Google`. A Wiktionary article shows each dictionary entry
with up to 12 senses, in the Sidebar as in the popup.

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
| Wiktionary | The dictionary entry: part of speech and the list of senses. For English words, translations into your language; for German and Serbian often English definitions | About 0.1 s, up to about 0.2 s, also when you click words 20 seconds apart. After more than a minute without a lookup, about 0.3–0.45 s. The first word of each language after Lexiflux starts takes about 0.4 s (English), 0.5 s (Serbian) or 0.8 s (German), while the data for finding dictionary forms loads |
| Google | Google Translate's translation, plus its alternatives by part of speech for English and German | About 0.3 s, sometimes up to a second |

On 24 test words in English, German and Serbian, translated into Russian, the LLM
translation picked the right sense for 23. Wiktionary listed it for 19 from the word as clicked
(21 from the dictionary form: it cannot tell that "steht ... auf" means "aufstehen"), and Google
for 15 (and gave it as the translation for 6).

- **LLM translation** uses the free pool (see [Models](#models) and [Keys](#keys)). Every
  translation asks two of its models at once and takes the faster answer, so it uses one request
  from the daily quota of each; the Sidebar articles share that quota. If no answer comes within
  3 seconds, the popup says the models are busy; click again to retry.
- **Wiktionary** looks the word up on [kaikki.org](https://kaikki.org/), which publishes the
  English and the Russian Wiktionary as data. There is nothing to install, but it needs the
  internet, and every word you look up for the first time is sent to kaikki.org. It works for
  books in English, German and Serbian (and Croatian, Bosnian). It finds the dictionary form of
  an inflected word ("made" → "make"), contractions and old forms ("I'm", "liveth"), and Serbian
  words in both scripts. Select a contraction across its apostrophe: a single click takes only
  one side of it ("don" of "don't"). A Russian reader gets the Russian Wiktionary first. Words
  you looked up in the last 30 days answer even when kaikki.org is down; otherwise the popup says
  kaikki.org is not reachable. Every answer links to the Wiktionary page and its licence,
  CC BY-SA 4.0.
- **Google** translates the word without its sentence, so for a word with several meanings it
  may pick the wrong one. Google may stop answering without notice.

If the chosen translator fails, the popup shows what went wrong. It never switches to another
translator on its own.

Every word you look up goes to your vocabulary (the words export and Anki) with one
translation: the LLM translation of the word in the sentence you read it in, whatever
translator the popup uses. A dictionary cannot tell which of its senses the text means, and
its first sense is often not the one ("see" in "just in time to see it" is not "престол").
With Wiktionary or Google, the popup shows their answer at once and the LLM translation is
asked right after, without making the popup wait; until it arrives, or if the free pool is
busy, the vocabulary keeps the dictionary's first line and asks again the next time you look
the word up. Without free-pool keys (see [Keys](#keys)), the vocabulary keeps the dictionary's
(or Google's) first line. Each such lookup of a word in a sentence the vocabulary has no LLM
translation for yet asks two free-pool models at once, like the LLM translation popup, and uses
one request from the daily quota of each.

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

Enter your API keys on the [AI Keys](http://localhost:6100/ai-keys/) page (in the menu). Next to
each key the page says where to get it. A key you enter pays for your own articles only and
works from your next article on.

- **Free pool**: any one of the free keys on the page is enough (Groq, Google Gemini, Z.ai); more
  keys make the pool faster and more reliable. Lexiflux does not use an OpenRouter key: the pool
  leaves out the OpenRouter models because with them more Articles ended in "busy".
- **GPT-5.6 Sol and Luna**: an OpenAI key (paid).
- **Claude Opus**: an Anthropic key (paid).

For each key the page shows whose key your articles use: yours, the server's, or none. A saved
key is never shown again, only its last 4 characters; you can replace or clear it. Lexiflux keeps
the keys in its database, encrypted with the server's secret key (`SECRET_KEY`); if that key
changes, enter yours again.

Whoever runs Lexiflux can also give the server keys, which every user without a key of their own
uses (`GROQ_API_KEY`, `GEMINI_API_KEY`, `ZAI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`):

- **Running from source**: in a `.env` file in the Lexiflux folder, or in the environment.
  `llmbroker env freetier` prints the free keys with a link to get each one (it also lists
  OpenRouter).
- **Docker**: pass them to `docker run`, see [Docker](docker.md#ai-keys).
- **A hosted server**: in the server's environment variables (secrets).

If a key is missing or refused, the article says whose key it was, yours or the server's, and
links to the AI Keys page.
