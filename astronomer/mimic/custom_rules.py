"""Custom extractor rules for Chase/DrProfit/CrypNuevo formats the generic
extractor misses. Each rule returns (direction, asset, entry, target) or None.
Conservative by design: needs asset + directional verb + number in one post.
Usage: cd astronomer && python3 -m mimic.custom_rules
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSET = re.compile(r"\$([A-Z]{2,10})\b")
NUM = re.compile(r"\$?(\d[\d,\.]*)\s?k?\b", re.IGNORECASE)


def num(s):
    try:
        v = float(s.replace(",", ""))
        if 1900 <= v <= 2100 and len(s.replace(",", "").split(".")[0]) == 4:
            return None  # years, not levels
        return v * 1000 if v < 1000 and "k" in s.lower() else v
    except ValueError:
        return None


SHORT_CTX = re.compile(r"(?i)\b(shorted|shorting|went short|big short|short position|bearish|to the downside)\b")
LONG_CTX = re.compile(r"(?i)\b(bought|buying|went long|big long|long position|bullish|accumulat)\b")
SKIP_CTX = re.compile(r"(?i)\b(since|in the year|year|called|episode|report|part|MA)\s*\d")


def resolve_dir(tx, fallback):
    lo = len(LONG_CTX.findall(tx))
    sh = len(SHORT_CTX.findall(tx))
    if sh > lo:
        return "BEARISH" if fallback == "BULLISH" else fallback
    return fallback


def assets(tx):
    return list(dict.fromkeys(m.upper() for m in ASSET.findall(tx)))


URL = re.compile(r"https?://\S+")
MONTH = re.compile(r"(?i)\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b")


TEMPORAL = re.compile(r"(?i)\b(since|year|called|episode|report|part|before|after|during|past|prior|from|until|through)\b")
# NOTE: "at"/"in" deliberately EXCLUDED — they precede real entries ("entered at $64k").


def nums(tx):
    tx = URL.sub(" ", tx)
    out = []
    for m in NUM.finditer(tx):
        start = m.start()
        pre = tx[max(0, start - 15):start]
        digits = m.group(0)
        # 4-digit years are never trade levels unless $/k-marked
        if re.fullmatch(r"\d{4}", digits) and not m.group(0).startswith("$"):
            window = tx[max(0, start - 20):m.end() + 20]
            if TEMPORAL.search(window) or MONTH.search(window):
                continue
        lastw = (pre.strip().split() or [""])[-1]
        if TEMPORAL.search(lastw) or re.search(r"(?i)\bMA$", pre):
            continue
        if MONTH.search(pre) or MONTH.search(tx[m.end():m.end() + 12]):
            continue
        if tx[m.end():m.end() + 2].strip().startswith("%"):
            continue  # percentages aren't price levels
        nxt = tx[m.end():m.end() + 12]
        if re.match(r"\s?(hours?|hrs|days?|minutes?|seconds?|weeks?|months?|years?)\b", nxt, re.IGNORECASE):
            continue  # durations aren't levels
        if re.search(r"(?i)(s&p|spx|qqq|dji|index)\s*$", pre):
            continue  # index names, not prices
        if re.search(r"#\s*$", pre):
            continue  # rankings (#1, #2...), not levels
        if re.search(r"(?i)(more than|over|under|about|around|nearly|almost|~)\s*$", pre) and \
           re.search(r"(?i)^\s*(altcoin|trade|short|account|wallet|post|people|trader|follower)", tx[m.end():m.end() + 20]):
            continue  # counts ("more than 100 altcoins"), not levels
        if re.search(r"(?i)^\s*(billion|million|trillion)\b", tx[m.end():m.end() + 14]):
            continue  # magnitudes ("5 billion"), not levels
        if re.search(r"(?i)^\s*(percent|pct|purchases|trades)\b", tx[m.end():m.end() + 14]):
            continue  # counts/percents, not levels
        if re.search(r"\+\s?(altcoin|trade|account|post|wallet)", tx[m.end():m.end() + 20], re.IGNORECASE):
            continue
        v = num(m.group(0))
        if v and v > 0:
            out.append(v)
    return out


def rule_buy_around(tx):
    """'interested/buy/bid around X' + $ASSET -> BULLISH, entry X.
    X must sit NEAR the trigger phrase (long essays contain dozens of stray
    numbers — first-surviving-number-wins was systematically wrong)."""
    m = re.search(r"(?i)\b(interested|buy|buying|bid|bidding|chance to buy|looking to buy)\b.{0,60}(around|at|near|@)", tx)
    if not m:
        return None
    lo, hi = max(0, m.start() - 20), m.end() + 60
    window = tx[lo:hi]
    a = assets(tx)
    # numbers near trigger, reusing all guards
    saved = []
    for mm in NUM.finditer(window):
        sub = window  # run guard logic on window-relative match
        pre = window[max(0, mm.start() - 15):mm.start()]
        post = window[mm.end():mm.end() + 20]
        if TEMPORAL.search((pre.strip().split() or [""])[-1]) or re.search(r"(?i)\bMA$", pre):
            continue
        if MONTH.search(pre) or MONTH.search(window[mm.end():mm.end() + 12]):
            continue
        if re.match(r"\s?%", window[mm.end():mm.end() + 2]) or \
           re.match(r"\s?(hours?|hrs|days?|minutes?|seconds?|weeks?|months?|years?)\b", window[mm.end():], re.IGNORECASE):
            continue
        if re.search(r"(?i)(s&p|spx|qqq|dji|index)\s*$", pre) or re.search(r"#\s*$", pre):
            continue
        dg = mm.group(0).strip()
        if re.fullmatch(r"\$?\d{4}[.,;:!]?", dg) and not dg.startswith("$"):
            # bare 4-digit: year ONLY if temporal/month context in FULL text ±40
            # (window edges truncate month names — never decide on truncated context)
            abspos = lo + mm.start()
            wide = tx[max(0, abspos - 40):abspos + 44]
            if TEMPORAL.search(wide) or MONTH.search(wide):
                continue
        if re.search(r"(?i)(more than|over|under|about|around|nearly|almost|~)\s*$", pre) and \
           re.search(r"(?i)^\s*(altcoin|trade|short|account|wallet|post|people|trader|follower)", post):
            continue
        if re.search(r"(?i)^\s*(billion|million|trillion)\b", post):
            continue
        if re.search(r"(?i)^\s*(percent|pct|purchases|trades)\b", post):
            continue
        v = num(dg)
        if v and v > 0:
            saved.append((abs(mm.start() - (m.end() - lo)), v))
    if a and saved:
        saved.sort()
        return (resolve_dir(tx, "BULLISH"), a[0], saved[0][1], None)
    return None


def rule_move_to(tx):
    """'move/run/headed to $X' + $ASSET -> BULLISH, target X."""
    m = re.search(r"(?i)\b(move|run|headed|heading|going) (to|toward[s]?)\s+\$?([\d,\.]+k?)\b", tx)
    if m:
        a = assets(tx)
        v = num(m.group(3))
        if a and v:
            return ("BULLISH", a[0], None, v)
    return None


def rule_ath(tx):
    """'expecting new all-time highs' + $ASSET -> BULLISH."""
    if re.search(r"(?i)(new all-time highs|new ATH|all time high)", tx):
        a = assets(tx)
        if a:
            return ("BULLISH", a[0], None, None)
    return None


def rule_ready_for(tx):
    """'Who is ready for $X' + $ASSET -> BULLISH, target X."""
    m = re.search(r"(?i)ready for\s+\$?([\d,\.]+k?)\b", tx)
    if m:
        a = assets(tx)
        v = num(m.group(1))
        if a and v:
            return ("BULLISH", a[0], None, v)
    return None


def rule_full_tp(tx):
    """'Full TP here at X' -> EXIT with price."""
    m = re.search(r"(?i)\bfull TP (here )?at\s+\$?([\d,\.]+k?)\b", tx)
    if m:
        a = assets(tx)
        v = num(m.group(2))
        if a and v:
            return ("EXIT", a[0], None, v)
    return None


def rule_short_around(tx):
    """Mirror of buy_around: 'short(ing) (here|around|into) X' + $ASSET -> BEARISH.
    Short language previously fell through (resolve_dir only flips BULLISH hits)."""
    m = re.search(r"(?i)\b(short|shorting|shorted|redistribut\w*|fade|fadeing)\b.{0,60}(around|at|near|@|into|here)\b", tx)
    if not m:
        return None
    lo, hi = max(0, m.start() - 20), m.end() + 60
    window = tx[lo:hi]
    a = assets(tx)
    saved = []
    for mm in NUM.finditer(window):
        pre = window[max(0, mm.start() - 15):mm.start()]
        post = window[mm.end():mm.end() + 20]
        if TEMPORAL.search((pre.strip().split() or [""])[-1]) or re.search(r"(?i)\bMA$", pre):
            continue
        if MONTH.search(pre) or MONTH.search(window[mm.end():mm.end() + 12]):
            continue
        if re.match(r"\s?%", window[mm.end():mm.end() + 2]) or \
           re.match(r"\s?(hours?|hrs|days?|minutes?|seconds?|weeks?|months?|years?)\b", window[mm.end():], re.IGNORECASE):
            continue
        if re.search(r"(?i)(s&p|spx|qqq|dji|index)\s*$", pre) or re.search(r"#\s*$", pre):
            continue
        dg = mm.group(0).strip()
        if re.fullmatch(r"\$?\d{4}[.,;:!]?", dg) and not dg.startswith("$"):
            abspos = lo + mm.start()
            wide = tx[max(0, abspos - 40):abspos + 44]
            if TEMPORAL.search(wide) or MONTH.search(wide):
                continue
        if re.search(r"(?i)(more than|over|under|about|around|nearly|almost|~)\s*$", pre) and \
           re.search(r"(?i)^\s*(altcoin|trade|short|account|wallet|post|people|trader|follower)", post):
            continue
        if re.search(r"(?i)^\s*(billion|million|trillion)\b", post):
            continue
        if re.search(r"(?i)^\s*(percent|pct|purchases|trades)\b", post):
            continue
        v = num(dg)
        if v and v > 0:
            saved.append((abs(mm.start() - (m.end() - lo)), v))
    if a and saved:
        saved.sort()
        return ("BEARISH", a[0], saved[0][1], None)
    return None


RULES = [rule_buy_around, rule_short_around, rule_move_to, rule_ath, rule_ready_for, rule_full_tp]


def apply(text):
    for fn in RULES:
        r = fn(text or "")
        if r:
            return {"rule": fn.__name__, "direction": r[0], "asset": r[1],
                    "entry": r[2], "target": r[3]}
    return None


def main():
    hits = []
    for h in ["Crypto_Chase", "DrProfitCrypto", "CrypNuevo"]:
        for suf in ("_aug2026", "_jul2026"):
            p = os.path.join(ROOT, "astronomer", "data", "backtest", "raw", f"{h}{suf}.json")
            if not os.path.exists(p):
                continue
            for t in json.load(open(p)):
                r = apply(t.get("text", ""))
                if r:
                    r.update({"handle": h, "post_id": str(t.get("id")),
                              "published_at": t.get("createdAt", "")})
                    hits.append(r)
    from collections import Counter
    print(f"custom-rule hits: {len(hits)} {dict(Counter((x['handle'], x['rule']) for x in hits))}")
    json.dump(hits, open(os.path.join(ROOT, "astronomer", "data", "custom_rule_hits.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
