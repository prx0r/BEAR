# Error Reference

Every error the GetXAPI Twitter/X API can return, what it means, and when a retry helps. HTTP status codes, X error codes, and per-endpoint handling.

This page lists the errors each endpoint can return, what they mean, and how to handle them. Use it to build robust error handling and know when a **retry** will help.

## Error response format

Errors return a JSON body with an `error` message. Some responses include extra fields:

```json
{
  "error": "Human-readable message",
  "twitter_error_code": 187,
  "challenge": "rate_limited",
  "retry_after": 120
}
```

- **`error`**: always present. For failures that come **from X**, this is X's own message, passed through verbatim. For issues on **our** side (temporary capacity, an internal error), it's a safe generic message.
- **`twitter_error_code`**: the numeric X error code (e.g. `187`, `344`, `502`). Present **only** when the failure came from X directly; omitted for validation, capacity, and internal errors. So if it's present, you can branch on it reliably.
- **`challenge`**: login only. A stable, machine-readable key (`rate_limited`, `locked`, `verification_required`, `totp_required`).
- **`retry_after`**: present on some rate-limit responses; seconds to wait.

## Common errors (all endpoints)

These can appear on any request.

| Status | Message | What it means | What to do |
|--------|---------|---------------|------------|
| **401** | `Invalid or missing API key` | Your API key is missing or wrong | Check your `Authorization: Bearer <key>` header |
| **400** | `Missing required … param: <x>` | A required field/parameter is missing or invalid | Fix the request |
| **429** | `Please try again shortly.` (our capacity) · `Rate limit exceeded…` · or an X-side limit message | Too many requests, our capacity, or an **X account limit** (e.g. daily DM/tweet limit, these carry a `twitter_error_code`) | Wait `retry_after` / short backoff, then retry |
| **500** | `Internal server error` | A temporary error occurred | Retry shortly |

**Two kinds of 401.** A `401` at the API level means your **API key** is wrong. On write endpoints (posting, liking, profile updates), a `401` can also mean the **`auth_token` you supplied** is invalid or expired, the message will say `Invalid auth_token` or `Could not authenticate you`. Re-mint the token in that case.

## HTTP status codes

