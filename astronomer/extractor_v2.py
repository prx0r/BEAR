"""Evidence-grounded signal extractor.

Extracts MarketEvents from X posts with exact evidence spans.
Source fidelity outranks what the model thinks is true.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class EvidenceSpan:
    """Exact quote supporting a field value."""
    field: str
    post_id: str
    quote: str
    start_char: int
    end_char: int


@dataclass
class MarketEvent:
    """Extracted market event from a post."""
    event_id: str
    post_id: str
    
    # Classification
    semantic_kind: str          # CALL, VIEW, OBSERVATION, INTERPRETATION, RETROSPECTIVE, NON_SIGNAL
    call_state: str = "NONE"   # DIRECT, CONDITIONAL, UPDATE, EXIT, NONE
    target_variable: str = "OTHER"  # PRICE_DIRECTION, VOLATILITY, etc.
    
    # Content
    asset: Optional[str] = None
    direction: Optional[str] = None
    
    # Entry/exit
    entry_type: Optional[str] = None
    entry_price: Optional[float] = None
    entry_low: Optional[float] = None
    entry_high: Optional[float] = None
    stop_price: Optional[float] = None
    target_prices: list[float] = field(default_factory=list)
    
    # Conditional
    condition_type: Optional[str] = None
    trigger_price: Optional[float] = None
    
    # Timeframe
    timeframe_value: Optional[str] = None
    timeframe_explicit: bool = False
    
    # Conviction
    conviction: str = "MEDIUM"
    
    # Evidence (REQUIRED for all non-null fields)
    evidence: list[EvidenceSpan] = field(default_factory=list)
    
    # Provenance
    extraction_version: str = "2.0"
    status: str = "VERIFIED"


# Classification constants
LONG_KW = ['long', 'longing', 'longed', 'buy', 'buying', 'bullish', 'accumulate']
SHORT_KW = ['short', 'shorting', 'shorted', 'sell', 'selling', 'bearish']
NEGATION = ['not', "n't", 'never', 'no ']
RETRO_KW = ['was', 'were', 'told you', 'called it', 'said so', 'yesterday']

ASSET_PATS = {
    'BTC': [r'\$btc', r'\bbtc\b', r'\bbitcoin\b'],
    'ETH': [r'\$eth', r'\beth\b', r'\bethereum\b'],
    'SOL': [r'\$sol\b', r'\bsol\b', r'\bsolana\b'],
    'HYPE': [r'\$hype', r'\bhyperliquid\b'],
    'TAO': [r'\$tao', r'\bbittensor\b'],
}


def find_quote_span(text: str, keyword: str) -> tuple[int, int]:
    """Find exact char positions of keyword in text."""
    idx = text.lower().find(keyword.lower())
    if idx >= 0:
        return idx, idx + len(keyword)
    return -1, -1


def classify_event(text: str, post_id: str, handle: str) -> list[MarketEvent]:
    """Classify a post into one or more MarketEvents with evidence."""
    lower = text.lower()
    events = []
    
    # Check for retrospective
    is_retro = any(w in lower for w in RETRO_KW)
    if is_retro:
        events.append(MarketEvent(
            event_id=f"evt_{post_id}_retro",
            post_id=post_id,
            semantic_kind="RETROSPECTIVE",
            evidence=[EvidenceSpan(
                field="semantic_kind",
                post_id=post_id,
                quote="retrospective content detected",
                start_char=0, end_char=0,
            )],
        ))
        return events
    
    # Check for promotion
    if any(w in lower for w in ['course', 'launch', 'subscribe', 'join', 'sign up']):
        events.append(MarketEvent(
            event_id=f"evt_{post_id}_promo",
            post_id=post_id,
            semantic_kind="NON_SIGNAL",
            evidence=[EvidenceSpan(
                field="semantic_kind",
                post_id=post_id,
                quote="promotional content detected",
                start_char=0, end_char=0,
            )],
        ))
        return events
    
    # Check for negation
    has_negation = any(w in lower for w in NEGATION)
    
    # Check for direction
    direction = None
    direction_evidence = None
    for kw in LONG_KW:
        span = find_quote_span(text, kw)
        if span[0] >= 0 and not has_negation:
            direction = "BULLISH"
            direction_evidence = EvidenceSpan(
                field="direction", post_id=post_id,
                quote=text[span[0]:span[1]], start_char=span[0], end_char=span[1],
            )
            break
    if not direction:
        for kw in SHORT_KW:
            span = find_quote_span(text, kw)
            if span[0] >= 0 and not has_negation:
                direction = "BEARISH"
                direction_evidence = EvidenceSpan(
                    field="direction", post_id=post_id,
                    quote=text[span[0]:span[1]], start_char=span[0], end_char=span[1],
                )
                break
    
    # Check for assets (use regex search, not plain string find)
    assets = []
    asset_evidence = []
    for asset, pats in ASSET_PATS.items():
        for pat in pats:
            m = re.search(pat, lower)
            if m:
                assets.append(asset)
                asset_evidence.append(EvidenceSpan(
                    field="asset", post_id=post_id,
                    quote=text[m.start():m.end()], start_char=m.start(), end_char=m.end(),
                ))
                break
    
    # Check for levels
    level_matches = list(re.finditer(r'(\d{1,3}[,.]?\d{3,4})\s*(k|K)?', text))
    levels = []
    level_evidence = []
    for m in level_matches:
        num_str = m.group(1).replace(',', '')
        try:
            num = float(num_str)
            if m.group(2):
                num *= 1000
            if 50000 < num < 500000:
                levels.append(num)
                level_evidence.append(EvidenceSpan(
                    field="level", post_id=post_id,
                    quote=m.group(0), start_char=m.start(), end_char=m.end(),
                ))
        except:
            pass
    
    # Check for conditional
    is_conditional = bool(re.search(r'\bif\b|\bwhen\b|\breclaim\b|\bbreak\b', lower))
    
    # Determine event kind
    if direction:
        semantic_kind = "CALL"
        call_state = "DIRECT" if not is_conditional else "CONDITIONAL"
    elif levels:
        semantic_kind = "OBSERVATION"
        call_state = "NONE"
    else:
        semantic_kind = "VIEW"
        call_state = "NONE"
    
    # Build evidence list
    evidence = []
    if direction_evidence:
        evidence.append(direction_evidence)
    for ev in asset_evidence:
        evidence.append(ev)
    for ev in level_evidence:
        evidence.append(ev)
    
    # Create event
    event = MarketEvent(
        event_id=f"evt_{post_id}_{semantic_kind.lower()}",
        post_id=post_id,
        semantic_kind=semantic_kind,
        call_state=call_state,
        target_variable="PRICE_DIRECTION" if direction else "OTHER",
        asset=assets[0] if assets else None,
        direction=direction,
        entry_type="MARKET" if direction and not levels else ("LEVEL" if levels else None),
        entry_price=levels[0] if levels else None,
        stop_price=None,
        target_prices=[],
        evidence=evidence,
    )
    
    events.append(event)
    return events


def extract_all(posts: list[dict]) -> list[MarketEvent]:
    """Extract events from all posts."""
    all_events = []
    for post in posts:
        events = classify_event(
            text=post.get('text', ''),
            post_id=post.get('tweet_id', ''),
            handle=post.get('handle', ''),
        )
        all_events.extend(events)
    return all_events
