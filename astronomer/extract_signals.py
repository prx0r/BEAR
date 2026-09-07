"""Astronomer signal extractor — pulls from Telegram channel (free, no API key needed)."""

import re
import json
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict

import httpx


@dataclass
class TradeSignal:
    """Extracted trade signal."""
    timestamp: str
    direction: str  # LONG, SHORT, NEUTRAL
    timeframe: str  # monthly, 3d, 6h, m30
    size_pct: Optional[float] = None
    entry: Optional[float] = None
    tp: Optional[float] = None
    sl: Optional[float] = None
    rr: Optional[float] = None
    status: str = "open"  # open, closed, tp_hit, sl_hit
    text: str = ""
    source_url: str = ""


class AstronomerExtractor:
    """Extract signals from Astronomer's Telegram channel."""

    TELEGRAM_URL = "https://t.me/s/AstronomerZero"

    def __init__(self):
        self._client = httpx.Client(timeout=15.0)

    def fetch_recent_posts(self, limit: int = 50) -> list[dict]:
        """Fetch recent posts from Telegram channel."""
        resp = self._client.get(self.TELEGRAM_URL)
        resp.raise_for_status()
        html = resp.text

        # Parse messages from Telegram HTML
        messages = []
        # Find message blocks
        msg_pattern = r'<div class="tgme_widget_message_wrap[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>'
        matches = re.findall(msg_pattern, html, re.DOTALL)

        for match in matches[:limit]:
            msg = self._parse_message(match)
            if msg:
                messages.append(msg)

        return messages

    def _parse_message(self, html: str) -> Optional[dict]:
        """Parse a single Telegram message."""
        # Extract text
        text_match = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
        text = ""
        if text_match:
            text = re.sub(r'<[^>]+>', '', text_match.group(1)).strip()

        # Extract X post preview text (embedded in Telegram)
        x_preview_match = re.search(r'link_preview_description[^>]*>(.*?)</div>', html, re.DOTALL)
        x_preview = ""
        if x_preview_match:
            x_preview = re.sub(r'<[^>]+>', '', x_preview_match.group(1)).strip()

        # Extract X post title
        x_title_match = re.search(r'link_preview_title[^>]*>(.*?)</div>', html, re.DOTALL)
        x_title = ""
        if x_title_match:
            x_title = re.sub(r'<[^>]+>', '', x_title_match.group(1)).strip()

        # Combine all text
        parts = [p for p in [text, x_title, x_preview] if p]
        full_text = "\n".join(parts) if parts else ""

        if not full_text:
            return None

        # Extract date
        date_match = re.search(r'datetime="([^"]+)"', html)
        date = date_match.group(1) if date_match else ""

        # Extract views
        views_match = re.search(r'(\d+[\d,.]*)\s*views', html)
        views = views_match.group(1).replace(',', '') if views_match else "0"

        # Extract X links
        x_links = re.findall(r'https://x\.com/astronomer_zero/status/(\d+)', html)

        return {
            "text": full_text,
            "date": date,
            "views": int(views),
            "x_links": list(set(x_links)),  # dedupe
        }

    def extract_signals(self, posts: list[dict]) -> list[TradeSignal]:
        """Extract trade signals from posts."""
        signals = []

        for post in posts:
            text = post["text"]
            lower = text.lower()

            # Skip non-trade posts
            if not any(w in lower for w in ["short", "long", "tp", "trade", "position", "hold"]):
                continue

            # Detect direction
            direction = "NEUTRAL"
            if any(w in lower for w in ["short", "shorting", "shorted", "$btc short", "shorts"]):
                direction = "SHORT"
            elif any(w in lower for w in ["long", "longing", "longed", "big size long", "scalp long"]):
                direction = "LONG"

            # Detect timeframe
            timeframe = "unknown"
            if any(w in lower for w in ["monthly", "macro", "spot accumulation"]):
                timeframe = "monthly"
            elif any(w in lower for w in ["3d", "tridaily", "positional", "positional timeframe"]):
                timeframe = "3d"
            elif any(w in lower for w in ["6h", "swing", "swing trade"]):
                timeframe = "6h"
            elif any(w in lower for w in ["m30", "scalp", "30m", "lower timeframes"]):
                timeframe = "m30"

            # Detect size
            size = None
            size_match = re.search(r'(\d+)%', text)
            if size_match:
                size = float(size_match.group(1))

            # Detect RR
            rr = None
            rr_match = re.search(r'(\d+\.?\d*)\s*rr', lower)
            if rr_match:
                rr = float(rr_match.group(1))

            # Detect TP/SL
            tp = None
            sl = None
            tp_match = re.search(r'tp\s*(?:at|@|hit|some|here)?\s*(?:at\s*)?(\d+[k,.]?\d*)', lower)
            if tp_match:
                tp = self._parse_price(tp_match.group(1))
            sl_match = re.search(r'(?:sl|stop|stoploss)\s*(?:at|@)?\s*(\d+[k,.]?\d*)', lower)
            if sl_match:
                sl = self._parse_price(sl_match.group(1))

            # Detect status
            status = "open"
            if any(w in lower for w in ["tp hit", "took profit", "tp'd", "closed", "touchdown", "there's the drop"]):
                status = "tp_hit"
            elif any(w in lower for w in ["sl hit", "stopped out", "big short l"]):
                status = "sl_hit"

            if direction != "NEUTRAL":
                signals.append(TradeSignal(
                    timestamp=post["date"],
                    direction=direction,
                    timeframe=timeframe,
                    size_pct=size,
                    tp=tp,
                    sl=sl,
                    rr=rr,
                    status=status,
                    text=text[:200],
                    source_url=f"https://t.me/s/AstronomerZero",
                ))

        return signals

    def _parse_price(self, s: str) -> Optional[float]:
        """Parse price string like '82k' or '82,500'."""
        s = s.replace(',', '').replace('k', '000').replace('K', '000')
        try:
            return float(s)
        except ValueError:
            return None

    def get_signal_summary(self) -> dict:
        """Get summary of recent signals."""
        posts = self.fetch_recent_posts()
        signals = self.extract_signals(posts)

        # Count by direction
        direction_counts = {}
        for s in signals:
            direction_counts[s.direction] = direction_counts.get(s.direction, 0) + 1

        # Count by timeframe
        tf_counts = {}
        for s in signals:
            tf_counts[s.timeframe] = tf_counts.get(s.timeframe, 0) + 1

        # Win rate
        tp_hits = sum(1 for s in signals if s.status == "tp_hit")
        closed = sum(1 for s in signals if s.status in ("tp_hit", "sl_hit"))
        win_rate = tp_hits / closed if closed > 0 else 0

        return {
            "total_posts": len(posts),
            "total_signals": len(signals),
            "direction_counts": direction_counts,
            "timeframe_counts": tf_counts,
            "win_rate": round(win_rate, 2),
            "recent_signals": [asdict(s) for s in signals[:10]],
        }


