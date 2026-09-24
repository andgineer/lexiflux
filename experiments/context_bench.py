"""Phase 1 of specs/plans/20260922-llmbroker-migration.md: can the default AI article drop the
[FRAGMENT]/[HIGHLIGHT] marks and take the selected word plus its sentence?

Arms, each run on the pool's two workhorses declared as custom direct models so the model
is held fixed:

    A  current lexiflux/resources/prompts/AI dictionary.txt, current marked passage
    B  new prompt (experiments/context_bench_prompts/AI dictionary.B.txt), marked passage
    C  new prompt (experiments/context_bench_prompts/AI dictionary.C.txt), word + sentence

--pool adds arm C once through the real pool (stream, fastest_of=2, wait=25).
--in-depth adds the In depth smoke on `gpt` (effort none, priority tier), which costs money;
--in-depth-unit runs it again with the variant that names the unit to analyse.
Records already in --out are skipped, so a rerun only fills what is missing.

    source ./activate.sh && python experiments/context_bench.py --arms A,B,C --out experiments/context_bench.json
    source ./activate.sh && python experiments/context_bench.py --arms "" --pool --in-depth
    source ./activate.sh && python experiments/context_bench.py --check
    source ./activate.sh && python experiments/context_bench.py --report
    source ./activate.sh && python experiments/context_bench.py --build-review experiments/.context-bench/review

Outside CI.
"""

import argparse
import asyncio
import dataclasses
import html
import json
import os
import random
import re
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
PROMPTS = Path(__file__).resolve().parent / "context_bench_prompts"
DEFAULT_OUT = REPO / "experiments" / "context_bench.json"
DEFAULT_HOME = REPO / "experiments" / ".context-bench" / "broker-home"

LANG_NAMES = {"en": "English", "de": "German", "sr": "Serbian"}
USER_LANG = "en"

MODELS = {
    "gemini": "google-gemini-3.5-flash-lite",
    "groq": "groq-gpt-oss-120b",
}
BENCH_PREFIX = "bench-"
# Seconds between calls. Groq's free tier allows 8000 tokens a minute, about three answers.
PACE = {"gemini": 6.0, "groq": 18.0}
IN_DEPTH_ALIAS = "gpt"
IN_DEPTH_PARAMS = {"reasoning_effort": "none", "service_tier": "priority"}
IN_DEPTH_PROMPTS = {"in_depth": "In depth.txt", "in_depth_unit": "In depth.unit.txt"}
# USD per million tokens, input / output, for gpt-5.6-sol on priority (echo-words tier_screen.py).
SOL_PRIORITY_PRICE = (8.00, 40.00)
IN_DEPTH_BOUND = 4000
ALLOWED_TAGS = {"b", "i", "table", "tr", "td"}
MARKS = ("[FRAGMENT]", "[/FRAGMENT]", "[HIGHLIGHT]", "[/HIGHLIGHT]")
# Fixed per plan: 10 context words, the production default of mark_term_and_sentence.
CONTEXT_WORDS = 10


@dataclass(frozen=True)
class Item:
    id: str
    lang: str
    klass: str
    passage: str
    selection: str
    occurrence: int
    sense: str
    unit: str
    source: str = "constructed"
    note: str = ""


CLASSES = ("polysemy", "repeated", "separable", "multiword", "cut_short")

ALICE = "tests/resources/alice_adventure_in_wonderland.txt"

