# Inline translation

The inline translation is the popup that opens inside the text when the reader selects a word
or phrase. It answers at once and briefly; the sidebar articles (`ai-articles.md`) are the place
for explanations. Each book language has its own inline translation in Language Preferences.

## Options

The popup is normally a Dictionary article, which uses one of three translators. The same three
are offered for a Dictionary article in the sidebar. The popup can also be any AI article
(`ai-articles.md`), but not a Site: a Site opens a web page, which the popup cannot show. The
rules below are about the three translators.

| Translator | What the popup shows | Right sense (24 bench items) | Answer time |
|---|---|---|---|
| LLM translation | one equivalent in the user language, for the sense the word has in the passage | 23 / 24 chosen | 0.59 s p50, 0.78 s p90 |
| Wiktionary | the dictionary entry: part of speech and a numbered list of senses | 20 / 24 listed | under a millisecond, offline |
| Google | Google's translation, then its dictionary alternatives by part of speech | 15 / 24 listed, 6 / 24 as the translation | 0.07 s |

The bench is 24 words in English, German and Serbian, each in a sentence that decides its
sense, translated into Russian (2026-09-24 and 2026-09-25).

- **LLM translation is the default** for new users (a Dictionary article with this
  translator). It is the only translator that picks the sense from the text, and it answers
  within a second. It needs the free-pool keys and shares their daily quota with the sidebar
  articles (Groq about 1,000 requests a day, Gemini about 500).
- **Wiktionary** needs no network, no keys and no quota, and it shows the whole range of
  senses. It does not choose among them. English words get equivalents in the user language;
  many German and Serbian senses have English definitions only.
- **Google** is the fastest and covers every language pair Google supports, but it translates
  the bare word, so it guesses the sense. It has no dictionary data for Serbian, and it depends
  on an unofficial endpoint.
- Not offered: MyMemory (3 of 24 right); Linguee (no answer for any German item, no Serbian)
  and PONS (no answer for any item). Glosbe, Linguee, PONS and similar sites remain available
  as Site articles in the sidebar.

## No fallback

- A translator never hands the word to another one. When it fails, the popup shows an alert
  that says what went wrong and, where the reader can act, what to do: retry, wait for the rate
  limit, pick another translator, install the Wiktionary data.
- A translator that reports nothing found shows the "found no translation" alert, not an empty
  popup.
- Failures are never cached; the next click asks again.

## LLM translation

- Free pool only: two free-tier models are asked at once and the first answer wins. A reader
  who wants a paid model makes the popup a Translate AI article instead.
- The model gets the selected word or phrase marked inside a short passage: its sentence plus
  the previous and the next sentence, whatever the sentence length.
- It replies with the translation only, in dictionary form. For a separable verb or a fixed
  expression it translates the whole unit (`steht ... auf` as `aufstehen`, not `stehen`).
- **3 s limit** on the whole answer, queueing included. Past it the popup shows the "busy"
  alert; an answer that arrives later is dropped.
- Answers are cached per word, passage and language pair, shared by all users of the server.

## Wiktionary

- Source: the kaikki.org extracts of the English and the Russian Wiktionary, for English,
  German and Serbo-Croatian. The Wiktionary option is offered for books in English, German,
  Serbian, Croatian and Bosnian.
- The data lives in its own file next to the application database, not in the database and not
  in the Docker image. The operator builds it with the `import-wiktionary` command and rebuilds
  it when fresher data is wanted (Wiktionary changes slowly; about monthly is enough). The
  import downloads about 3.2 GB, takes about three minutes and produces a file of about 230 MB.
  A rebuild replaces the file in one step, so readers never see a half-built dictionary.
- Translations of English words are kept for Russian and for the user languages set at import
  time. The English Wiktionary files Serbian, Croatian and Bosnian translations as
  Serbo-Croatian, so readers of these three languages get those.
- Without the file the option stays selectable; the popup says the data is not installed and
  gives the command.
- An inflected form finds the entry of its lemma ("springs" → "spring", "gingen" → "gehen",
  "kosu" → "kosa"). Serbian finds the same entry in either script, and pitch accent marks are
  ignored.
- For a Russian reader, entries of the Russian Wiktionary come first, then the English one;
  other readers get the English Wiktionary. Entries with equivalents in the user language come
  before entries that have English definitions only.
- A form shared by several lemmas lists every lemma. In German, lemmas capitalised like the
  clicked word come first (a capitalised German word is a noun). In English and Serbian a
  capital usually only starts a sentence, so a capitalised word is looked up as if written in
  lower case: "Spring" at a sentence start leads with the season, and a name spelled the same
  (the Russian Wiktionary files surnames as nouns) comes after it. Among the rest, the lemma
  with more senses leads.
- **Licence:** Wiktionary is CC BY-SA 4.0 and GFDL. Every Wiktionary result ends with "from
  Wiktionary, CC BY-SA 4.0", linking to the word's Wiktionary page and to the licence. In the
  popup a long sense list scrolls and the attribution stays in view below it.

## Google

- Google's JSON translation endpoint, with three client identifiers tried in order. The next
  identifier is tried only when Google refuses one; a network failure is reported at once.
- A lookup has 3 s in all, shared by the identifiers: no identifier is tried after that, and a
  request waits for the connection and for each read at most the time left. A request slow at
  more than one of these steps can still run past 3 s.
- The dictionary alternatives, grouped by part of speech, are shown when Google has them
  (English and German, not Serbian).
- When Google returns the word itself and no alternatives, it found nothing.

## Vocabulary history

- Every successful popup lookup is remembered for the vocabulary export with a single
  translation: the LLM's answer, Google's translation without the alternatives, or
  Wiktionary's first sense in the user language (the Russian Wiktionary's usage labels such as
  "экон." or "поэт., перен." and the stress marks dropped: "весна", not "весна́") or, when no
  sense is in the user language, the first English definition. The Wiktionary sense list in
  the popup keeps labels and stress marks.
- Failed lookups are not remembered.

## Language Preferences

- The editor offers exactly the three translators. A choice outside them, or a translator
  that cannot serve the language pair (Google for a language it does not know, Wiktionary for
  a book language it has no data for), cannot be saved.
- A Site cannot be saved as the inline translation.
- The check spends no pool call and makes no network request.

## Serbian: Lingea next to Glosbe

- Glosbe stays the default Site article for every language: its real-world example sentences
  are the point.
- When language preferences are created for Serbian with a user language Lingea has a
  dictionary from (36 languages at recnici.lingea.rs, among them English, German and Russian),
  a Lingea Site article is added after Glosbe. Lingea finds the lemma of an inflected Serbian
  form and separates homonyms, which Glosbe's page does not. The rule is applied again when the
  reader picks a user language for the first time, because preferences created before that
  have no real user language yet.
- The Lingea link opens the dictionary from the reader's current user language. When Lingea
  has no dictionary from it, the article shows an alert saying so instead of a link to a
  wrong dictionary. Any Site URL can ask for the user language in Lingea's naming.
- Lingea takes Latin script, so a Cyrillic word is transliterated in its link. Any Site URL can
  ask for this transliteration.
- Preferences copied to another book language do not take the Lingea article.
