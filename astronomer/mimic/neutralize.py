"""Rule-based neutralizer v1 — strip content markers, keep style shape.

Masks: urls, cashtags (any case), numbers, emoji/symbols, %/x-leverage tokens.
Style kept: casing rhythm lowered, sentence structure, punctuation, stopwords.
Usage: pairs = [(neutralize(t), t) ...]; audit bar: <10% leakage on 30-sample.
"""
import re

URL = re.compile(r"https?://\S+")
CASH = re.compile(r"\$[A-Za-z]{2,10}\b")
NUM = re.compile(r"\d[\d,\.]*k?\b")
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\u2300-\u23FF\u2B00-\u2BFF\uFE00-\uFE0F]")
PCT = re.compile(r"\s?%\s?")
LEV = re.compile(r"\b\d+\s?[xX]\b")
TF = re.compile(r"\b\d+\s?(?:min|mins|h|hr|hrs|d|w|mo|y)\b", re.IGNORECASE)
DATES = re.compile(r"\b\d+(?:st|nd|rd|th)\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", re.IGNORECASE)
COINS = re.compile(r"(?<!\w)(btc|eth|sol|hype|xrp|doge|ada|avax|link|ton|ARB|OP)\b", re.IGNORECASE)


def neutralize(t: str) -> str:
    t = URL.sub(" URL ", t)
    t = CASH.sub(" ASSET ", t)
    t = LEV.sub(" LEV ", t)
    t = NUM.sub(" NUM ", t)
    t = EMOJI.sub(" ", t)
    t = PCT.sub(" PCT ", t)
    t = TF.sub(" TF ", t)
    t = DATES.sub(" DATE ", t)
    t = COINS.sub(" ASSET ", t)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def leaked(neutral: str) -> bool:
    return bool(re.search(
        r"\$[A-Za-z]{2,10}\b|\d[\d,\.]*k?|[\U0001F300-\U0001FAFF\u2600-\u27BF\u2300-\u23FF\u2B00-\u2BFF\uFE00-\uFE0F]|"
        r"(?<!\w)(btc|eth|sol|hype|xrp|doge)\b", neutral))
