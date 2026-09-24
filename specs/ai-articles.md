# AI articles

AI articles are the sidebar panels, and optionally the inline translation, that an LLM
writes about the selected word or phrase. Every AI call goes through llmbroker; lexiflux
talks to no provider directly.

## Models

Every AI article names one of four models:

| Model | What it is | Measured on the deeper article (24 words) |
|---|---|---|
| Free pool | llmbroker's routed pool of free-tier models | short article: first text 0.8 s median, whole answer p90 3.6 s |
| GPT-5.6 Sol | OpenAI, direct | 4.04/5, 5 serious errors, 0.78 s to first text, 7.3 s whole, $0.036 per article |
| GPT-5.6 Luna | OpenAI, direct | 3.67/5, 8 serious errors, 2.69 s to first text, $0.003 per article |
| Claude Opus | Anthropic, direct | 4.38/5, 3 serious errors, 17.6 s to first text (p90 29.6 s), $0.058 per article |

The numbers come from echo-words' measurements of its "Подробнее" article
(`../echo-words/spec/decision-llm-backend.md`).

- The default **Article** uses the free pool: it costs nothing and, once the pool has learned
  which of its models answer, text starts in about a second.
- Every other AI article defaults to **Sol with reasoning off on priority processing**. Of the
  configurations that put text on screen within about a second, it reads best by a wide margin
  and makes the fewest serious errors. Only Opus reads better, and it starts after 17.6 s.
- **Luna** is offered as the cheap option and **Opus** as the most accurate one; both lose
  to Sol on the balance of quality, speed and price.
- Not offered, measured and beaten: the mid-size GPT (3.62/5, 13 serious errors), Sonnet
  (3.38/5, 17), Haiku (2.04/5, 53 serious errors, wrong-language forms and invented senses).
- Not offered, unmeasured: paid Gemini, Grok, DeepSeek, Mistral and local models (Ollama).
  Every offered option is one more set of knob defaults to measure and keep current, and a
  local model needs memory the hosted deployments do not have.
- A model that the llmbroker catalog no longer carries is not offered in the editor, and an
  article still set to it shows the retired-model message instead of failing.

### Free pool members

- The pool excludes the OpenRouter models (Nemotron 3 Ultra and Laguna S 2.1), as echo-words
  does. Nemotron is a reasoning model: it answers HTTP 200 at once, then often holds its lane
  past the pool's 25 s wait without text. Laguna answered quickly when it answered, but on the
  shared free key most of its calls were rate-limited. As the race's second lane, neither could
  rescue a Gemini Flash Lite stall (10–40 s on Google's side in some windows), and in those
  windows 7–13% of Articles ended "busy".
- With them out, the second lane is Groq, which answers in 2–3 s. At the same moments, the pool
  with the exclusion answered 27 of 28 Articles (first text p50 0.8 s, p90 2.1 s); in a later
  window without a stall, 36 of 36 (first text p50 0.6 s, p90 0.8 s, whole answer p90 2.2 s).
- Groq's free tier is the limit of this rescue: once its rate limit is hit, a Gemini stall again
  ends "busy".
- The exclusion is kept in the broker's own state (llmbroker's disable), so it holds locally, in
  Docker and on Koyeb, and survives model-list refreshes. A name the catalog no longer carries
  is skipped with a log line.
- The OpenRouter key is then unused, so the no-key message does not list it, and a server with
  only that key gets the no-key message instead of "busy".

### Reasoning effort and processing tier

Each AI article on a paid model has two knobs, with per-model defaults:

| Model | Default effort | Default tier |
|---|---|---|
| Sol | none | priority |
| Luna | low | priority |
| Opus | low | (not offered) |

- Knobs exist only where echo-words measured them: effort (none / low / medium / high) on
  OpenAI and Anthropic, processing tier (priority / standard) on OpenAI only.
- Priority processing costs about twice as much and answers about three times faster on Sol
  (a whole deeper article in 7.3 s against 22.7 s).
- Reasoning decides the wait for the first text and cannot be bought back: Sol at low effort
  starts after 6.2 s. With reasoning on, answers also scored lower on the deeper article.
