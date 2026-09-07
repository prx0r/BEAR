"""Meme token extractor — dynamic cashtag and contract address extraction.

Extracts:
- Cashtags: $PONS, $CASHCAT, $WIF, etc.
- Solana addresses: base58 32-44 chars
- EVM addresses: 0x + 40 hex chars
- Dexscreener/GeckoTerminal/FOMO links

Classifies actions:
- ENTRY, ADD, BULLISH_THESIS, HOLD, TARGET, REDUCE, EXIT, BEARISH, RETROSPECTIVE, MENTION
"""

import re
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Cashtags: $ followed by 2-20 alphanumeric/underscore
# But exclude pure numbers (monetary amounts like $50, $100, $1M)
CASHTAG_RE = re.compile(r'\$([A-Za-z][A-Za-z0-9_]{1,19})')

# Monetary amounts to exclude
MONEY_RE = re.compile(r'^\d+[KkMmBb]?$')

# Solana addresses: base58, 32-44 chars (no 0, O, I, l)
SOLANA_ADDR_RE = re.compile(r'\b[1-9A-HJ-NP-Za-km-z]{32,44}\b')

# EVM addresses: 0x + 40 hex chars
EVM_ADDR_RE = re.compile(r'\b0x[0-9a-fA-F]{40}\b')

# Dexscreener links
DEXSCREENER_RE = re.compile(r'dexscreener\.com/(\w+)/([0-9a-fA-F]+)')

# GeckoTerminal links
GECKOTERMINAL_RE = re.compile(r'geckoterminal\.com/(\w+)/pools/([0-9a-fA-F]+)')

# FOMO links
FOMO_RE = re.compile(r'fomo\.me/(\w+)')

# Contract address in text (often prefixed with "CA:" or "ca:")
CA_LABEL_RE = re.compile(r'(?:CA|ca|contract)\s*[:=]\s*([1-9A-HJ-NP-Za-km-z]{32,44}|0x[0-9a-fA-F]{40})')

# Action keywords
ENTRY_KW = re.compile(r'\b(?:bought|buying|buy|long|entered|opening|starting|initiated|picked up|loaded|ap[eé]d?|aped)\b', re.I)
ADD_KW = re.compile(r'\b(?:adding|add more|averaging|dca|increasing|scaling in|building)\b', re.I)
THESIS_KW = re.compile(r'\b(?:highest conviction|bullish on| thesis| believe in| think .{0,30} goes| will run| going to| going parabolic| conviction play| my pick| alpha)\b', re.I)
TARGET_KW = re.compile(r'\b(?:to \d|target| price target| see it at| expect|100m|1b|10x|5x|100x)\b', re.I)
REDUCE_KW = re.compile(r'\b(?:took profit|took half|trimming|trim|selling some|reducing|de-risking|taking profit|took a bit)\b', re.I)
EXIT_KW = re.compile(r'\b(?:closed|sold all|exited|out of|gone|fully out|completely out|flat)\b', re.I)
BEARISH_KW = re.compile(r'\b(?:dead|rug|scam|avoid|stay away|exit only|don.t buy|not buying|overvalued|too late|topped)\b', re.I)
RETRO_KW = re.compile(r'\b(?:turned \$|into \$|was at|bought at .{0,20} and now|from \$.{0,10} to|called this|told you|first called|early call|was early)\b', re.I)
MENTION_KW = re.compile(r'\b(?:mention|hat tip|shoutout|found by|via |h/t )\b', re.I)


# ---------------------------------------------------------------------------
# Asset extraction
# ---------------------------------------------------------------------------

def extract_asset_refs(text: str) -> list[dict]:
    """Extract all asset references from text."""
    refs = []
    seen = set()

    # 1. Cashtags (exclude monetary amounts)
    for m in CASHTAG_RE.finditer(text):
        sym = m.group(1).upper()
        if sym not in seen and not MONEY_RE.match(m.group(1)):
            seen.add(sym)
            refs.append({
                "type": "cashtag",
                "symbol": sym,
                "start": m.start(),
                "end": m.end(),
                "quote": text[m.start():m.end()],
            })

    # 2. EVM addresses
    for m in EVM_ADDR_RE.finditer(text):
        addr = m.group(0)
        if addr not in seen:
            seen.add(addr)
            refs.append({
                "type": "evm_address",
                "contract_address": addr,
                "chain": "evm",
                "start": m.start(),
                "end": m.end(),
                "quote": text[m.start():m.end()],
            })

    # 3. Solana addresses (only with CA label or in known context)
    # Only match if preceded by CA:, ca:, contract:, or in a Dexscreener/Gecko link context
    for m in CA_LABEL_RE.finditer(text):
        addr = m.group(1)
        if addr not in seen and not addr.startswith("0x"):
            seen.add(addr)
            refs.append({
                "type": "solana_address",
                "contract_address": addr,
                "chain": "solana",
                "start": m.start(),
                "end": m.end(),
                "quote": text[m.start():m.end()],
            })

    # 4. Dexscreener links
    for m in DEXSCREENER_RE.finditer(text):
        chain = m.group(1)
        addr = m.group(2)
        if addr not in seen:
            seen.add(addr)
            refs.append({
                "type": "dexscreener",
                "contract_address": addr,
                "chain": chain,
                "start": m.start(),
                "end": m.end(),
                "quote": text[m.start():m.end()],
            })

    # 5. GeckoTerminal links
    for m in GECKOTERMINAL_RE.finditer(text):
        chain = m.group(1)
        pool = m.group(2)
        if pool not in seen:
            seen.add(pool)
            refs.append({
                "type": "geckoterminal_pool",
                "pool_address": pool,
                "chain": chain,
                "start": m.start(),
                "end": m.end(),
                "quote": text[m.start():m.end()],
            })

    # 6. CA labels
    for m in CA_LABEL_RE.finditer(text):
        addr = m.group(1)
        if addr not in seen:
            seen.add(addr)
            chain = "evm" if addr.startswith("0x") else "solana"
            refs.append({
                "type": "ca_label",
                "contract_address": addr,
                "chain": chain,
                "start": m.start(),
                "end": m.end(),
                "quote": text[m.start():m.end()],
            })

    return refs