ITEMS = [
    Item(
        "en-spring", "en", "polysemy",
        "The old armchair in the corner had seen better days. When Tom sat down, a spring "
        "creaked somewhere deep inside the seat and poked him through the worn cushion. He "
        "jumped up at once and decided that the chair would go to the dump on Saturday.",
        "spring", 1,
        "a coiled metal spring inside the seat of the chair (not the season, not a water source)",
        "spring",
    ),
    Item(
        "en-fine", "en", "polysemy",
        "The letter from the council arrived on Monday morning. Because he had left the car "
        "in front of the fire station, he had to pay a fine of eighty pounds within two weeks. "
        "He grumbled about it all through dinner.",
        "fine", 1,
        "a sum of money paid as a penalty (noun), not the adjective 'fine'",
        "fine",
    ),
    Item(
        "en-saw", "en", "repeated",
        "The workshop was cold and smelled of sawdust. She saw at once that the saw on the "
        "bench was far too blunt to cut the oak. She put it aside and went to look for a "
        "sharper one.",
        "saw", 2,
        "the second 'saw': a cutting tool with a toothed blade (noun), not the past tense of 'see'",
        "saw",
    ),
    Item(
        "en-bear", "en", "repeated",
        "The campers froze. “I can’t bear it,” Anna whispered as the bear lumbered towards "
        "their tent and began to sniff at the cooler. Nobody dared to move.",
        "bear", 1,
        "the first 'bear': to tolerate or endure (can't bear it), not the animal",
        "bear",
    ),
    Item(
        "en-make-out", "en", "separable",
        "She was looking about for some way of escape, and wondering whether she could get "
        "away without being seen, when she noticed a curious appearance in the air: it "
        "puzzled her very much at first, but, after watching it a minute or two, she made it "
        "out to be a grin, and she said to herself “It’s the Cheshire Cat: now I shall have "
        "somebody to talk to.”",
        "made", 1,
        "'made ... out' = make out: to manage to see or recognise something (she made it out "
        "to be a grin); only 'made' was selected",
        "make out",
        ALICE,
    ),
    Item(
        "en-at-any-rate", "en", "multiword",
        "Suddenly she came upon a little three-legged table, all made of solid glass; there "
        "was nothing on it except a tiny golden key, and Alice’s first thought was that it "
        "might belong to one of the doors of the hall; but, alas! either the locks were too "
        "large, or the key was too small, but at any rate it would not open any of them. "
        "However, on the second time round, she came upon a low curtain she had not noticed "
        "before, and behind it was a little door about fifteen inches high: she tried the "
        "little golden key in the lock, and to her great delight it fitted!",
        "at any rate", 1,
        "whatever the reason, in any case (a discourse phrase)",
        "at any rate",
        ALICE,
    ),
    Item(
        "en-file", "en", "cut_short",
        "The warden came in without knocking. “Where did you get the file?” he asked, pointing "
        "at the fresh scratches on the iron bars of the window. The prisoner only shrugged.",
        "file", 1,
        "a metal hand tool with a rough surface for cutting or smoothing (the prisoner used it "
        "on the bars), not a document or computer file",
        "file",
        note="the splitter cuts the question off from 'he asked, pointing at ... the iron bars'",
    ),
    Item(
        "en-bill", "en", "cut_short",
        "We spent the whole morning in the hide by the estuary. The bill measured approx. 12 "
        "cm, longer than that of any other wader on the mudflats. Nobody in our group had ever "
        "seen a curlew that large.",
        "bill", 1,
        "a bird's beak, not an invoice, banknote or law",
        "bill",
        note="the splitter cuts after 'approx.', so 'wader on the mudflats' is in the next piece",
    ),
    Item(
        "de-schloss", "de", "polysemy",
        "Als wir spät in der Nacht nach Hause kamen, wartete die nächste Überraschung auf uns. "
        "Der Schlüssel steckte zwar im Schloss, ließ sich aber keinen Millimeter drehen. "
        "Schließlich mussten wir den Schlüsseldienst rufen.",
        "Schloss", 1,
        "a door lock (das Schloss), not a castle",
        "Schloss",
    ),
    Item(
        "de-bank", "de", "polysemy",
        "Nach dem langen Spaziergang waren die Großeltern müde. Sie setzten sich auf eine Bank "
        "im Schatten der alten Linde und fütterten die Tauben. Erst gegen Abend gingen sie "
        "langsam nach Hause.",
        "Bank", 1,
        "a bench (plural Bänke), not a financial institution (plural Banken)",
        "Bank",
    ),
    Item(
        "de-leiter", "de", "repeated",
        "Am Montag regnete es durch die Decke der Werkstatt. Der Leiter der Werkstatt holte die "
        "Leiter aus dem Keller und stieg selbst aufs Dach. Nach einer Stunde war das Loch "
        "geflickt.",
        "Leiter", 2,
        "the second 'Leiter': a ladder (die Leiter), not the head or manager (der Leiter)",
        "Leiter (die)",
    ),
    Item(
        "de-haken", "de", "repeated",
        "Das Angebot klang zu gut, um wahr zu sein. Er hängte seinen Mantel an den Haken und "
        "las den Vertrag noch einmal, denn irgendwo musste die Sache doch einen Haken haben. "
        "Tatsächlich fand er ihn im Kleingedruckten.",
        "Haken", 2,
        "the second 'Haken': a catch, a hidden drawback (die Sache hat einen Haken), not a hook",
        "Haken, or the expression 'einen Haken haben'",
    ),
    Item(
        "de-aufstehen", "de", "separable",
        "Mein Bruder ist sehr diszipliniert. Er steht jeden Morgen um sieben auf, auch am "
        "Wochenende. Danach geht er eine Stunde im Park joggen.",
        "steht", 1,
        "'steht ... auf' = aufstehen, to get up (out of bed); only 'steht' was selected",
        "aufstehen",
    ),
    Item(
        "de-reinen-wein", "de", "multiword",
        "Lange hatte sie gezögert und immer neue Ausreden erfunden. Gestern hat sie ihm endlich "
        "reinen Wein eingeschenkt und alles über ihre Schulden erzählt. Er blieb erstaunlich "
        "ruhig.",
        "reinen Wein eingeschenkt", 1,
        "to tell someone the plain truth, to come clean",
        "(jemandem) reinen Wein einschenken",
    ),
    Item(
        "de-gericht", "de", "cut_short",
        "Es war schon spät, und außer uns saß niemand mehr im Saal. „Was hältst du von dem "
        "Gericht?“, fragte der Koch und stellte den dampfenden Teller vor mich hin. Ich "
        "probierte vorsichtig einen Löffel.",
        "Gericht", 1,
        "a dish, a prepared meal (das Gericht), not a court of law",
        "Gericht",
        note="the splitter cuts the question off from 'fragte der Koch und stellte den Teller hin'",
    ),
    Item(
        "de-fluegel", "de", "cut_short",
        "Die Musikschule bereitet sich auf das Jahreskonzert vor. Der Flügel steht in Zi. 12 "
        "und muss vor dem Konzert unbedingt noch gestimmt werden. Der Klavierstimmer kommt am "
        "Donnerstag.",
        "Flügel", 1,
        "a grand piano, not a wing",
        "Flügel",
        note="the splitter cuts after 'Zi.' (Zimmer), so 'noch gestimmt werden' is in the next piece",
    ),
    Item(
        "sr-grad", "sr", "polysemy",
        "Лето је почело лепо, али у среду је све кренуло наопако. Око подне је пао град "
        "величине ораха и за десет минута уништио цео воћњак. Деда после тога дуго није ни са "
        "ким разговарао.",
        "град", 1,
        "hail (precipitation), not a city",
        "град",
    ),
    Item(
        "sr-kosa", "sr", "polysemy",
        "Deda je ustao pre zore da pokosi livadu iza kuće. Uzeo je kosu iz šupe, naoštrio je "
        "brusom i polako krenuo niz brdo. Do doručka je već pokosio pola livade.",
        "kosu", 1,
        "a scythe, not hair (accusative of kosa)",
        "kosa",
    ),
    Item(
        "sr-jezik", "sr", "repeated",
        "Јутро није почело најбоље. Опекао је језик врелим чајем, па је на часу једва изговорио "
        "реченицу, иако страни језик учи већ пет година. Професорка се само насмејала.",
        "језик", 1,
        "the first 'језик': the tongue (the organ), not a language",
        "језик",
    ),
    Item(
        "sr-sat", "sr", "repeated",
        "Voz je opet kasnio. Pogledao je na sat i shvatio da na peronu čeka već ceo sat. Onda "
        "je odustao i pozvao taksi.",
        "sat", 1,
        "the first 'sat': a watch or clock (pogledati na sat), not an hour",
        "sat",
    ),
    Item(
        "sr-vratiti-se", "sr", "separable",
        "Stric Milan otišao je u Ameriku kao mladić. Posle rata se nikada nije vratio u rodno "
        "selo. Kuću je prodao preko posrednika, a pisma je slao sve ređe.",
        "vratio", 1,
        "'se ... vratio' = vratiti se, to return, come back; not 'vratiti', to give back; only "
        "'vratio' was selected",
        "vratiti se",
    ),
    Item(
        "sr-koplje", "sr", "multiword",
        "Пао је на првом испиту, а онда и на другом. Ипак, није хтео да баци копље у трње, него "
        "је цело лето учио по осам сати дневно. У септембру је положио све.",
        "баци копље у трње", 1,
        "to give up, to throw in the towel",
        "бацити копље у трње",
    ),
    Item(
        "sr-luk", "sr", "cut_short",
        "Lovci su se spremali za polazak pre svitanja. „Gde si stavio luk?“ upitao je stariji "
        "brat, tražeći strele po šatoru. Mlađi je samo slegnuo ramenima.",
        "luk", 1,
        "a bow (the weapon), not an onion",
        "luk",
        note="the splitter cuts the question off from 'upitao je ... tražeći strele po šatoru'",
    ),
    Item(
        "sr-kljuc", "sr", "cut_short",
        "Сваког лета бака нас је водила у манастир изнад села. Код кључа поред цркве св. Петке "
        "мештани и данас пуне флаше водом за коју верују да лечи очи. Ми деца смо се највише "
        "радовали сладоледу у порти.",
        "кључа", 1,
        "a spring, a place where water comes out of the ground (genitive of кључ), not a key",
        "кључ",
        note="the splitter cuts after 'св.', so the water is in the next piece",
    ),
]
ITEMS_BY_ID = {item.id: item for item in ITEMS}

