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
| Wiktionary | the dictionary entry: part of speech and a numbered list of senses | 21 / 24 listed from the dictionary form, 19 / 24 from the clicked text | 0.13 s p50, 0.21 s p90 |
| Google | Google's translation, then its dictionary alternatives by part of speech | 15 / 24 listed, 6 / 24 as the translation | 0.07 s |

The bench is 24 words in English, German and Serbian, each in a sentence that decides its
sense, translated into Russian (2026-09-24 to 2026-09-26).

- **LLM translation is the default** for new users (a Dictionary article with this
  translator). It is the only translator that picks the sense from the text, and it answers
  within a second. It needs the free-pool keys and shares their daily quota with the sidebar
  articles (Groq about 1,000 requests a day, Gemini about 500).
- **Wiktionary** needs no keys and nothing installed, and it shows the whole range of senses.
  It does not choose among them, so the vocabulary history takes the LLM translation instead
  (see Vocabulary history), which uses the pool's quota. English words get equivalents in the
  user language, and the Russian Wiktionary has Russian senses for every word it has; many
  German and Serbian senses have English definitions only. It needs kaikki.org to be reachable.
- **Google** is the fastest and covers every language pair Google supports, but it translates
  the bare word, so it guesses the sense. It has no dictionary data for Serbian, and it depends
  on an unofficial endpoint.
- Not offered: MyMemory (3 of 24 right); Linguee (no answer for any German item, no Serbian)
  and PONS (no answer for any item). Glosbe, Linguee, PONS and similar sites remain available
  as Site articles in the sidebar.

## No fallback

- A translator never hands the word to another one. When it fails, the popup shows an alert
  that says what went wrong and, where the reader can act, what to do: retry, wait for the rate
  limit, pick another translator.
- A translator that reports nothing found shows the "found no translation" alert, not an empty
  popup.
- Failures are never cached; the next click asks again.

## LLM translation

- Free pool only: two free-tier models are asked at once and the first answer wins, so every
  LLM translation, the popup's or the vocabulary history's, spends one request from the quota
  of each of the two. A reader who wants a paid model makes the popup a Translate AI article
  instead.
- The model gets the selected word or phrase marked inside a short passage: its sentence plus
  the previous and the next sentence, whatever the sentence length.
- It replies with the translation only, in dictionary form. For a separable verb or a fixed
  expression it translates the whole unit (`steht ... auf` as `aufstehen`, not `stehen`).
- **3 s limit** on the whole answer, queueing included. Past it the popup shows the "busy"
  alert; an answer that arrives later is dropped.
- Answers are cached per word, passage and language pair, shared by all users of the server.

## Wiktionary

- **Online, nothing installed.** The reader never runs a command to install or refresh
  dictionary data. The clicked word is lemmatised on the server (simplemma, a dependency of the
  app, for English, German and Serbo-Croatian), then the kaikki.org pages of the word as clicked
  and of its lemma are fetched from the English and the Russian Wiktionary at once. The option
  is offered for books in English, German, Serbian, Croatian and Bosnian.
- Why online: a local copy of the data means a 3.2 GB download and an import that every
  reader would have to run and repeat; the per-word pages need nothing and answer in about
  0.1 s.
- **Russian first for a Russian reader.** Only a Russian reader gets the Russian Wiktionary,
  and its entries come first; other readers get the English Wiktionary. Translations of English
  words are shown in the user language; the English Wiktionary files Serbian, Croatian and
  Bosnian translations as Serbo-Croatian, so readers of these three languages get those.
  Likewise, Norwegian readers get the Norwegian, Bokmål and Nynorsk translations, Filipino
  readers the Tagalog ones, Chinese readers the Mandarin ones (most Chinese translations are
  filed as Mandarin) and Kurdish readers the Kurmanji ones.
