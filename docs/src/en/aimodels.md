# AI Models

Lexiflux uses AI models to write the articles in the `Sidebar`
(you open it with the blue binocular icon).

You can also use AI for inline text translation. By default
it uses Google Translate.

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
There are a number of dictionaries embedded like Google Translate, Linguee Translator, MyMemory Translator, PONS Translator.

### Site
You define what a URL to open and with which parameters.
This is useful for a good translator that does not have an API, like glosbe.com.

Most of them should be opened in an external window, but some of them can even be opened inside the Sidebar.

This is controlled by the `open in new window` parameter.

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