IN_DEPTH_ITEMS = ["en-fine", "en-make-out", "de-schloss", "de-aufstehen", "sr-grad", "sr-vratiti-se"]


@dataclass(frozen=True)
class Context:
    content: str
    term_word_ids: list[int]
    word: str
    sentence: str
    marked: str


def _django() -> None:
    os.environ.setdefault("LEXIFLUX_ENV", "local")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "lexiflux.environments")
    sys.path.insert(0, str(REPO))
    import django  # noqa: PLC0415

    django.setup()


def page_content(item: Item) -> str:
    return f"<p>{html.escape(item.passage, quote=False)}</p>"


def build_context(item: Item) -> Context:
    """What the production code derives from a page and a selection, per arm."""
    from lexiflux.language import llm as llm_module  # noqa: PLC0415
    from lexiflux.language.parse_html_text_content import extract_content_from_html  # noqa: PLC0415
    from lexiflux.language.sentence_extractor import break_into_sentences  # noqa: PLC0415
    from lexiflux.language.word_extractor import parse_words  # noqa: PLC0415

    content = page_content(item)
    words, _ = parse_words(content, lang_code=item.lang)
    _, mapping = break_into_sentences(content, words, lang_code=item.lang)
    term_word_ids = _selection_ids(item, content, words)

    page = SimpleNamespace(content=content, words=words, word_sentence_mapping=mapping)
    book = SimpleNamespace(code=item.id)
    hashable = (
        ("book_code", item.id),
        ("book_page_number", 1),
        ("term_word_ids", tuple(term_word_ids)),
    )
    # mark_term_and_sentence reads the page from the DB; hand it this in-memory page instead.
    with (
        mock.patch.object(llm_module, "Book", SimpleNamespace(objects=SimpleNamespace(get=lambda **_: book))),
        mock.patch.object(
            llm_module,
            "BookPage",
            SimpleNamespace(objects=SimpleNamespace(get=lambda **_: page)),
        ),
    ):
        marked_html = llm_module.Llm.mark_term_and_sentence(
            llm_module.Llm.__new__(llm_module.Llm),
            hashable,
            context_words=CONTEXT_WORDS,
        )
    marked = extract_content_from_html(marked_html)

    first_sentence, last_sentence = mapping[term_word_ids[0]], mapping[term_word_ids[-1]]
    sentence_ids = [w for w, s in mapping.items() if first_sentence <= s <= last_sentence]
    sentence = extract_content_from_html(
        content[words[min(sentence_ids)][0] : words[max(sentence_ids)][1]],
    )
    word = extract_content_from_html(content[words[term_word_ids[0]][0] : words[term_word_ids[-1]][1]])
    return Context(content, term_word_ids, word, sentence, marked)


