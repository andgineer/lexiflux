"""Join the blind verdicts of the context bench with the key and the timing records, and apply
Phase 1's decision rule (specs/plans/20260922-llmbroker-migration.md).

    source ./activate.sh && python experiments/context_bench_aggregate.py
    source ./activate.sh && python experiments/context_bench_aggregate.py --serious

Rule: ship C unless B beats it on context-sense hits or on serious errors with a 95% paired
bootstrap interval that excludes zero, pairs being item x fixed model. If B's win disappears
once the repeated-word class is left out, B wins only on that class: ship C and add the
occurrence index to the prompt as a follow-up. A vs B is reported as the prompt change alone.
"""

import argparse
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIXED_MODELS = ("gemini", "groq")
REPEATED = "repeated"
LANGS = ("en", "de", "sr")


def load_verdicts(review: Path, key: dict[str, dict[str, str]]) -> tuple[dict, dict, list[str]]:
    """(config, word) -> verdict row, config -> ranks, and every problem found on the way."""
    rows: dict[tuple[str, str], dict] = {}
    ranks: dict[str, list[int]] = defaultdict(list)
    problems: list[str] = []
    for path in sorted(review.glob("verdict-*.jsonl")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            line = line.strip()
            if not line.startswith("{"):
                continue
            where = f"{path.name}:{number}"
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                problems.append(f"{where}: not JSON ({exc})")
                continue
            word = row.get("word")
            if word not in key:
                problems.append(f"{where}: unknown word {word!r}")
                continue
            if "ranking" in row:
                for position, label in enumerate(row["ranking"], start=1):
                    if label in key[word]:
                        ranks[key[word][label]].append(position)
                continue
            label = row.get("label")
            if label not in key[word]:
                problems.append(f"{where}: unknown label {label!r} for {word}")
                continue
            missing = [f for f in ("score", "context_sense", "lemma", "serious", "contract") if f not in row]
            if missing:
                problems.append(f"{where}: {word}/{label} lacks {missing}")
                continue
            row = normalise(row)
            if row is None:
                problems.append(f"{where}: {word}/{label} has an unreadable score")
                continue
            config = key[word][label]
            if (config, word) in rows:
                problems.append(f"{where}: {word}/{label} scored twice; the later line is used")
            rows[(config, word)] = row
    expected = {(config, word) for word, labels in key.items() for config in labels.values()}
    for config, word in sorted(expected - set(rows)):
        problems.append(f"unscored: {word} {config}")
    return rows, ranks, problems


def _yes(value: object) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() in ("yes", "true", "y"))


def normalise(row: dict) -> dict | None:
    """Booleans and a numeric score, whichever way a reviewer spelled them."""
    try:
        score = int(float(row["score"]))
    except (TypeError, ValueError):
        return None
    serious = row.get("serious") or []
    return {
        **row,
        "score": score,
        "context_sense": _yes(row["context_sense"]),
        "lemma": _yes(row["lemma"]),
        "contract": _yes(row["contract"]),
        "serious": serious if isinstance(serious, list) else [serious],
    }


def load_bench(path: Path) -> tuple[dict[str, dict], dict[str, list[dict]]]:
    """Item metadata by id, and the timing records by config."""
    data = json.loads(path.read_text(encoding="utf-8"))
    items: dict[str, dict] = {}
    by_config: dict[str, list[dict]] = defaultdict(list)
    for record in data["records"]:
        items.setdefault(record["item"], {"lang": record["lang"], "klass": record["klass"]})
        if record["run"] == "pool":
            by_config["C-pool"].append(record)
        elif record["run"] in ("A", "B", "C"):
            by_config[f"{record['arm']}-{record['model']}"].append(record)
    return items, by_config


def q(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))]


def fmt_q(values: list[float]) -> str:
    return f"{q(values, 0.5):.2f} / {q(values, 0.9):.2f}" if values else "-"


def config_order(config: str) -> tuple[str, int]:
    arm, model = config.split("-", 1)
    return arm, (FIXED_MODELS + ("pool",)).index(model) if model in FIXED_MODELS + ("pool",) else 9


