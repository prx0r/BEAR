# Cost/Benefit Analysis — Per Content Type

## GetXAPI Pricing

| Endpoint | Cost | Returns |
|----------|------|---------|
| Advanced Search | $0.001/call | ~20 tweets |
| Tweet Thread | $0.005/call | Full thread |
| Tweet Replies | $0.001/call | Replies to tweet |
| User Info | $0.001/call | Profile snapshot |
| Article Get | $0.001/call | Full X Article |
| Monitoring | $0 (Pro) | Real-time webhooks |
| Image download | $0 | HTTP GET |

## Per-Account Assessment

### @astronomer_zero (2,264 tweets)

| Content Type | Count | Cost | Worth It? |
|--------------|-------|------|-----------|
| Standalone posts | 579 | $0 | ✅ Core signal |
| Replies (already fetched) | 1,685 | $0 | ✅ 14% contain signals |
| Media/charts | 472 | $0 | ✅ 21% have images |
| Thread resolution | ~57 | $0.29 | ⚠️ Test first |
| Article detection | ~28 | $0.03 | ⚠️ Test first |
| User info snapshot | 1 | $0.001 | ✅ |
| **TOTAL EXTRA** | | **$0.31** | |

### @Timeless_Crypto (131 tweets)

| Content Type | Count | Cost | Worth It? |
|--------------|-------|------|-----------|
| Standalone posts | 108 | $0 | ✅ Core signal |
| Replies (already fetched) | 23 | $0 | ❌ Mostly noise |
| Media/charts | 87 | $0 | ✅ **66% — PRIMARY ALPHA** |
| Thread resolution | ~10 | $0.05 | ⚠️ Test first |
| Article detection | ~5 | $0.005 | ⚠️ Test first |
| User info snapshot | 1 | $0.001 | ✅ |
| **TOTAL EXTRA** | | **$0.06** | |

## Key Insights

1. **Media/charts are FREE to download** — just HTTP GET the URLs we already have
2. **Replies cost nothing extra** — they're included in the Advanced Search response
3. **Thread resolution is cheap** — $0.005 per thread, only needed for multi-post theses
4. **Articles are cheap** — $0.001 per article, but need to detect which posts are article wrappers

## What's Worth It Per Account

| Account | Media | Replies | Threads | Articles |
|---------|-------|---------|---------|----------|
| Astronomer | ✅ 21% | ✅ 14% signal | ⚠️ Test | ⚠️ Test |
| Timeless | ✅ **66%** | ❌ 18% noise | ⚠️ Test | ⚠️ Test |

**Timeless: charts are EVERYTHING.** 66% of his posts have media. His alpha is in the chart annotations, not the text.

**Astronomer: replies matter.** 74% replies, but 14% contain signals. Filter by signal keywords.