def _selection_ids(item: Item, content: str, words: list[tuple[int, int]]) -> list[int]:
    tokens = item.selection.split()
    surfaces = [html.unescape(content[s:e]) for s, e in words]
    found = 0
    for start in range(len(surfaces) - len(tokens) + 1):
        if surfaces[start : start + len(tokens)] == tokens:
            found += 1
            if found == item.occurrence:
                return list(range(start, start + len(tokens)))
    raise ValueError(f"{item.id}: selection {item.selection!r} #{item.occurrence} not found")


def _template(name: str) -> str:
    return (PROMPTS / name).read_text(encoding="utf-8")


def build_messages(arm: str, item: Item, ctx: Context) -> list[dict]:
    if arm == "A":
        system = (
            (REPO / "lexiflux" / "resources" / "prompts" / "AI dictionary.txt")
            .read_text(encoding="utf8")
            .strip()
            # Production passes Google codes here, not names (lexical_views.get_lexical_article).
            .format(text_language=item.lang, user_language=USER_LANG)
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": f"The text is: {ctx.marked}"},
        ]
    names = {"text_language": LANG_NAMES[item.lang], "user_language": LANG_NAMES[USER_LANG]}
    if arm == "B":
        prompt = _template("AI dictionary.B.txt").format(text=ctx.marked, **names)
    elif arm == "C":
        prompt = _template("AI dictionary.C.txt").format(word=ctx.word, sentence=ctx.sentence, **names)
    elif arm in IN_DEPTH_PROMPTS:
        prompt = _template(IN_DEPTH_PROMPTS[arm]).format(word=ctx.word, sentence=ctx.sentence, **names)
    else:
        raise ValueError(arm)
    return [{"role": "user", "content": prompt}]


def remove_marks(text: str) -> str:
    """The current TextOutputParser: what production strips from an answer to a marked prompt."""
    for mark in MARKS:
        text = text.replace(mark, "")
    return text


_TAG = re.compile(r"<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9]*)([^>]*)>")
_MARKDOWN = {
    "bold": re.compile(r"\*\*[^*\n]+\*\*|__[^_\n]+__"),
    "emphasis": re.compile(r"(?<![\w*])\*(?![\s*])[^*\n]+?(?<![\s*])\*(?![\w*])"),
    "heading": re.compile(r"(?m)^\s{0,3}#{1,6}\s"),
    "code_fence": re.compile(r"```"),
    "inline_code": re.compile(r"`[^`\n]+`"),
    "md_table": re.compile(r"(?m)^\s*\|.*\|\s*$"),
}
_BULLET = re.compile(r"(?m)^\s*[-*•]\s+\S")


