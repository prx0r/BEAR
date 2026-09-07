# Overview

Get X/Twitter tweets pushed to your server in real time. Register the accounts to monitor and receive every new tweet as an HMAC-signed webhook within seconds.

Real-time tweet monitoring pushes new tweets to **your** server. Register the X accounts you care about, point them at a webhook URL, and every new tweet is delivered as a signed HTTPS `POST` within seconds of being published.

No polling. No cron jobs. No missed tweets while your job was asleep.

This section is the endpoint reference. For plans, detection latency and how push compares with polling, start with the [Twitter webhook API](https://www.getxapi.com/twitter-webhook-api) page on the main site. If you were looking for X's own webhook product and its CRC check, that is a different system, covered in [X webhooks, the CRC check and subscription limits](https://www.getxapi.com/blogs/twitter-webhooks-crc-guide).

Monitoring endpoints are **not billed per API call**. Access comes with a Monitoring plan, and your plan sets how many accounts you can watch at once. Webhook deliveries and retries are never charged individually.

## How it works

1. **Create a webhook**: a destination URL plus a signing secret. [Create webhook](/docs/monitoring/webhook-create)
2. **Add a monitor**: tell us which X account to watch and which webhook to deliver to. [Add monitor](/docs/monitoring/add-monitor)
3. **Receive tweets**: every new tweet arrives at your URL as a signed `POST`. [Delivery contract](/docs/monitoring/webhook-delivery)

That's the whole loop. Everything else is management: listing, pausing, repointing, removing.

## Authentication

Every request uses the same bearer key as the rest of the API:

```
curl https://api.getxapi.com/twitter/monitor/list \
  -H "Authorization: Bearer YOUR_API_KEY"
```

If your account has never had a Monitoring plan, monitoring endpoints return `403`. If a previous subscription has **lapsed**, the read endpoints ([`list`](/docs/monitoring/list-monitors), [`health`](/docs/monitoring/monitor-health), [`webhook/list`](/docs/monitoring/webhook-list)) keep working so you can see your saved setup; everything else returns `403` with code `SUBSCRIPTION_LAPSED` until you renew. See the [error reference](/docs/monitoring/overview#errors) below.

## Concepts

| Term | Meaning |
|------|---------|
| **Webhook** | A destination URL and its signing secret. Reusable, so many monitors can deliver to one webhook. |
| **Monitor** | One subscription: *you* watch *this X account*, delivering to *this webhook*. Counts against your plan limit. |
| **Target** | The X account being watched. Shared across all customers watching it. |
| **Delivery** | A single webhook `POST` for one tweet on one monitor. Identified by a stable `delivery_id`. |

## Two different "tiers"

These are unrelated, and the names are easy to confuse:

| What it controls | Where it's set |
|------------------|----------------|
| **Poll tier**: How fast a tweet is detected: `standard` ≈ 15s, `fast` ≈ 2s | Per monitor, via `tier` |
| **Plan tier**: How **many** accounts you can watch at once | Your Monitoring subscription |

A `fast` monitor and a `standard` monitor both count as exactly one monitor against your plan limit. `fast` changes latency, not quota.

## Monitoring starts from now

When you add a monitor we record a **baseline**, the newest tweet on that account at that moment. Only tweets posted **after** the baseline are delivered.

There is no backfill. Adding a monitor for an account with 10,000 existing tweets will not send you 10,000 webhooks.

The same applies when you resume a paused monitor: resuming re-baselines, so tweets posted during the pause are **not** replayed. If you need history, use [User Tweets](/docs/users/user-tweets) or [Advanced Search](/docs/tweets/advanced-search) alongside monitoring.

## Shared targets and `effective_tier`

Targets are shared. If several customers watch the same account, it is polled once and the result fanned out to everyone watching it.

A consequence you will see in [List monitors](/docs/monitoring/list-monitors): the response has both `requested_tier` and `effective_tier`. If someone else watching the same account requested `fast`, that account is polled at `fast` speed and **you get the benefit**. Your `effective_tier` reads `fast` even though you requested `standard`.

`effective_tier` is never *slower* than what you requested. It is only ever equal or better, and it is not something you can rely on or pay less for. Treat it as a bonus, not a guarantee.

## Why monitor X accounts in real time

Real-time tweet monitoring is the building block behind most X automation:

- **Trading and market signals.** Headline accounts move markets, and a 15-second lag is the difference between acting on news and reading about it.
- **Brand monitoring and social listening.** Catch mentions, complaints, and viral threads while the conversation is still live.
- **Competitor tracking.** Know the moment a rival announces a launch, a price change, or a funding round.
- **Lead generation.** Watch accounts that post buying intent and route new tweets straight into your CRM.
- **News aggregation.** Build a feed from a curated set of reporters and wire services without polling any of them.
- **Community and moderation tooling.** React to posts from members of your own community as they land.

Because delivery is push-based, none of these need a scheduler, a queue of cron jobs, or a last-seen-ID table on your side.

## Webhooks vs polling vs the X streaming API

Three ways to get new tweets, and what each actually costs you:

| Approach | Latency | What you maintain | Availability |
|----------|---------|-------------------|--------------|
| **GetXAPI webhooks** (this section) | 2s to 15s | A single HTTPS endpoint | Any Monitoring plan |
| **Polling a read endpoint** | Your interval, plus drift | Cron, last-seen-ID state, backoff, dedupe | Any account, billed per call |
| **Official X filtered stream** | Near real time | A held-open connection, reconnect and backfill logic | Gated to the enterprise tier |

Polling works and is still the right answer when you need history rather than new posts. What it cannot do is scale to many accounts cheaply: every account you watch multiplies your call volume, whether or not anything was posted. Webhooks invert that, so you are only doing work when a tweet actually exists. For pulling the past rather than the present, use [User Tweets](/docs/users/user-tweets) or [Advanced Search](/docs/tweets/advanced-search).

## Delivery guarantees

- **At-least-once.** A tweet may be delivered more than once. Dedupe on `delivery_id`.
- **Signed.** Every request carries an HMAC-SHA256 signature. [Verify it](/docs/monitoring/webhook-delivery#verifying-the-signature). It is the only thing proving the request came from us.
- **Retried.** Failed deliveries retry with exponential backoff for roughly 21 minutes before being dropped.
- **Ordered per target, not globally.** Tweets from one account arrive in order. Tweets from different accounts may interleave.

## Endpoints

**Webhooks**

| Endpoint | Purpose |
|----------|---------|
| [`POST /twitter/monitor/webhook/create`](/docs/monitoring/webhook-create) | Register a delivery URL, get a signing secret |
| [`GET /twitter/monitor/webhook/list`](/docs/monitoring/webhook-list) | List your webhooks |
| [`POST /twitter/monitor/webhook/test`](/docs/monitoring/webhook-test) | Send a signed test payload |
| [`DELETE /twitter/monitor/webhook/delete`](/docs/monitoring/webhook-delete) | Remove a webhook |

**Monitors**

| Endpoint | Purpose |
|----------|---------|
| [`POST /twitter/monitor/add`](/docs/monitoring/add-monitor) | Start watching an account |
| [`GET /twitter/monitor/list`](/docs/monitoring/list-monitors) | List your monitors |
| [`POST /twitter/monitor/update`](/docs/monitoring/update-monitor) | Pause, resume, change tier or webhook |
| [`POST /twitter/monitor/remove`](/docs/monitoring/remove-monitor) | Stop watching, free a plan slot |
| [`GET /twitter/monitor/health`](/docs/monitoring/monitor-health) | Your queue and delivery status |

## Rate limits

The endpoints above are the **control plane**, how you manage and test your setup. They are rate limited to prevent abuse. This is not a cap on how much data you receive: **tweet deliveries and their retries are never rate limited**, no matter how often a monitored account posts.

| Endpoint / action | Limit |
|-------------------|-------|
| [`POST /webhook/create`](/docs/monitoring/webhook-create) | 10/min |
| [`POST` or `DELETE /webhook/delete`](/docs/monitoring/webhook-delete) | 10/min combined across both verbs |
| [`POST /webhook/test`](/docs/monitoring/webhook-test) | 5/min |
| [`GET /webhook/list`](/docs/monitoring/webhook-list) | 60/min |
| [`POST /add`](/docs/monitoring/add-monitor) | 20/min |
| [`GET /list`](/docs/monitoring/list-monitors) | 60/min |
| [`POST /update`](/docs/monitoring/update-monitor) | 30/min |
| [`POST /update`](/docs/monitoring/update-monitor) with `action: "resume"` | 20/min |
| [`POST /remove`](/docs/monitoring/remove-monitor) | 30/min |
| [`GET /health`](/docs/monitoring/monitor-health) | 60/min |

**Fixed 60-second windows.** A window opens on your first request and resets 60 seconds later, when the full allowance returns. There is no gradual refill.

**Shared across all your API keys.** The counter is keyed to your account, not to the key you send. Creating more keys does not raise your ceiling.

**Some requests consume two allowances.** [`POST /add`](/docs/monitoring/add-monitor) with an inline `webhook_url` draws on both the monitor-add *and* the webhook-create budget, since it creates a webhook as a side effect. Both are checked before either is charged, so a `429` never spends the allowance that still had room.

**Throttled requests cost nothing.** No monitoring endpoint is billed per call, so a `429` never touches your credit balance.

### Rate limit headers

Every response tells you where you stand on whichever limit that request came closest to reaching:

| Header | Meaning |
|--------|---------|
| `RateLimit-Limit` | Requests allowed in the current window |
| `RateLimit-Remaining` | Requests left in the current window |
| `RateLimit-Reset` | Seconds until the window resets |
| `Retry-After` | **On `429` only.** Seconds to wait before retrying |

### 429 response

```json
{
  "error": "Rate limit exceeded. Please try again later.",
  "retry_after": 42
}
```

The webhook endpoints return the same shape with a more specific message:

```json
{
  "error": "Webhook rate limit exceeded. Please try again later.",
  "retry_after": 42
}
```

`retry_after` is in seconds and always matches the `Retry-After` header. Wait it out rather than retrying immediately: a retry inside the same window returns `429` again.

## Errors

| Status | Code | Meaning |
|--------|------|---------|
| `400` | n/a | Missing or invalid parameters, or a webhook URL we won't accept |
| `403` | n/a | Monitoring is not enabled for this account |
| `403` | `SUBSCRIPTION_LAPSED` | Your subscription has ended or has a payment issue. Reads still work; renew to resume. Your monitors are kept, suspended |
| `403` | `QUOTA_EXCEEDED` | You've hit your plan's monitor limit. Remove one or upgrade |
| `404` | n/a | Monitor, webhook, or X account not found |
| `409` | `ALREADY_MONITORED` | You already have a monitor on that account |
| `409` | `WEBHOOK_IN_USE` | The webhook still has active monitors attached |
| `429` | n/a | Rate limit exceeded. Wait `retry_after` seconds, then retry. See [rate limits](#rate-limits) |
| `502` | `BASELINE_FAILED` | We couldn't read the account's timeline to set a start point. Retry |
| `503` | n/a | Monitoring is temporarily unavailable |

`BASELINE_FAILED` is deliberate. Rather than risk starting a monitor from the wrong point and flooding you with old tweets, we fail and ask you to retry.

## Frequently asked questions

### How fast will I receive a new tweet?

Around 15 seconds on the `standard` tier and around 2 seconds on `fast`, measured from the moment the tweet is published to the moment we send the `POST`. Your own handler time is on top of that.

### Do I get charged per tweet delivered?

No. Monitoring is not billed per API call. Your plan sets how many accounts you can watch at once, and deliveries plus retries are never charged individually.

### Can I monitor replies and quote tweets?

Replies, yes: set `include_replies: true` on the monitor. Quote tweets are the account's own posts, so they are always delivered, and each payload carries an `isQuote` flag.

### Will I get tweets from before I added the monitor?

No. Monitoring is forward-only from the baseline we record when the monitor is created. There is no backfill, and resuming a paused monitor re-baselines rather than replaying the gap.

### How many accounts can I monitor?

As many as your plan's monitor limit allows. Both active and paused monitors hold a slot, so only [removing](/docs/monitoring/remove-monitor) a monitor frees one.

### What happens if my server goes down?

Failed deliveries retry with exponential backoff for roughly 21 minutes. Past that they are dead-lettered and counted in `failed_24h` on [Health](/docs/monitoring/monitor-health). Tweets dropped that way are not recoverable through monitoring, so backfill them with [User Tweets](/docs/users/user-tweets).