def config_table(rows: dict, ranks: dict, items: dict, timings: dict) -> None:
    configs = sorted({config for config, _ in rows} | set(timings), key=config_order)
    print(
        "| config | scored | mean /5 | en | de | sr | serious | context-sense | lemma | contract "
        "| mechanical contract | avg rank | first delta p50 / p90 s | whole p50 / p90 s "
        "| chars p50 | call errors |",
    )
    print("|---" * 16 + "|")
    for config in configs:
        mine = [(word, row) for (c, word), row in rows.items() if c == config]
        by_lang = [
            _mean([row["score"] for word, row in mine if items.get(word, {}).get("lang") == lang])
            for lang in LANGS
        ]
        records = timings.get(config, [])
        ok = [r for r in records if "error" not in r]
        firsts = [r["first_s"] for r in ok if r.get("first_s") is not None]
        wholes = [r["total_s"] for r in ok]
        chars = [r["chars"] for r in ok]
        cells = [
            config,
            str(len(mine)),
            _mean([row["score"] for _, row in mine]),
            *by_lang,
            str(sum(len(row["serious"] or []) for _, row in mine)),
            _hits(mine, "context_sense"),
            _hits(mine, "lemma"),
            _hits(mine, "contract"),
            f"{sum(1 for r in ok if r['contract']['ok'])}/{len(ok)}",
            f"{statistics.mean(ranks[config]):.1f}" if ranks.get(config) else "-",
            fmt_q(firsts),
            fmt_q(wholes),
            f"{statistics.median(chars):.0f}" if chars else "-",
            str(len(records) - len(ok)),
        ]
        print("| " + " | ".join(cells) + " |")


def _mean(values: list[float]) -> str:
    return f"{statistics.mean(values):.2f}" if values else "-"


def _hits(mine: list[tuple[str, dict]], field: str) -> str:
    return f"{sum(1 for _, row in mine if row[field] is True)}/{len(mine)}"


def pairs(  # noqa: PLR0913 - the filters, one keyword each
    rows: dict,
    items: dict,
    better: str,
    worse: str,
    klass: str | None = None,
    *,
    exclude: str | None = None,
    model: str | None = None,
) -> list[dict]:
    """Per item x fixed model: (better - worse) context-sense hit, (worse - better) serious
    errors and (better - worse) score, so every difference is positive where `better` wins."""
    out = []
    for word, meta in sorted(items.items()):
        if klass is not None and meta["klass"] != klass:
            continue
        if exclude is not None and meta["klass"] == exclude:
            continue
        for fixed in FIXED_MODELS:
            if model is not None and fixed != model:
                continue
            b = rows.get((f"{better}-{fixed}", word))
            w = rows.get((f"{worse}-{fixed}", word))
            if b is None or w is None:
                continue
            out.append(
                {
                    "context_sense": int(b["context_sense"] is True) - int(w["context_sense"] is True),
                    "serious": len(w["serious"] or []) - len(b["serious"] or []),
                    "score": b["score"] - w["score"],
                },
            )
    return out


def bootstrap(diffs: list[float], n_boot: int, rng: random.Random) -> tuple[float, float, float]:
    if not diffs:
        return float("nan"), float("nan"), float("nan")
    means = sorted(statistics.fmean(rng.choices(diffs, k=len(diffs))) for _ in range(n_boot))
    return statistics.fmean(diffs), means[int(0.025 * n_boot)], means[int(0.975 * n_boot) - 1]


def wins(ps: list[dict], n_boot: int, rng: random.Random) -> dict[str, tuple[float, float, float]]:
    return {metric: bootstrap([p[metric] for p in ps], n_boot, rng) for metric in ("context_sense", "serious", "score")}


def excludes_zero_positive(ci: tuple[float, float, float]) -> bool:
    return ci[1] > 0


def show(title: str, result: dict, n: int) -> None:
    cells = " | ".join(f"{m[0]:+.3f} [{m[1]:+.3f}, {m[2]:+.3f}]" for m in result.values())
    print(f"| {title} | {n} | {cells} |")