def main():
    """CLI entry point."""
    import click

    @click.command()
    @click.option("--limit", "-n", default=50, help="Number of posts to fetch")
    @click.option("--json", "as_json", is_flag=True, help="Output as JSON")
    def cli(limit: int, as_json: bool):
        """Extract Astronomer signals from Telegram."""
        extractor = AstronomerExtractor()
        summary = extractor.get_signal_summary()

        if as_json:
            click.echo(json.dumps(summary, indent=2))
        else:
            click.echo(f"Astronomer Signal Summary")
            click.echo(f"=" * 50)
            click.echo(f"Posts scanned: {summary['total_posts']}")
            click.echo(f"Signals found: {summary['total_signals']}")
            click.echo(f"Win rate: {summary['win_rate'] * 100:.0f}%")
            click.echo(f"\nDirection breakdown:")
            for d, c in summary['direction_counts'].items():
                click.echo(f"  {d}: {c}")
            click.echo(f"\nTimeframe breakdown:")
            for t, c in summary['timeframe_counts'].items():
                click.echo(f"  {t}: {c}")
            click.echo(f"\nRecent signals:")
            for s in summary['recent_signals'][:5]:
                click.echo(f"  [{s['timeframe']}] {s['direction']} @ {s['timestamp'][:10]} — {s['text'][:80]}...")

    cli()


if __name__ == "__main__":
    main()
