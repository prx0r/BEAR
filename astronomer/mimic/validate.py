"""A13: schema validator — enforce categories/schema.json in stdlib.

Usage: cd astronomer && python3 -m mimic.validate [FILE.jsonl]  (default: self-test)
Exit 0 = all valid. Prints violations with row numbers.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCHEMA = json.load(open(os.path.join(ROOT, "astronomer", "mimic", "categories", "schema.json")))
ARCH_PAYLOAD = {"CALL": "call", "EXIT": "exit", "COND": "cond", "VERDICT": "verdict",
                "MACRO_STATE": "macro_state", "FLOW_DATA": "flow_data",
                "LEAN_TAC": "lean_tac", "EDU": "edu", "CHATTER": "chatter"}
ENUMS = {"direction": {"LONG", "SHORT"}, "entry_basis": {"NOW", "LEVEL", "UNKNOWN"},
         "fraction": {"PARTIAL", "FULL", "UNKNOWN"}, "scope": {"ASSET", "SECTOR", "MARKET"},
         "verdict": {"BULL", "BEAR", "RANGE"},
         "metric": {"ETF_FLOW", "FUNDING", "OI", "LS_RATIO", "CVD", "WHALE", "UNLOCK", "LIQ", "HACK"},
         "lean": {"LONG", "SHORT"}, "reason": {"REPLY", "NO_NUMBERS", "SPAM", "OFF_TOPIC"},
         "position": {"OPEN", "HYPOTHETICAL", "UNKNOWN"}}


def errors(row):
    errs = []
    for k in SCHEMA["required"]:
        if k not in row or row[k] in (None, ""):
            errs.append(f"missing required {k}")
    if errs:
        return errs
    if row.get("archetype") not in ARCH_PAYLOAD:
        return [f"bad archetype {row.get('archetype')}"]
    if not re.fullmatch(r"[0-9]{15,25}", str(row.get("post_id", ""))):
        errs.append("post_id not snowflake")
    if not isinstance(row.get("evidence"), list) or not row["evidence"]:
        errs.append("evidence empty")
    pay = ARCH_PAYLOAD[row["archetype"]]
    sub = row.get(pay)
    if not isinstance(sub, dict):
        return errs + [f"missing payload {pay}"]
    reqs = {"call": ["asset", "direction", "entry_basis"], "exit": ["asset", "exit_zone", "fraction"],
            "cond": ["asset", "trigger", "action"], "verdict": ["scope", "verdict", "because"],
            "macro_state": ["topics"], "flow_data": ["metric", "values"],
            "lean_tac": ["asset", "lean", "chart_ref"], "edu": ["concepts"], "chatter": ["reason"]}[pay]
    for k in reqs:
        if k not in sub or sub[k] in (None, ""):
            errs.append(f"{pay} missing {k}")
    for k, allowed in ENUMS.items():
        for obj in (row, sub):
            if k in obj and obj[k] not in allowed:
                errs.append(f"bad enum {k}={obj[k]}")
    if row["archetype"] == "LEAN_TAC" and not row.get("chart_ref"):
        errs.append("LEAN_TAC without chart_ref")
    return errs


def selftest():
    rows = [
        {"post_id": "1234567890123456789", "handle": "a", "author_id": "1",
         "published_at": "2026-01-01T00:00:00+00:00", "archetype": "CALL",
         "text": "LONG BTC here", "evidence": [{"field": "direction", "span": "LONG"}],
         "call": {"asset": "BTC", "direction": "LONG", "entry_basis": "NOW"}},
        {"post_id": "bad", "handle": "a", "author_id": "1",
         "published_at": "2026-01-01T00:00:00+00:00", "archetype": "CALL",
         "text": "x", "evidence": [{"field": "direction", "span": "x"}],
         "call": {"asset": "BTC", "direction": "UP"}},
        {"post_id": "1234567890123456789", "handle": "a", "author_id": "1",
         "published_at": "2026-01-01T00:00:00+00:00", "archetype": "LEAN_TAC",
         "text": "looks good", "evidence": [{"field": "lean", "span": "good"}],
         "lean_tac": {"asset": "BTC", "lean": "LONG"}},
    ]
    results = [errors(r) for r in rows]
    assert results[0] == [], results[0]
    assert any("UP" in e or "direction" in e for e in results[1]), results[1]
    assert any("chart" in e for e in results[2]), results[2]
    print("selftest: 3/3 (valid passes, bad-enum + chartless-LEAN rejected)")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        selftest()
    else:
        bad = 0
        for i, line in enumerate(open(sys.argv[1])):
            line = line.strip()
            if not line:
                continue
            e = errors(json.loads(line))
            if e:
                bad += 1
                print(f"row {i}: {e}")
        print(f"{'ALL VALID' if not bad else f'{bad} INVALID'}")
        sys.exit(1 if bad else 0)