- "Model default" sends nothing, and the provider decides.
- The free pool takes no knobs.
- An article with a knob its model's provider does not have, or a model that is not offered,
  cannot be saved.

## Keys

- lexiflux stores, reads and shows no API keys. There is no settings page for them, and users
  never enter keys.
- llmbroker reads the operator's keys from the environment and from `.env` in the repository
  root. In Docker they are passed to the container as environment variables; on Koyeb they are
  Koyeb secrets exposed as environment variables.
- Every user spends the operator's keys, paid models included. There is no per-user limit; if
  sign-ups are open, a daily per-user limit is the follow-up.
- A missing key is explained in the article itself: for the pool, the help and link of every
  key that serves a pool model, the environment variable name and where it goes; for a paid model, its provider's key
  help and variable name. No message points to a settings page.

## Broker state

- One broker per process. Requests are attributed to the user in llmbroker's journal, but all
  users share the pool and its learned ordering.
- Locally and in Docker the broker keeps its state in lexiflux's own llmbroker home next to the
  database, not in the machine-wide llmbroker directory: the pool exclusions are persistent, and
  there they would also switch those models off for every other llmbroker user on the machine.
- On Koyeb it keeps its state in lexiflux's PostgreSQL. The pool learns which models answer
  fast; on a cold broker Groq gpt-oss-120b wrote 10 of 23 answers at 2.2/5 with first text p90
  14.5 s, while warm, Gemini wrote 20 of 24 with first text p90 1.6 s. Keeping the state across
  deploys keeps the pool warm.
- An llmbroker schema upgrade may drop that state; the pool then re-learns. No keys live there.

## What the model is given

- The prompt gets two plain values: the selected **word** (as it stands in the text) and its
  **sentence**. There are no in-text marks.
- A selection spanning several sentences gets all of them.
- A sentence shorter than 6 words is extended with the previous and the next sentence, where
  they exist.
- Prompts get language names, not language codes.

Why word + sentence (lexiflux's own bench, 24 words in English, German and Serbian, scored
blind on Gemini 3.5 Flash Lite): with echo-words' short-article rules, a marked passage scored
3.88/5 and word + sentence 3.58/5. The whole gap came from two cases the bench over-represents:
a sentence cut short at an abbreviation or dialogue line, and one word repeated in a sentence in
two senses. On the ordinary items word + sentence was as good or better (4.25 against 3.92, one
serious error against two). The short-sentence extension covers the first case; the second is
rare and accepted. The previous lexiflux prompt scored 3.17/5 with 15 serious errors.

## Prompts

- **AI dictionary** (the default Article) uses echo-words' short-article rules.
- **In depth** uses echo-words' extended prompt, bound to 4000 characters, plus one sentence
  that makes it head the whole unit (`make out`, `aufstehen`, `vratiti se`) rather than the
  selected piece.
- **Origin** gives an origin only where the model knows it and leaves it out otherwise.
- A custom AI article's prompt may use the word, the sentence and both language names.

## Streaming

- Sidebar articles stream into their panel as the model writes; the inline translation waits
  for the whole answer.
- The free pool asks two models at once and waits up to 25 s. The first to produce text
  streams into the panel; if the other finishes its whole answer first, that answer replaces
  the panel's text.
- Changing the selection aborts every running article; its provider call is cancelled when
  its next text arrives.
- A stream is never compressed, so text is not held back until the answer ends.
- An answer cut off mid-stream keeps its text and adds a "cut off, retry" notice.
- Only complete answers are cached.

## Rendering

- Panels whose prompts lay the answer out with line breaks keep them.
- Markdown bold and italic in an answer are shown as bold and italic.

## Default articles

New users get:

| Title | Type | Model |
|---|---|---|
| Article | AI dictionary | free pool |
| In depth | In depth | Sol, none, priority |
| Sentence | Sentence | Sol, none, priority |
| glosbe | Site | — |

The inline translation is the Google Translate dictionary. A new AI article a user adds
defaults to Sol, none, priority.