def contract_check(text: str, *, bound: int | None = None) -> dict[str, Any]:
    tags = _TAG.findall(text)
    bad_tags = sorted({name.lower() for _, name, _ in tags if name.lower() not in ALLOWED_TAGS})
    with_attributes = sorted(
        {name.lower() for closing, name, attrs in tags if not closing and attrs.strip().strip("/")},
    )
    markdown = sorted(kind for kind, pattern in _MARKDOWN.items() if pattern.search(text))
    leaked = [mark for mark in MARKS if mark in text]
    stripped = text.strip()
    check = {
        "ok": not bad_tags and not with_attributes and not markdown and not leaked,
        "bad_tags": bad_tags,
        "tags_with_attributes": with_attributes,
        "markdown": markdown,
        "leaked_marks": leaked,
        "bullets": bool(_BULLET.search(text)),
        # lexiflux's pane sets innerHTML with white-space: normal, so these collapse to spaces.
        "newlines": stripped.count("\n"),
        "chars": len(stripped),
    }
    if bound is not None:
        check["within_bound"] = len(stripped) <= bound
        check["ok"] = check["ok"] and check["within_bound"]
    return check


# ---------------------------------------------------------------- results file


def load(out: Path) -> dict:
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))
    return {"meta": {}, "records": []}


def save(out: Path, data: dict) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(out)


def record_key(record: dict) -> tuple[str, str, str]:
    return record["run"], record["model"], record["item"]


# ---------------------------------------------------------------- calls


async def stream_direct(http, cfg, key: str, messages: list[dict], params: dict, timeout: float) -> dict:
    """AsyncDirectClient.stream's own request and SSE reader, keeping the usage and granted
    tier that its stream drops (as echo-words' tier_screen.py does)."""
    from llmbroker.chat import (  # noqa: PLC0415
        NO_DELTA,
        aiter_chat_chunks,
        build_chat_request,
        empty_answer_error,
        parse_stream_chunk,
        provider_error,
    )
    from llmbroker.http_status import DETAIL_SNIPPET, ERROR_FLOOR  # noqa: PLC0415

    url, headers, body = build_chat_request(
        cfg.base_url, cfg.model, key, messages, stream=True, params=params,
    )
    started = time.monotonic()
    first: float | None = None
    parts: list[str] = []
    usage = None
    granted = None
    async with asyncio.timeout(timeout):
        async with http.stream("POST", url, headers=headers, json=body) as resp:
            if resp.status_code >= ERROR_FLOOR:
                detail = (await resp.aread()).decode(errors="replace")[:DETAIL_SNIPPET]
                raise provider_error(resp.status_code, detail, resp.headers)
            async for chunk in aiter_chat_chunks(resp, cfg.model):
                delta, chunk_usage = parse_stream_chunk(chunk, cfg.model)
                usage = chunk_usage or usage
                granted = chunk.get("service_tier") or granted
                if delta:
                    if first is None:
                        first = time.monotonic() - started
                    parts.append(delta)
    if not parts:
        raise empty_answer_error(cfg.model, NO_DELTA)
    return {
        "first_s": round(first, 3) if first is not None else None,
        "total_s": round(time.monotonic() - started, 3),
        "text_raw": "".join(parts),
        "usage": dataclasses.asdict(usage) if usage else None,
        "service_tier": granted,
    }


def _retry_wait(exc: Exception, attempt: int) -> float:
    retry_after = getattr(exc, "retry_after", None)
    if isinstance(retry_after, (int, float)) and retry_after > 0:
        return min(float(retry_after) + 1.0, 90.0)
    return min(10.0 * 2**attempt, 90.0)


async def call_with_retries(http, cfg, key, messages, params, *, timeout: float, attempts: int) -> dict:
    from llmbroker import AuthError  # noqa: PLC0415

    failures: list[str] = []
    for attempt in range(attempts):
        try:
            result = await stream_direct(http, cfg, key, messages, params, timeout)
            result["failed_attempts"] = failures
            return result
        except AuthError as exc:
            failures.append(f"{type(exc).__name__}: {str(exc)[:300]}")
            break
        except TimeoutError:
            failures.append(f"timeout after {timeout:.0f} s")
        except Exception as exc:  # noqa: BLE001 - a failed attempt is a recorded outcome.
            failures.append(f"{type(exc).__name__}: {str(exc)[:300]}")
            await asyncio.sleep(_retry_wait(exc, attempt))
    return {"error": failures[-1], "failed_attempts": failures}


def _prompt_text(messages: list[dict]) -> str:
    return "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages)


def _finish(record: dict, arm: str, *, bound: int | None = None) -> dict:
    if "text_raw" in record:
        text = remove_marks(record["text_raw"]) if arm in ("A", "B") else record["text_raw"]
        record["text"] = text.strip()
        record["chars"] = len(record["text"])
        record["contract"] = contract_check(record["text"], bound=bound)
        record["raw_contract"] = contract_check(record["text_raw"], bound=bound)
    return record