def has_asset_reference(text: str) -> bool:
    """Quick check if text contains any asset reference."""
    return bool(CASHTAG_RE.search(text) or EVM_ADDR_RE.search(text) or
                SOLANA_ADDR_RE.search(text) or CA_LABEL_RE.search(text) or
                DEXSCREENER_RE.search(text) or GECKOTERMINAL_RE.search(text))


# ---------------------------------------------------------------------------
# Action classification
# ---------------------------------------------------------------------------

def classify_meme_action(text: str) -> tuple[str, float]:
    """Classify the action in a meme-related post.

    Returns (action, confidence).
    """
    lower = text.lower()

    # Priority order: EXIT > REDUCE > ENTRY > ADD > THESIS > TARGET > BEARISH > RETRO > MENTION
    # (Exit/reduce are more specific and should override generic bullishness)

    if RETRO_KW.search(text):
        return "RETROSPECTIVE", 0.9

    if EXIT_KW.search(text):
        return "EXIT", 0.85

    if REDUCE_KW.search(text):
        return "REDUCE", 0.8

    if BEARISH_KW.search(text):
        return "BEARISH", 0.7

    if ENTRY_KW.search(text):
        return "ENTRY", 0.8

    if ADD_KW.search(text):
        return "ADD", 0.75

    if THESIS_KW.search(text):
        return "BULLISH_THESIS", 0.7

    if TARGET_KW.search(text):
        return "TARGET", 0.7

    if MENTION_KW.search(text):
        return "MENTION", 0.6

    # Default: if it has an asset reference but no clear action, it's a MENTION
    if has_asset_reference(text):
        return "MENTION", 0.5

    return "IGNORE", 0.0


# ---------------------------------------------------------------------------
# Combined extractor
# ---------------------------------------------------------------------------

@dataclass
class MemeExtraction:
    """Result of meme extraction from a single post."""
    post_id: str
    author_handle: str
    author_id: str
    published_at: str
    text: str

    # Asset references found
    asset_refs: list[dict] = field(default_factory=list)

    # Primary action
    action: str = "IGNORE"
    action_confidence: float = 0.0

    # Conviction
    conviction: str = "MEDIUM"

    # Whether this is an explicit entry (not just thesis)
    explicit_entry: bool = False

    # Evidence
    evidence_quotes: list[str] = field(default_factory=list)


def extract_meme_event(post: dict) -> Optional[MemeExtraction]:
    """Extract meme event from a post.

    Args:
        post: Dict with tweet_id, text, author_id, author_handle, created_at

    Returns:
        MemeExtraction if post contains asset references, None otherwise.
    """
    text = post.get("text", "")

    # Pre-filter: must contain asset reference
    if not has_asset_reference(text):
        return None

    # Extract asset references
    asset_refs = extract_asset_refs(text)

    if not asset_refs:
        return None

    # Classify action
    action, confidence = classify_meme_action(text)

    # Determine conviction
    lower = text.lower()
    if any(w in lower for w in ["highest conviction", "conviction play", "my pick", "all in", "yolo"]):
        conviction = "HIGH"
    elif any(w in lower for w in ["like", "interesting", "watching", "keeping an eye"]):
        conviction = "LOW"
    else:
        conviction = "MEDIUM"

    # Determine if explicit entry
    explicit_entry = action in ("ENTRY", "ADD")

    # Collect evidence quotes
    evidence_quotes = []
    for ref in asset_refs:
        if ref.get("quote"):
            evidence_quotes.append(ref["quote"])

    return MemeExtraction(
        post_id=post.get("tweet_id", post.get("id", "")),
        author_handle=post.get("handle", post.get("author_handle", "")),
        author_id=post.get("author_id", ""),
        published_at=post.get("created_at", post.get("createdAt", "")),
        text=text,
        asset_refs=asset_refs,
        action=action,
        action_confidence=confidence,
        conviction=conviction,
        explicit_entry=explicit_entry,
        evidence_quotes=evidence_quotes,
    )


def extract_meme_events(posts: list[dict]) -> list[MemeExtraction]:
    """Extract meme events from a list of posts.

    Returns only posts that contain asset references.
    """
    events = []
    for post in posts:
        event = extract_meme_event(post)
        if event:
            events.append(event)
    return events
