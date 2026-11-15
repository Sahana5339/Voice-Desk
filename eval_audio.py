"""Measure the FULL voice pipeline on recorded clips.

  python eval_audio.py audio_samples.csv            # rules only
  python eval_audio.py audio_samples.csv --hybrid   # rules + LLM (needs LLM_* in .env)

CSV columns: wav, text (what was actually said, typed by you), language, category, urgency
Reports: speech-to-text word/character error rate, ticket accuracy from the transcript (end to end), ticket accuracy
from the reference text (so you can see how much error speech-to-text adds), latency. Writes results/audio_results.*
"""
import csv
import os
import statistics
import sys

from dotenv import load_dotenv

import core
import hybrid
import syst

HERE = os.path.dirname(os.path.abspath(__file__))


def _lev(a, b):
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def _clean(s):
    s = core.norm(s)
    return "".join(ch if (ch.isalnum() or ch.isspace() or "\u0900" <= ch <= "\u0dff") else " " for ch in s).split()


def wer(ref, hyp):
    r, h = _clean(ref), _clean(hyp)
    return _lev(r, h) / max(len(r), 1)


def cer(ref, hyp):
    r, h = " ".join(_clean(ref)), " ".join(_clean(hyp))
    return _lev(list(r), list(h)) / max(len(r), 1)


def main(path, use_hybrid=False):
    load_dotenv(os.path.join(HERE, ".env"))
    key = os.environ.get("GNANI_API_KEY", "").strip()
    if not key:
        sys.exit("Add GNANI_API_KEY to .env first.")
    make = (lambda *a, **k: hybrid.make_ticket_hybrid(*a, **k)) if use_hybrid else core.make_ticket
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8")) if r.get("wav")]
    out, missing = [], 0
    for r in rows:
        wav = r["wav"] if os.path.isabs(r["wav"]) else os.path.join(HERE, r["wav"])
        if not os.path.exists(wav):
            missing += 1
            continue
        res = syst.transcribe(open(wav, "rb").read(), "indic-auto", "prisma-v3.0", key, os.path.basename(wav))
        ref = r["text"]
        tk = make(res["text"], res["lang"], 0)
        tk_ref = make(ref, None, 0)
        out.append({"wav": r["wav"], "language": r["language"], "reference": ref, "transcript": res["text"],
                    "detected": res["lang"], "wer": round(wer(ref, res["text"]), 3), "cer": round(cer(ref, res["text"]), 3),
                    "stt_ms": res["stt_ms"], "gold": f"{r['category']}/{r['urgency']}",
                    "e2e": f"{tk['category']}/{tk['urgency']}", "e2e_ok": tk["category"] == r["category"] and tk["urgency"] == r["urgency"],
                    "e2e_cat_ok": tk["category"] == r["category"],
                    "text_only_ok": tk_ref["category"] == r["category"] and tk_ref["urgency"] == r["urgency"],
                    "critical_gold": r["urgency"] == "Critical", "critical_hit": tk["urgency"] == "Critical"})
    if not out:
        sys.exit(f"No clips found ({missing} missing). Put recordings in clips/ and match the wav column.")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    with open(os.path.join(HERE, "results", "audio_results.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    n, crit = len(out), [o for o in out if o["critical_gold"]]
    lines = [f"Audio evaluation: {n} clips ({'rules + LLM' if use_hybrid else 'rules only'}), Prisma v3.0 auto-detect", "",
             "| Group | Clips | WER (mean) | CER (mean) | Category correct (e2e) | Category+urgency correct (e2e) | Same, from reference text |",
             "|---|---|---|---|---|---|---|"]
    for g in ["ALL"] + sorted({o["language"] for o in out}):
        s = [o for o in out if g == "ALL" or o["language"] == g]
        lines.append(f"| {g} | {len(s)} | {statistics.mean(o['wer'] for o in s):.1%} | {statistics.mean(o['cer'] for o in s):.1%} | "
                     f"{sum(o['e2e_cat_ok'] for o in s) / len(s):.0%} | {sum(o['e2e_ok'] for o in s) / len(s):.0%} | "
                     f"{sum(o['text_only_ok'] for o in s) / len(s):.0%} |")
    if crit:
        lines += ["", f"Critical (fraud/safety) recall from speech: {sum(o['critical_hit'] for o in crit)}/{len(crit)}"]
    lines += ["", f"Median speech-to-text latency: {statistics.median(o['stt_ms'] for o in out):.0f} ms"]
    if missing:
        lines.append(f"({missing} listed clips were not found and were skipped.)")
    text = "\n".join(lines)
    open(os.path.join(HERE, "results", "audio_results.md"), "w", encoding="utf-8").write(text + "\n")
    print(text)
    for o in out:
        if not o["e2e_ok"]:
            print("MISS", o["language"], "| said:", o["reference"], "| heard:", o["transcript"], "|", o["e2e"], "vs", o["gold"])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1], "--hybrid" in sys.argv)