async def run_fixed(broker, http, data: dict, out: Path, model: str, arms: list[str], args) -> None:
    cfg, key = await broker.llms.resolve_direct(name=BENCH_PREFIX + MODELS[model])
    done = {record_key(r) for r in data["records"] if "error" not in r}
    for item in _selected_items(args):
        ctx = build_context(item)
        # A provider's periodic slow spell must not land on the same arm item after item.
        order = random.Random(f"{item.id}-{model}").sample(arms, len(arms))
        for arm in order:
            if (arm, model, item.id) in done:
                continue
            messages = build_messages(arm, item, ctx)
            result = await call_with_retries(
                http, cfg, key, messages, {}, timeout=args.timeout, attempts=args.attempts,
            )
            record = _finish(
                {
                    "run": arm,
                    "arm": arm,
                    "model": model,
                    "model_id": cfg.model,
                    "item": item.id,
                    "lang": item.lang,
                    "klass": item.klass,
                    "word": ctx.word,
                    "sentence": ctx.sentence,
                    "prompt": _prompt_text(messages),
                    "at": datetime.now(UTC).isoformat(timespec="seconds"),
                    **result,
                },
                arm,
            )
            _replace(data, record)
            save(out, data)
            _log(record)
            await asyncio.sleep(max(args.pace, PACE[model]))


async def run_pool(broker, data: dict, out: Path, args) -> None:
    from llmbroker import NoLLMAvailableError, StreamInterruptedError, StreamReplacementError  # noqa: PLC0415

    done = {record_key(r) for r in data["records"] if "error" not in r}
    for item in _selected_items(args):
        if ("pool", "pool", item.id) in done:
            continue
        ctx = build_context(item)
        messages = build_messages("C", item, ctx)
        prompt = messages[0]["content"]
        started = time.monotonic()
        first: float | None = None
        parts: list[str] = []
        record: dict[str, Any] = {}
        stream = broker.stream(prompt, operation="AI dictionary", fastest_of=2, wait=25)
        try:
            async with stream:
                async for delta in stream:
                    if delta and first is None:
                        first = time.monotonic() - started
                    parts.append(delta)
            record = {"text_raw": "".join(parts), "answered_by": stream.llm_name, "replaced": False}
        except StreamReplacementError as exc:
            record = {
                "text_raw": exc.replacement.text,
                "answered_by": exc.replacement.llm_name,
                "replaced": True,
                "streamed_by": exc.streamed_llm_name,
                "provisional_chars": len("".join(parts)),
            }
        except StreamInterruptedError as exc:
            record = {"text_raw": "".join(parts), "answered_by": exc.llm_name, "interrupted": True}
        except NoLLMAvailableError as exc:
            record = {"error": f"NoLLMAvailableError({getattr(exc, 'reason', None)}): {str(exc)[:300]}"}
        except Exception as exc:  # noqa: BLE001 - a failed call is a recorded outcome.
            record = {"error": f"{type(exc).__name__}: {str(exc)[:300]}"}
        record.update(
            {
                "first_s": round(first, 3) if first is not None else None,
                "total_s": round(time.monotonic() - started, 3),
            },
        )
        record = _finish(
            {
                "run": "pool",
                "arm": "C",
                "model": "pool",
                "model_id": record.get("answered_by"),
                "item": item.id,
                "lang": item.lang,
                "klass": item.klass,
                "word": ctx.word,
                "sentence": ctx.sentence,
                "prompt": _prompt_text(messages),
                "at": datetime.now(UTC).isoformat(timespec="seconds"),
                **record,
            },
            "C",
        )
        _replace(data, record)
        save(out, data)
        _log(record)
        await asyncio.sleep(args.pace)


async def run_in_depth(broker, http, data: dict, out: Path, args, variant: str = "in_depth") -> None:
    cfg, key = await broker.llms.resolve_direct(IN_DEPTH_ALIAS)
    done = {record_key(r) for r in data["records"] if "error" not in r}
    for item_id in IN_DEPTH_ITEMS:
        if (variant, "gpt", item_id) in done:
            continue
        item = ITEMS_BY_ID[item_id]
        ctx = build_context(item)
        messages = build_messages(variant, item, ctx)
        result = await call_with_retries(
            http, cfg, key, messages, IN_DEPTH_PARAMS, timeout=args.timeout, attempts=2,
        )
        record = _finish(
            {
                "run": variant,
                "arm": variant,
                "model": "gpt",
                "model_id": cfg.model,
                "params": IN_DEPTH_PARAMS,
                "item": item.id,
                "lang": item.lang,
                "klass": item.klass,
                "word": ctx.word,
                "sentence": ctx.sentence,
                "prompt": _prompt_text(messages),
                "at": datetime.now(UTC).isoformat(timespec="seconds"),
                **result,
            },
            variant,
            bound=IN_DEPTH_BOUND,
        )
        record["cost_usd"] = _sol_cost(record.get("usage"))
        _replace(data, record)
        save(out, data)
        _log(record)


def _sol_cost(usage: dict | None) -> float | None:
    if not usage:
        return None
    price_in, price_out = SOL_PRIORITY_PRICE
    return round(
        ((usage.get("prompt_tokens") or 0) * price_in + (usage.get("completion_tokens") or 0) * price_out)
        / 1_000_000,
        5,
    )


def _replace(data: dict, record: dict) -> None:
    key = record_key(record)
    data["records"] = [r for r in data["records"] if record_key(r) != key] + [record]


