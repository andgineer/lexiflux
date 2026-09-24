# Blind review: the short dictionary article of a reading app

An English-speaking reader is reading a book in English, German or Serbian. They
selected a word or a phrase in the text, and the app showed a short dictionary article
about it in a side pane, written in English. Several anonymous systems answered the
same selection. For each word you get all of their answers, each under a random label
that means nothing and changes from word to word. You produced none of them and have
no stake in any. Do not try to work out which system wrote what, and do not assume two
answers to different words share an author.

## What the packet holds

Each entry is one selection:

- `passage` — the text the reader was reading, with the selection marked ⟦like this⟧.
  Where the selected word occurs more than once, only the marked occurrence was selected.
- `selected` — the selected words exactly as they stand in the text.
- `reference` — the item author's reading: the sense the selection has in this passage
  and the unit an article should be headed by. Use it as a check, not as law: if you are
  sure it is wrong, say so in a `minor` note and judge by your own reading.
- `answers` — every system's article, under its label.

## What a good answer is

A compact dictionary article about the selected unit, for a reader in the middle of a
book who wants to understand this passage and learn the word:

- It is headed by the unit's dictionary form: the base form of an inflected word
  (`kosu` → `kosa`), the whole verb for one piece of a separable or reflexive verb
  (`steht … auf` → `aufstehen`, `se … vratio` → `vratiti se`, `made … out` →
  `make out`), and the expression in its dictionary form for a multi-word selection.
- It leads with the sense the unit has in this passage. Other real senses may follow.
- It gives English equivalents, forms where they help, usage, origin only where it is
  reliable, and a few short examples with English translations. For an English word the
  "translations" are English definitions or synonyms: the reader reads English books and
  English is also their own language.
- It is written in English. Only the headword, quoted source text and source-language
  examples are in the source language.

The pane renders HTML. The format this app accepts: only `<b>`, `<i>`, `<table>`, `<tr>`
and `<td>`, with no attributes; no Markdown (`**x**`, `*x*`, `# heading`, `| a | b |`
tables) and no code fences. Any other tag (`<p>`, `<br>`, `<ul>`, `<li>`, `<h3>`,
`<div>`, `<span>`, …) breaks it. Line breaks are measured separately; do not count them
against an answer.

## How to judge

Check everything yourself — you know these languages. In order of weight:

1. **Truth** — anything the reader would memorise or understand wrong. A sense the word
   does not have, a wrong translation, a false etymology stated as fact, a wrong
   grammatical claim (gender, plural, case, aspect, government, separability,
   conjugation, auxiliary), an example that is ungrammatical, unidiomatic or not in the
   source language, a word from another language passed off as the source language's,
   an English translation that distorts the example, and a statement that the selection
   means something in this passage that it does not mean there. A hedged "probably" is
   not an error.
2. **Usefulness for this reader** — the sense used in the passage made clear, real other
   senses, real usage and collocations. Padding, invented usage notes and off-topic
   material count against.
3. **Instructions** — English throughout outside the headword, quoted source text and
   examples; examples translated; the format above.

**Severity.** *Serious*: a reader who trusts the answer would learn something false
about the word, its grammar or its use, would misunderstand the passage, or would copy
a wrong example. *Minor*: everything else — typos, a weak or ill-fitting example that is
still correct, a peripheral inaccuracy, formatting.

An article that merely lists another sense first, without claiming it is the one used
here, is recorded as `"context_sense": false` and is not by that alone a serious error.
An article that says or clearly implies that the passage uses a sense it does not use
has a serious error, and you quote that claim.

**Score anchors** — use them as written, so scores mean the same across reviewers:

- **5** — nothing false; useful to this reader; follows the format.
- **4** — nothing that matters is false; minor slips only.
- **3** — usable, but thin or padded, or one serious error outside the core of the
  entry (a side etymology, a side sense, a usage note).
- **2** — a serious error in the core (the sense used in the passage, the word's main
  senses, its grammar, its main examples), or several serious errors at the edges.
- **1** — several serious errors in the core, or the answer would mislead the reader
  about the word itself or about the passage.

Read every answer in full. Do not skim, and do not let length stand in for quality.

## What to record per answer

- `score` — 1 to 5, by the anchors.
- `context_sense` — `true` when the article leads with the sense the selection has in
  this passage: the first sense, translation or definition it gives after the heading
  is that sense, or it opens by naming that sense as the one used here. `false`
  otherwise, including when it never gives that sense.
- `lemma` — `true` when the heading (the first bold text) is the dictionary form of the
  selected unit: the base form, not the inflected one; the whole separable or reflexive
  verb with its particle or `se`/`sich`, not the selected piece; the whole expression for
  a multi-word selection. An article may add an article or a grammatical note to the
  heading (`die Leiter`). Where the reference names two acceptable headings, either is
  `true`.
- `serious` — every serious error, each with the offending text quoted exactly as it
  stands in the answer, so it can be found by search, and one sentence on why.
- `contract` — `true` when the answer keeps the format above and is written in English
  outside the headword, quoted source text and source-language examples; `false`
  otherwise, with `contract_why` naming what broke it (the tag, the Markdown, the
  language). `contract_why` is empty when `contract` is `true`.
- `minor` — short notes on the minor problems, or an empty list.

## Output

Write one JSON object per line (JSONL) to the output file named in your task, one line
per answer, in this exact shape:

```
{"word": "<word_id>", "label": "<label>", "score": 4, "context_sense": true, "lemma": true, "serious": [{"quote": "<exact text>", "why": "<one sentence>"}], "contract": true, "contract_why": "", "minor": ["<short note>"]}
```

`serious` is an empty list when there is none. `score` is an integer; `context_sense`,
`lemma` and `contract` are JSON booleans. After all answer lines of a word, add one line
for that word:

```
{"word": "<word_id>", "ranking": ["<best label>", "...", "<worst label>"], "note": "<one sentence on what separates the top from the bottom>"}
```

Every label of every word in your packet gets exactly one answer line. Write nothing
else to the file.

Then return, as your final message, a short summary: for each word, the best and worst
labels and the most important serious errors you found.