def decision(rows: dict, items: dict, n_boot: int, seed: int) -> None:
    rng = random.Random(seed)
    classes = sorted({meta["klass"] for meta in items.values()})
    header = (
        "| comparison | pairs | context-sense hits, mean diff [95% CI] "
        "| serious errors, mean diff [95% CI] | score, mean diff [95% CI] |"
    )
    for better, worse, title in (("B", "C", "B over C"), ("B", "A", "B over A (the prompt change alone)")):
        print(f"\n### {title}: positive = {better} better\n")
        print(header)
        print("|---" * 5 + "|")
        overall = pairs(rows, items, better, worse)
        show("all", wins(overall, n_boot, rng), len(overall))
        for klass in classes:
            ps = pairs(rows, items, better, worse, klass)
            show(klass, wins(ps, n_boot, rng), len(ps))
        for model in FIXED_MODELS:
            ps = pairs(rows, items, better, worse, model=model)
            show(f"model {model}", wins(ps, n_boot, rng), len(ps))

    overall_ps = pairs(rows, items, "B", "C")
    if not overall_ps:
        print("\nDecision: no B/C pairs scored yet.")
        return
    overall = wins(overall_ps, n_boot, rng)
    b_wins = [m for m in ("context_sense", "serious") if excludes_zero_positive(overall[m])]
    repeated = wins(pairs(rows, items, "B", "C", REPEATED), n_boot, rng)
    repeated_wins = [m for m in ("context_sense", "serious") if excludes_zero_positive(repeated[m])]
    print("\n### Decision\n")
    if not b_wins:
        print("B does not beat C on context-sense hits or serious errors (both intervals include zero "
              "or favour C): **ship C**.")
        if repeated_wins:
            print(f"Within the repeated-word class alone B is ahead on {', '.join(repeated_wins)}: "
                  "add the occurrence index (e.g. `the second \"saw\"`) to the prompt as a follow-up.")
        return
    rest = wins(pairs(rows, items, "B", "C", exclude=REPEATED), n_boot, rng)
    rest_wins = [m for m in ("context_sense", "serious") if excludes_zero_positive(rest[m])]
    print(f"B beats C overall on {', '.join(b_wins)}.")
    print(f"Without the repeated-word class: B ahead on {', '.join(rest_wins) or 'nothing'} "
          + ", ".join(f"{m} {rest[m][0]:+.3f} [{rest[m][1]:+.3f}, {rest[m][2]:+.3f}]" for m in ("context_sense", "serious")))
    if rest_wins:
        print("B's win does not rest on the repeated-word class alone: **ship B**.")
    else:
        print("B wins only on the repeated-word class: **ship C and add the occurrence index** "
              "(e.g. `the second \"saw\"`) to the prompt as a follow-up.")


def serious_list(rows: dict) -> None:
    by_config: dict[str, list[str]] = defaultdict(list)
    for (config, word), row in sorted(rows.items()):
        for item in row["serious"] or []:
            by_config[config].append(f"{word}: {item.get('quote', '')[:100]!r} — {item.get('why', '')}")
    for config in sorted(by_config, key=config_order):
        print(f"\n#### {config}")
        for line in by_config[config]:
            print(" -", line)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--review", default=str(REPO / "experiments" / ".context-bench" / "review"))
    parser.add_argument("--bench", default=str(REPO / "experiments" / "context_bench.json"))
    parser.add_argument("--boot", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--serious", action="store_true", help="list every serious error")
    args = parser.parse_args()

    review = Path(args.review)
    key = json.loads((review / "key.json").read_text(encoding="utf-8"))
    rows, ranks, problems = load_verdicts(review, key)
    items, timings = load_bench(Path(args.bench))
    if problems:
        print(f"## Problems ({len(problems)})\n")
        for problem in problems[:60]:
            print(" -", problem)
        print()
    if not rows:
        sys.exit("no verdicts found")
    print("## Per arm and model\n")
    config_table(rows, ranks, items, timings)
    print("\n## Per-class counts (context-sense hits / serious errors / mean score)\n")
    class_table(rows, items)
    print("\n## Decision rule")
    decision(rows, items, args.boot, args.seed)
    if args.serious:
        print("\n## Serious errors")
        serious_list(rows)


def class_table(rows: dict, items: dict) -> None:
    classes = sorted({meta["klass"] for meta in items.values()})
    configs = sorted({config for config, _ in rows}, key=config_order)
    print("| config | " + " | ".join(classes) + " |")
    print("|---" * (len(classes) + 1) + "|")
    for config in configs:
        cells = []
        for klass in classes:
            mine = [row for (c, word), row in rows.items() if c == config and items.get(word, {}).get("klass") == klass]
            if not mine:
                cells.append("-")
                continue
            hits = sum(1 for row in mine if row["context_sense"] is True)
            serious = sum(len(row["serious"] or []) for row in mine)
            cells.append(f"{hits}/{len(mine)} / {serious} / {statistics.mean(r['score'] for r in mine):.2f}")
        print(f"| {config} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
