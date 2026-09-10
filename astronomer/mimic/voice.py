"""Voice loop: evolve prompt-populations that write like astro (cg evo pattern).

Individual = system prompt. Fitness (deterministic, scored locally):
  numbers_present (has $/levels) + direction_match + struct_score (shape filter)
  + jaccard(actual). Hermes (:11434) generates; harness scores; elites mutate.
Usage: cd astronomer && python3 -m mimic.voice --pilot   # 4 prompts x 5 posts
       python3 -m mimic.voice --gen0                    # 4 x 12, then mutate->gen1
"""
import argparse
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OLLAMA = "http://127.0.0.1:11434/api/generate"

PROMPTS = {
    "terse": "You are a crypto trader posting on X. Write ONE short post (under 280 chars): asset with $, direction (long/short), one entry level, one target. Terse. No hashtags. No disclaimer.",
    "astro-verbose": "You are a crypto trader posting on X. Write a post like a market update: $BTC first, then 2-4 short paragraphs separated by blank lines. State your positioning (long/short), key levels with numbers, what would change your mind. Confident, direct, uses 'Alright' sparingly. No hashtags.",
    "levels-first": "You are a crypto trader posting on X. Lead with exact numbers: entry, target, invalidation with $ and k formatting. Then one line of reasoning. Then what invalidates. Under 400 chars total.",
    "conditional": "You are a crypto trader posting on X. Write a conditional setup post: IF price does X THEN you will do Y, with the invalidation that kills the idea. Include $asset and at least two numbers. Under 300 chars.",
}

DIRW = re.compile(r"(?i)\b(long|short|buy|sell|bullish|bearish)\b")
NUMW = re.compile(r"\$?\d[\d,\.]*k?\b")


def generate(sys_prompt, context, timeout=120):
    body = json.dumps({"model": "hermes3:8b",
                       "system": sys_prompt,
                       "prompt": context,
                       "stream": False,
                       "options": {"num_predict": 140, "temperature": 0.7}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r).get("response", "")


def struct_score(text):
    t = (text or "").lower()
    s = 0.0
    s += 0.4 if re.search(r"\$[a-z]{2,10}\b", t) else 0.0
    s += 0.3 if len(re.findall(r"\d[\d,\.]*k?\b", t)) >= 2 else 0.0
    s += 0.2 if 80 <= len(t) <= 500 else 0.0
    s += 0.1 if "#" not in t else 0.0
    return s


def direction_of(text):
    t = (text or "").lower()
    longs = len(re.findall(r"\b(long|buy|bullish)\b", t))
    shorts = len(re.findall(r"\b(short|sell|bearish)\b", t))
    if longs == shorts:
        return None
    return "BULLISH" if longs > shorts else "BEARISH"


def fitness(gen, actual_text, actual_dir):
    tok = lambda s: set(re.findall(r"[a-z0-9$]+", (s or "").lower()))
    j = len(tok(gen) & tok(actual_text)) / max(1, len(tok(gen) | tok(actual_text)))
    gd = direction_of(gen)
    return {"numbers": 1.0 if len(NUMW.findall(gen or "")) >= 2 else 0.0,
            "direction": 1.0 if (gd and gd == actual_dir) else 0.0,
            "struct": struct_score(gen), "jaccard": round(j, 3)}


def load_sample(n):
    rows = json.load(open(os.path.join(ROOT, "astronomer", "data", "core3", "normalized",
                                       "all_outcomes_EXPANDED.json")))
    a = [o for o in rows if o.get("author_handle") == "astronomer_zero" and o.get("return_24h") is not None]
    ev = {}
    for l in open(os.path.join(ROOT, "astronomer", "data", "core3", "normalized",
                               "astronomer_zero_events.jsonl")):
        try:
            r = json.loads(l)
            ev[r["event_id"]] = r
        except Exception:
            pass
    out = []
    for o in a[-n:]:
        r = ev.get(o["event_id"], {})
        out.append({"direction": o.get("direction"), "asset": o.get("asset", "BTC"),
                    "text": r.get("text", ""), "published_at": r.get("published_at", "")})
    return out


def score_prompt(name, sys_prompt, sample):
    fits = []
    for s in sample:
        ctx = (f"Market: {s['asset']} call, model lean {s['direction']}, "
               f"date {s['published_at'][:10]}. Write the trader's post.")
        try:
            gen = generate(sys_prompt, ctx)
        except Exception as e:
            gen = ""
        f = fitness(gen, s["text"], s["direction"])
        f["total"] = round(0.3 * f["numbers"] + 0.3 * f["direction"] + 0.2 * f["struct"] + 0.2 * f["jaccard"], 3)
        fits.append(f)
    agg = {k: round(sum(f[k] for f in fits) / max(1, len(fits)), 3) for k in ("numbers", "direction", "struct", "jaccard", "total")}
    agg["n"] = len(fits)
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--gen0", action="store_true")
    a = ap.parse_args()
    n = 5 if a.pilot else 12
    sample = load_sample(n)
    print(f"sample: {len(sample)} astro posts", flush=True)
    results = {}
    outp = os.path.join(ROOT, "astronomer", "data", "mimic_trials",
                        f"voice_{'pilot' if a.pilot else 'gen0'}.json")
    for name, sys_prompt in PROMPTS.items():
        agg = score_prompt(name, sys_prompt, sample)
        results[name] = agg
        print(f"  {name}: total={agg['total']} num={agg['numbers']} dir={agg['direction']} struct={agg['struct']} jac={agg['jaccard']}", flush=True)
        json.dump(results, open(outp, "w"), indent=1)
        json.dump(results, open(outp, "w"), indent=1)
        print(f"saved -> {outp}", flush=True)


if __name__ == "__main__":
    main()