- **Lemma.** An inflected form finds its lemma ("springs" → "spring", "Träumen" → "Traum",
  "kosu" → "kosa"). Serbian is lemmatised in Latin script, which the lemmatiser knows better;
  the English Wiktionary files Serbian words in Latin, the Russian one in Cyrillic (its Cyrillic
  pages are the fuller ones), so a word in either script finds the same entries. A Croatian book
  uses the Russian Wiktionary's Croatian section instead, whose pages are in Latin: it has the
  Croatian forms the Serbian section lacks ("mlijeko" → молоко; 13 of 16 common Croatian words,
  against 7 in the Serbian section). A Bosnian book uses the Serbian section. Accents printed
  on a Serbian word are dropped ("kȍsu" is looked up as "kosu"): Wiktionary's page names have
  none.
- **Capitals.** What a capital means depends on where the word stands in its passage. It
  starts a sentence when nothing comes before it, or when the text before it ends in `.`, `!`,
  `?`, `…` or `:`, optionally followed by quotes or dashes. The book's structure counts too:
  a heading, a paragraph, a list item or a table cell ends where the next one starts, so the
  first word after a heading starts a sentence even though the heading has no full stop
  ("CHAPTER VIII. The Queen's Croquet-Ground" / "A large rose-tree …"). In a plain-text book
  only a blank line ends a block: its single line breaks mostly wrap a sentence (Alice in
  Wonderland has 232 capitals in mid-sentence at the start of a wrapped line). Quoted speech
  after a comma or a semicolon starts a sentence when the opening quote touches the word
  (`He asked, “Will you come?”`, also with „ « » ‹ › ‘ ‚ and straight quotes); a straight quote
  after a comma and a space closes the speech instead (`"Come," Tom said`). The full stop of
  Mr., Mrs., Ms., Dr., St., Hr., Fr., z. B. and d. h. does not end a sentence ("said Mr.
  Bennet").
  - English and Serbian, sentence start: the capital says nothing, so the word is looked up in
    lower case ("Still" is "still", not a surname). Only when nothing is written like it in
    lower case is it looked up as written, as a name ("London").
  - English and Serbian, mid-sentence: the capital marks a name, so the word as written is
    looked up too, in the same round ("China" and "china"). A Serbian name comes first ("Luka"
    → Лука, then "luka", harbour). An English name comes first when the English Wiktionary
    translates it into the user language, as it does countries and months ("China" → Китай,
    "May" → май, "March" → март, "Turkey" → Турция). An English name without translations is
    mostly a surname or the personified "King" or "Rabbit" of a tale, so it follows the
    lowercase word ("the King" → король, then "King").
  - German: a capital marks a noun, so the word keeps its case ("Schloss", not "schloss" of
    "schließen"); in mid-sentence a noun with entries of its own costs no further lookup. At a
    sentence start the capital says nothing. When the lemma is written in lower case, its
    entries come first ("Ich" → ich, «я», then das Ich; likewise "Aber", "Nichts", "Es",
    "Wenn"). Otherwise the lowercase
    spelling is looked up in one more round and its entries come first ("Gut, dass …" → gut),
    unless the lowercase spelling is only a form of another word: then the noun stays first
    ("Schloss", then "schließen"). A capitalised German word that finds nothing, or only names,
    is looked up in lower case wherever it stands ("Schön" → schön).
  - Without a passage, English and Serbian words are taken as starting a sentence and German
    ones as standing in mid-sentence. The popup and the sidebar both pass the passage.
  - A word clicked in lower case stays in lower case where the lemmatiser only capitalises it
    ("robin" is the bird, not the name "Robin"); a capitalised click keeps the lemmatiser's
    capital ("I").
- **Scope of the position rules.** They cover the common shapes of a sentence start and are not
  extended shape by shape: the remembered translation comes from the LLM, so a shape they miss
  only reorders the popup's list. The bar is a whole book measured against hand-marked sentence
  starts: in Alice in Wonderland the shapes not covered (a quote without a comma before it, a
  bracket after a full stop) change the first entry of 1 of 54 distinct words.
- **Forms the lemmatiser does not know.** A contraction, an archaic or a nonstandard form, or a
  German verbal noun, that the lemmatiser leaves as it is follows the "form of" link on its own
  page ("I'm" → "I", "liveth" → "live", "wouldst" → "will", "curiouser" → "curious", "Tanzen" →
  "tanzen"): the popup shows the word's own senses, then its "form of" line, then the lemma's
  entries. At most three links are followed; links marked dialectal, initialism, acronym,
  misspelling or pronunciation spelling lead to unrelated words and are not followed, and an
  alternative spelling is followed only for a contraction. A word with its own entries ("she",
  "be") leads with them. About 4 % of real clicks need this second round of requests.
  The reader splits words at apostrophes, so a contraction is looked up when the reader selects
  it across the apostrophe; a single click sends one side of it ("don" of "don't").
- **Russian pointers.** A Russian Wiktionary sense that only names another word spelled alike
  ("вариант hair" under "hear", "устар. вариант tale" under "tell") is left out, like the English
  Wiktionary's alternative spellings: it leads to an unrelated word.
- **Order.** Within a word, entries with equivalents in the user language come before
  entries that have English definitions only. Of the words looked up for a click (the word, its
  lemma, the word as written), the ones written in the case the capital rules above put first
  come first; after that the one with more senses ("made" is "make" before it is a maggot). A
  name reached through a lemma or a link is mostly someone's surname and is left out when
  anything else is found; otherwise it is the answer ("Beogradu" → "Beograd", Belgrade).
- **Time.** A request gets about 2 s, and the whole lookup stays within the popup's 3 s; a page
  that has not arrived by then counts as failed. The connections to kaikki.org stay open for a
  minute between lookups: readers click words seconds apart, and new connections cost about
  0.2 s more per click.
- **Cache.** Every page is kept for 30 days, a missing page too (18 % of requests are for pages
  kaikki.org does not have, repeated for every inflected form), and shared by all users of the
  server. Timeouts, connection errors, 5xx and 429 answers are never cached, nor is a page that
  is not kaikki.org's data.
- **Outcomes.** Entries found: the sense list. Every page missing: the "found no translation"
  alert. kaikki.org unreachable (timeout, connection error, 5xx, 429, or not its data) and no
  entries: the translator network alert, "Wiktionary (kaikki.org) is not reachable". One
  edition failing while the other has entries: those entries, and nothing cached for the failed
  page, so the next click asks again.
- **Privacy.** Every lookup that is not cached sends the word to kaikki.org.
- kaikki.org answers an unknown page address with 404, like a missing word, so a changed site
  layout would look like "no entry" everywhere. An opt-in check against the real site, a known
  word from both editions, guards it.
- **Measured** (2026-09-25/26, Russian reader): 21 of 24 bench senses listed from the
  dictionary form, 19 from the clicked text; the lemma listed for 42 of 45 inflected forms from
  real books; the first entry is the word or its lemma for all of Alice in Wonderland's 200
  most frequent words (a check of the head word only, not of its part of speech or sense: "see"
  leading with the noun "престол" passes it); 20 of 20 contractions (selected whole) and
  archaic forms reach an entry. Per click with nothing cached (2026-09-26, 109 clicks): 0.13 s
  p50 and 0.21 s p90. Clicks one after another (15 clicks) took 0.08 s p50 and 0.21 s p90,
  clicks 20 s apart (15 clicks) 0.13 s p50 and 0.22 s p90; no click after a pause paid for new
  connections. After more than a minute without a lookup the connections are new: 0.3–0.45 s.
  The first word of a language after the server starts also loads its lemmatiser: 0.4 s for
  English, 0.5 s for Serbian, 0.8 s for German. With the passages the
  words stand in, the results are the same, and "Seine" at the start of a sentence leads with
  "sein" (the lemma is the first entry for 42 of the 45 inflected forms).
- **Memory.** Each language's lemmatiser data loads at its first word and stays. The lemmatiser
  runs in its low-memory mode: the same lemmas (checked on 140,000 words per language) for about
  a fifth of the memory: 3 MB for English, 26 MB for German, 8 MB for Serbo-Croatian, instead
  of 30, 141 and 37 MB; a word takes about 12 µs instead of 2. The running server measured
  150 MiB at start and 204 MiB with all three loaded, well inside the 512 MB of Koyeb's free
  instance.
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

- Every successful popup lookup is remembered for the vocabulary export and Anki with a single
  translation, and that translation is the LLM translation of the word in the passage it was
  looked up in, whatever the popup's translator. A dictionary lists senses without knowing
  which one the text means: its first sense made wrong cards for common words ("see" →
  престол, "felt" → войлок, "might" → мощь, "even" → чётный).
- The translation remembered is of the unit the popup's LLM translation translates: for a word
  inside a fixed expression or a separable verb that is the whole unit, so a reverse Anki card
  can read as a phrase ("встать → feet"). This is accepted: it is the sense the reader met.
- With LLM translation as the popup, its answer is remembered.
- With Wiktionary or Google as the popup, the popup shows its own answer at once. The LLM
  translation of the same word and passage (free pool, 3 s limit, the popup's cache) starts
  after the popup has its answer, and the popup never waits for it. When it answers, it
  becomes the entry's translation.
- Until then, or when the pool fails or has no answer in 3 s, a new entry holds the
  translator's first line: Google's translation without the alternatives, or Wiktionary's first
  sense in the user language (the Russian Wiktionary's usage labels such as "экон." or "поэт.,
  перен." and the stress marks dropped: "весна", not "весна́") or, when no sense is in the user
  language, the first English definition. The Wiktionary sense list in the popup keeps labels
  and stress marks. The next lookup of the word asks the LLM again.
- An entry that already has an LLM translation into the reader's language keeps it, with the
  passage it translates, until the new LLM translation arrives; a failed one leaves both
  unchanged.
- An entry that has the LLM translation into the reader's language of the same passage is not
  asked again, also after the server restarts.
- An AI article as the popup remembers its answer, as the popup shows it.
- Every other Wiktionary or Google lookup asks the LLM (unless the popup's cache has the
  answer), and like every LLM translation it races two pool models: it spends one request from
  the quota of each, the same free quota as the LLM popup and the sidebar articles.
- Failed lookups are not remembered.
- **Measured** (2026-09-26, Russian reader, real free pool): 50 of Alice in Wonderland's 200
  most frequent words at their first occurrence in the book (12 whose Wiktionary first sense was
  known to be wrong, and 38 others spread over the list), judged by hand for fitting the sense
  the word has there. Wiktionary's first sense fit 24; the LLM translation in context fit 47, 11
  of the 12 known wrong ones among them. 13 of the 47 translate a phrase the word belongs to, as
  the prompt asks for fixed expressions: "feet" in "started to her feet" → встать, "at" in
  "wondered at" → удивиться, "make" in "make out" → разглядеть. For about 10 of them the line
  does not translate the word itself, and its reverse Anki card reads like "встать → feet".
  Counting those as misses, the LLM translation fits about 37 of 50, against Wiktionary's first
  sense at 24. Groq's GPT-OSS 120B answered 41 and fit 40; Gemini 3.5 Flash Lite answered 9 and
  fit 7. Misses: "would" in "would be worth" → "быть стоющим" (Gemini), "the" in the chapter
  title "Down the Rabbit-Hole" → "в" (Gemini), the "court" of the trial → "двор" (Groq). Asked
  about 35 times a minute, 46 of the 50 were answered within 3 s; the other 4 hit the free
  tiers' per-minute limits (Groq allows 30 requests a minute, Gemini's quota ran out for a
  minute) and were answered when asked again a minute later, as the next lookup of the word
  would.

## Language Preferences

- The editor offers exactly the three translators. A choice outside them, or a translator
  that cannot serve the language pair (Google for a language it does not know, Wiktionary for
  a book language it has no data for), cannot be saved.
- A Site cannot be saved as the inline translation.
- The check spends no pool call and makes no network request.
- Every translator can be chosen for the popup and for a sidebar Dictionary article; the choice
  is not narrowed. Instead the editor describes the selected translator in one line: what it
  returns and where it fits best (LLM translation for the popup, Wiktionary's long sense list for
  the sidebar, Google fast but blind to the sentence). The default popup translator is LLM
  translation.

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