def _log(record: dict) -> None:
    status = record.get("error") or f"{record.get('chars')} chars"
    extra = f" by {record.get('answered_by')}" if record["run"] == "pool" else ""
    if record.get("replaced"):
        extra += " (replaced)"
    print(
        f"{record['item']:16} {record['run']:8} {record['model']:6} first {record.get('first_s')} "
        f"total {record.get('total_s')} {status}{extra}",
        flush=True,
    )


def _selected_items(args) -> list[Item]:
    return [ITEMS_BY_ID[i] for i in args.items] if args.items else ITEMS


def _bench_configs():
    from llmbroker import curated_pool  # noqa: PLC0415

    by_name = {cfg.name: cfg for cfg in curated_pool().configs}
    return [
        dataclasses.replace(by_name[name], name=BENCH_PREFIX + name, from_preset=False, weight=0.0)
        for name in MODELS.values()
    ]


async def run(args) -> None:
    import httpx  # noqa: PLC0415
    from llmbroker import AsyncBroker, Secrets  # noqa: PLC0415

    out = Path(args.out)
    data = load(out)
    arms = [a for a in args.arms.split(",") if a]
    home = Path(args.broker_home)
    home.mkdir(parents=True, exist_ok=True)
    direct: list = [*_bench_configs(), IN_DEPTH_ALIAS]
    data["meta"].update(
        {
            "llmbroker": _llmbroker_version(),
            "models": {model: BENCH_PREFIX + name for model, name in MODELS.items()},
            "in_depth": {"alias": IN_DEPTH_ALIAS, "params": IN_DEPTH_PARAMS},
            "context_words": CONTEXT_WORDS,
        },
    )
    broker = AsyncBroker(secrets=Secrets(REPO / ".env"), home=home, direct=direct)
    try:
        async with httpx.AsyncClient(timeout=args.timeout) as http:
            jobs = [run_fixed(broker, http, data, out, model, arms, args) for model in args.models]
            if args.in_depth:
                jobs.append(run_in_depth(broker, http, data, out, args))
            if args.in_depth_unit:
                jobs.append(run_in_depth(broker, http, data, out, args, "in_depth_unit"))
            await asyncio.gather(*jobs)
            # After the fixed runs and a minute's rest, so the pool does not share their rate limits.
            if args.pool:
                if jobs:
                    await asyncio.sleep(60)
                await run_pool(broker, data, out, args)
    finally:
        await broker.aclose()
    save(out, data)


def _llmbroker_version() -> str:
    from importlib.metadata import version  # noqa: PLC0415

    return version("llmbroker")


# ---------------------------------------------------------------- report