| Status | Meaning |
|--------|---------|
| **200** | Success |
| **202** | Accepted, the action is queued/pending (e.g. a community post awaiting moderation) |
| **400** | Bad request, missing/invalid parameters, invalid proxy URL, or media too large |
| **401** | Unauthorized, bad API key or invalid/expired `auth_token` |
| **403** | Forbidden — a **protected/private or suspended target account** (its posts can't be read), a suspended/locked account you're using, a permission restriction, or a Premium-only action |
| **404** | Not found, the user, tweet, or resource doesn't exist |
| **409** | Conflict, duplicate tweet |
| **410** | Gone, the account is suspended |
| **422** | The login couldn't be completed (retry usually helps) |
| **423** | Locked, the account is locked or needs a verification step |
| **429** | Too many requests, a rate limit was hit |
| **500 / 502 / 503** | Temporary server or upstream error, retry |

## Twitter error codes

When a failure comes from X, we pass through X's own code as `twitter_error_code`.

| Code | Meaning | What to do |
|------|---------|------------|
| **32** | Could not authenticate you | `auth_token` is invalid/expired, re-mint it |
| **63** | The target account is suspended | Nothing, the account is gone |
| **64** | Your account is suspended | Use a different account |
| **131** | Temporary X internal error | Retry |
| **139** | Already liked | Already done, safe to ignore |
| **144** | No tweet found with that ID | The tweet was deleted or the ID is wrong |
| **187** | Duplicate tweet | Change the text or wait ~15 minutes |
| **226** | Request looked automated | Retry |
| **326** | Account temporarily locked | Unlock at `x.com/account/access`, then retry |
| **327** | Already retweeted | Already done, safe to ignore |
| **344** | Posting temporarily limited (network/IP throttle, not the account) | Retry shortly, or post through a clean dedicated proxy — one sticky IP per account. Not billed |
| **349** | Cannot message this user | The recipient doesn't accept your DMs |
| **399** | Wrong password / couldn't log in | Check credentials, or retry (temporary login limit) |
| **433** | Reply restricted / Premium required | The tweet is reply-gated, or the action needs X Premium |
| **465** | Cannot retweet an outdated tweet | The tweet is too old to retweet |
| **476** | Not allowed to send message requests | The account can't send DM requests |
| **502** | Daily DM (message request) limit reached | Wait 24 hours, or use an X Premium account for higher limits |

## Reading tweets & search

Applies to `/twitter/user/tweets`, `/twitter/user/tweets_and_replies`, and `/twitter/tweet/advanced_search`.

| Status | Message | What to do |
|--------|---------|------------|
| **403** | `This account's posts are not available. The account is protected (private), suspended, or no longer active.` | **Don't retry** — this is permanent, not a temporary error. The target's posts aren't readable by anyone who isn't an approved follower. Point the request at a public account. |
| **403** | `This account is suspended, so its posts are not available.` | The target account is suspended. Nothing to do — the account is gone. |
| **502** | `Upstream returned an unexpected response — please retry.` | A genuine transient upstream hiccup for that request. **Retry** — the API already rotates accounts internally, so a retry almost always succeeds. **Not billed.** |

A **protected/suspended target** returns a fast, terminal `403` (retrying never helps). A `502` here is the opposite — a transient blip that a retry clears. They are different conditions despite both meaning "no posts returned."

## Posting & engagement

### Create Tweet

**POST** `/twitter/tweet/create`

| Status | Code | Message | What to do |
|--------|------|---------|------------|
| **409** | 187 | `Status is a duplicate.` | Change the text or wait ~15 min |
| **403** | 433 | `The original Tweet author restricted who can reply…` | The tweet doesn't allow your reply |
| **403** | 433 | Long-form / long-video needs Premium | Use a Premium account or shorten the content |
| **403** | n/a | Not a member of the community | Join the community first |
| **429** | 344 | Posting temporarily limited (network/IP throttle) | Retry shortly, or use a clean dedicated proxy (one sticky IP/account). **Not billed** |
| **502** | n/a | `X returned an empty result` (outcome unconfirmed) | Retry — the API already re-tries once, duplicate-safe. **Not billed** |
| **400** | n/a | `File size exceeds…` | Reduce the media file size |
| **202** | n/a | `pending_moderation: true` | Not an error, the community post is awaiting review |
| **503** | 226 | `This request looks automated` | Retry |
| **502 / 503** | n/a | Temporary connection error | Retry (if you supplied a `proxy`, confirm it's working) |

### Edit Tweet

**POST** `/twitter/tweet/edit`

| Status | Code | Message | What to do |
|--------|------|---------|------------|
| **403** | n/a | `This post can't be edited…` | The account isn't X Premium, the ~1h edit window passed, the edit limit was reached, or the post is a reply/thread (not an editable original). Don't retry |
| **400** | n/a | `Missing required field: tweet_id` | Provide `tweet_id` and `text` |
| **404** | n/a | Post not found | Wrong id, or you passed a superseded id (edit the latest version's `data.id`) |
| **401** | 32 | `Could not authenticate you` | `auth_token` invalid/expired, re-mint |

### Favorite / Retweet / Bookmark

**POST** `/twitter/tweet/favorite` · `/twitter/tweet/retweet` · `/twitter/tweet/bookmark` · `/twitter/tweet/unbookmark`

| Status | Code | Message | What to do |
|--------|------|---------|------------|
| **403** | n/a | `User is suspended, deactivated or offboarded` | The account you're using is dead, switch accounts |
| **401** | 32 | `Could not authenticate you` | `auth_token` invalid/expired, re-mint |
| **403** | 465 | `not permitted to retweet an outdated Tweet` | The tweet is too old to retweet |
| **200** | 139 / 327 | already liked / already retweeted | Already done, safe to ignore |
| **429** | n/a | Rate limit | Slow down, then retry |
| **502 / 503** | n/a | Temporary connection error | Retry |

### Delete Tweet

**POST** `/twitter/tweet/delete`

| Status | Message | What to do |
|--------|---------|------------|
| **404** | `No status found with that ID` | Already deleted or wrong ID |
| **403** | Not the author | You can only delete your own tweets |
| **401** | Invalid `auth_token` | Re-mint the token |

### Follow / Unfollow

**POST** `/twitter/user/follow` · `/twitter/user/unfollow`

| Status | Message | What to do |
|--------|---------|------------|
| **404** | `User not found` | Check the handle/ID |
| **403** | Restricted | The account or target doesn't allow it |
| **401** | Invalid `auth_token` | Re-mint the token |
| **429** | Follow limit | Wait, then retry |

### Update Profile / Avatar / Banner

**POST** `/twitter/user/update_profile` · `/twitter/user/update_avatar` · `/twitter/user/update_banner`

| Status | Message | What to do |
|--------|---------|------------|
| **401** | `Invalid auth_token - could not fetch credentials` | Re-mint the token |
| **400** | Image too large / bad format | Fix the image |

### Join Community

**POST** `/twitter/community/join`

| Status | Message | What to do |
|--------|---------|------------|
| **429** | `You have already joined several Communities…` | Try again later |
| **400** | Invalid community | Check the community ID |
| **403** | Restricted | The account can't join |

## Login

**POST** `/twitter/user_login`

The `challenge` field is a stable key you can branch on programmatically.

| Status | `challenge` | Message | What to do |
|--------|-------------|---------|------------|
| **429** | `rate_limited` | `Login temporarily limited by Twitter (rate limit). Try again later.` | Wait ~30 min, or retry with a higher-quality proxy |
| **401** | n/a | `Wrong password` | Check the credentials |
| **401** | `totp_required` | `Two-factor authentication is enabled, provide totp_secret` | Include the account's `totp_secret` |
| **404** | n/a | `Username not found` | Check the handle |
| **410** | n/a | `Account suspended` | The account is gone |
| **423** | `locked` | `Account locked, unlock at x.com/account/access, then retry.` | Unlock the account, then retry |
| **423** | `verification_required` | `Verification required: Twitter is asking to verify this login.` | Log into the account manually once to clear it |
| **423** | `email_code` | `Verification required: Twitter wants a code sent to the account's email.` | Complete the email verification manually |
| **502** | `proxy_unreachable` | `The login proxy did not respond…` | Try a different proxy, or omit `proxy` |
| **400** | n/a | `Invalid proxy URL.` | Fix the `proxy` value |
| **422** | n/a | `Login did not complete. Try again.` | **Retry**: this usually succeeds on a second attempt |
| **503** | n/a | `Login service is temporarily unavailable. Try again shortly.` | Retry shortly |

**Most common:** `429 rate_limited` (the login IP was throttled, retry with a cleaner proxy or after a short wait) and `422` (retry usually clears it). If you supply your own `proxy`, a high-quality residential or mobile IP gives the best login success rate.

## Media Upload

**POST** `/twitter/media/upload`

| Status | Message | What to do |
|--------|---------|------------|
| **400** | `File size exceeds…` | Reduce the file size |
| **400** | Unsupported type | Use a supported format |
| **401** | Invalid `auth_token` | Re-mint the token |
| **502** | Temporary upload error | Retry |

**Limits:** images (PNG / JPG / GIF / WEBP) up to 5 MB · animated GIF up to 15 MB · video (MP4) up to 512 MB.

## Direct Messages

**POST** `/twitter/dm/send` · `/twitter/dm/list` · `/twitter/dm/conversation`

| Status | Code | Message | What to do |
|--------|------|---------|------------|
| **429** | 502 | `You've hit your daily message request limit. Subscribe to Premium for higher limits.` | Wait 24h, or use a Premium account |
| **403** | 476 | `Sender is not verified to send message requests` | The account can't send DM requests |
| **403** | 349 | `Cannot send messages to this user` | The recipient doesn't accept your DMs |
| **401** | 32 | `Could not authenticate you` | Re-mint the token |
| **404** | n/a | Conversation / user not found | Check the recipient |

## Reading data

**GET** `/twitter/tweet/detail` · `/twitter/user/tweets` · `/twitter/user/info` · `/twitter/user/followers` · `/twitter/user/following` · `/twitter/tweet/thread` · `/twitter/tweet/replies` · `/twitter/user/search` · and all other read endpoints

| Status | Message | What to do |
|--------|---------|------------|
| **404** | `Tweet not found: <id>` | The tweet was deleted, is protected, or the ID is wrong |
| **404** | `Could not resolve userId for @<handle>` | The handle doesn't exist, was renamed, or is suspended |
| **404** | `Could not find user with ID: <id>` | Check the user ID |
| **400** | `Missing required query param: <x>` | Provide the required parameter |
| **429** | Rate limit | Wait `retry_after`, then retry |

**Region-restricted content.** If a tweet shows "Due to local regulations, this content is restricted on X" in your browser, that's a **regional block on your location**, not an API error, the API can still return it. If you route the request through your own `proxy` that exits in the restricted country, the same regional block applies. Use no proxy, or a proxy in an unrestricted region.

## Spaces

**GET** `/twitter/spaces/info` · **POST** `/twitter/spaces/download`

| Status | Message | What to do |
|--------|---------|------------|
| **404** | `Space not found` | Use the **Space** URL (not a tweet URL); the Space may have expired |
| **400** | Missing `space_url` | Provide the Space URL |
| **200** | `"downloadable": false` | Not an error, this Space has no downloadable audio |

## Articles

**GET** `/twitter/article/get` · **POST** `/twitter/article/create|update|publish|unpublish|delete|list`

| Status | Message | What to do |
|--------|---------|------------|
| **403** | Premium required | Articles require an X Premium account |
| **404** | Article not found | Check the article ID |
| **401** | Invalid `auth_token` | Re-mint the token |
| **400** | Invalid content | Fix the article body |

## Retry guide

| You see… | Retry? | Notes |
|----------|--------|-------|
| **429** | ✅ after `retry_after` / short wait | You hit a rate limit |
| **422** (login) | ✅ | Usually succeeds on the next attempt |
| **500 / 502 / 503** | ✅ | Temporary, retry shortly |
| **226** | ✅ | Retry |
| **401** | ❌ | Fix your API key or re-mint the `auth_token` |
| **403** (suspended/locked) | ❌ | Use a different account, or unlock it first |
| **404** | ❌ | Check the ID/handle |
| **400 / 409** | ❌ | Fix the request (params, media size, duplicate text) |

**Tip:** Build retry-with-backoff for `429`, `422` (login), and `5xx`. For `401`/`403`/`404`/`400`, don't retry, fix the input or the account first.