def _q(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def report(args) -> None:
    data = load(Path(args.out))
    groups: dict[tuple[str, str], list[dict]] = {}
    for record in data["records"]:
        groups.setdefault((record["run"], record["model"]), []).append(record)
    print(
        "| run | model | answers | errors | retried | first p50 / p90 s | whole p50 / p90 s "
        "| chars p50 / max | contract ok | multi-line | cost $ |",
    )
    print("|---" * 11 + "|")
    for (run_name, model), rows in sorted(groups.items()):
        ok = [r for r in rows if "error" not in r]
        firsts = [r["first_s"] for r in ok if r.get("first_s") is not None]
        totals = [r["total_s"] for r in ok]
        chars = [r["chars"] for r in ok]
        retried = sum(1 for r in rows if r.get("failed_attempts"))
        contract = sum(1 for r in ok if r["contract"]["ok"])
        multiline = sum(1 for r in ok if r["contract"]["newlines"])
        cost = sum(r.get("cost_usd") or 0 for r in ok)
        print(
            f"| {run_name} | {model} | {len(ok)} | {len(rows) - len(ok)} | {retried} "
            f"| {_fmt(firsts, 0.5)} / {_fmt(firsts, 0.9)} | {_fmt(totals, 0.5)} / {_fmt(totals, 0.9)} "
            f"| {statistics.median(chars) if chars else '-'} / {max(chars) if chars else '-'} "
            f"| {contract}/{len(ok)} | {multiline}/{len(ok)} | {cost:.3f} |",
        )
    pool = [r for r in data["records"] if r["run"] == "pool" and "error" not in r]
    if pool:
        by: dict[str, int] = {}
        for r in pool:
            by[str(r.get("answered_by"))] = by.get(str(r.get("answered_by")), 0) + 1
        print("\npool answered by:", by, "| replaced:", sum(1 for r in pool if r.get("replaced")))
    for record in data["records"]:
        if record["run"] in IN_DEPTH_PROMPTS and "error" not in record:
            c = record["contract"]
            heading = re.match(r"\s*<b>(.*?)</b>", record["text"])
            print(
                f"{record['run']} {record['item']}: heading {heading.group(1) if heading else None!r}, "
                f"{c['chars']} chars, within {IN_DEPTH_BOUND}: "
                f"{c['within_bound']}, tags ok: {not c['bad_tags']}, markdown: {c['markdown']}, "
                f"tier {record.get('service_tier')}, ${record.get('cost_usd')}",
            )
    for record in data["records"]:
        if "error" in record or not record["contract"]["ok"]:
            reason = record.get("error") or {
                k: v for k, v in record["contract"].items() if k in ("bad_tags", "markdown", "leaked_marks", "tags_with_attributes") and v
            }
            print(f"not ok: {record['run']} {record['model']} {record['item']}: {reason}")


def _fmt(values: list[float], share: float) -> str:
    return f"{_q(values, share):.2f}" if values else "-"


# ---------------------------------------------------------------- blind review


def _labels(rng: random.Random, count: int) -> list[str]:
    pool = [f"{letter}{digit}" for letter in "ABCDEFGHJKLMNPQRSTUVWXYZ" for digit in range(2, 10)]
    return rng.sample(pool, count)


def _config(record: dict) -> str:
    return f"{record['arm']}-{record['model']}" if record["run"] != "pool" else "C-pool"


def _shown_passage(item: Item) -> str:
    tokens = item.selection.split()
    words = list(re.finditer(r"\b\w+\b", item.passage))
    found = 0
    for start in range(len(words) - len(tokens) + 1):
        if [w.group() for w in words[start : start + len(tokens)]] == tokens:
            found += 1
            if found == item.occurrence:
                a, b = words[start].start(), words[start + len(tokens) - 1].end()
                return f"{item.passage[:a]}⟦{item.passage[a:b]}⟧{item.passage[b:]}"
    raise ValueError(item.id)


def build_review(args) -> None:
    data = load(Path(args.out))
    review = Path(args.build_review)
    review.mkdir(parents=True, exist_ok=True)
    rng = random.SystemRandom()
    answers: dict[str, list[dict]] = {}
    for record in data["records"]:
        if record["run"] in ("A", "B", "C", "pool") and "error" not in record:
            answers.setdefault(record["item"], []).append(record)
    key: dict[str, dict[str, str]] = {}
    packets: dict[str, list[dict]] = {}
    for lang in LANG_NAMES:
        items = [item for item in ITEMS if item.lang == lang]
        # Each packet gets one item of each class it can, so no reviewer sees only one kind.
        halves = [items[0::2], items[1::2]]
        for n, half in enumerate(halves, start=1):
            entries = []
            for item in half:
                records = answers.get(item.id, [])
                rng.shuffle(records)
                labels = _labels(rng, len(records))
                key[item.id] = {label: _config(r) for label, r in zip(labels, records, strict=True)}
                entries.append(
                    {
                        "word_id": item.id,
                        "source_language": LANG_NAMES[item.lang],
                        "target_language": LANG_NAMES[USER_LANG],
                        "selected": item.selection,
                        "passage": _shown_passage(item),
                        "reference": {"sense_in_passage": item.sense, "unit_to_head": item.unit},
                        "answers": [
                            {"label": label, "text": r["text"]}
                            for label, r in zip(labels, records, strict=True)
                        ],
                    },
                )
            packets[f"{lang}{n}"] = entries
    for name, entries in packets.items():
        (review / f"packet-{name}.json").write_text(
            json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8",
        )
    (review / "key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    for name, entries in packets.items():
        print(f"packet-{name}.json: {len(entries)} words, {sum(len(e['answers']) for e in entries)} answers")


# ---------------------------------------------------------------- check


def check(args) -> None:
    for item in _selected_items(args):
        ctx = build_context(item)
        print(f"== {item.id} ({item.klass}) ids {ctx.term_word_ids}")
        print(f"   word:     {ctx.word!r}")
        print(f"   sentence: {ctx.sentence!r}")
        print(f"   marked:   {ctx.marked!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arms", default="A,B,C", help="comma-separated subset of A,B,C; empty for none")
    parser.add_argument("--models", nargs="+", default=list(MODELS), choices=list(MODELS))
    parser.add_argument("--items", nargs="+", default=[], choices=list(ITEMS_BY_ID))
    parser.add_argument("--pool", action="store_true", help="also run arm C through the real pool")
    parser.add_argument("--in-depth", action="store_true", help="also run the In depth smoke on gpt")
    parser.add_argument(
        "--in-depth-unit", action="store_true", help="also run the In depth smoke with the unit sentence",
    )
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--broker-home", default=str(DEFAULT_HOME))
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--attempts", type=int, default=5)
    parser.add_argument("--pace", type=float, default=2.0, help="minimum seconds between calls")
    parser.add_argument("--check", action="store_true", help="print the derived contexts, call nothing")
    parser.add_argument("--report", action="store_true", help="summarise --out, call nothing")
    parser.add_argument("--build-review", metavar="DIR", help="write blind-review packets and key")
    args = parser.parse_args()
    _django()
    if args.check:
        check(args)
    elif args.report:
        report(args)
    elif args.build_review:
        build_review(args)
    else:
        asyncio.run(run(args))


if __name__ == "__main__":
    main()
