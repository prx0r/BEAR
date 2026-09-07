# Account Info

Get your GetXAPI account details, credit balance, and usage summary via API. Free endpoint, 30 requests/min.

GET`/account/me`Try it

This endpoint is **free** (no credits deducted). Rate limited to **30 requests per minute** per API key.

## Notes

- Returns your GetXAPI account details, credit balances, and usage summary.
- Uses the same `Authorization: Bearer <API_KEY>` header as the Twitter endpoints.
- Free to call, no credits consumed.
- **Two balances.** `credits_remaining` is your permanent top-up wallet. `plan_credits_remaining` is the expiring allowance from a subscription. Plan credits are spent **first**, then the wallet. Use `balance_total` for what you can actually spend right now.

## Response (200)

```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "credits_remaining": 2.26,
  "credits_used": 13.832,
  "total_requests": 12251,
  "created_at": "2026-02-06T10:46:59.399986+00:00",
  "plan_name": "pro_sub",
  "plan_credits_total": 40,
  "plan_credits_remaining": 27.57,
  "plan_credits_expires_at": "2026-08-26",
  "plan_credits_expired": false,
  "balance_total": 29.83
}
```

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | Account email |
| `name` | string | Account name |
| `credits_remaining` | number | **Top-up wallet** balance ($). Permanent, never expires |
| `credits_used` | number | Total credits spent ($) |
| `total_requests` | number | Total API calls made |
| `created_at` | string | Account registration date (ISO 8601) |
| `plan_name` | string | Active subscription plan id, or `null` when there is no plan |
| `plan_credits_total` | number | **Opening** plan-credit balance for the current cycle. See the note below |
| `plan_credits_remaining` | number | Plan credits left this cycle ($) |
| `plan_credits_expires_at` | string | Date the plan credits lapse (`YYYY-MM-DD`) |
| `plan_credits_expired` | boolean | `true` when the plan credits are past their expiry and no longer spendable |
| `balance_total` | number | `credits_remaining` + **unexpired** `plan_credits_remaining`. What you can spend now |

**`plan_credits_total` is the opening balance, not the plan's advertised allowance.** A renewal stacks your unused credits underneath the new grant, so a Pro plan advertising $30 can open a cycle at $42 if you carried $12 over. This makes `plan_credits_total - plan_credits_remaining` your spend for the current cycle, which is usually what you want. To check the advertised allowance instead, read the [pricing page](https://www.getxapi.com/pricing).

**Plan credits expire, wallet credits do not.** Once `plan_credits_expires_at` passes, the remaining plan credits stop working. `plan_credits_remaining` may still show a non-zero figure briefly, so check `plan_credits_expired` or just use `balance_total`, which already excludes them.

## Error Responses

### 429 - Rate limited

```json
{
  "error": "Too many requests. Limit: 30 per minute."
}
```

## Examples

```bash
curl -X GET "https://api.getxapi.com/account/me" \
  -H "Authorization: Bearer API_KEY"
```

```javascript
const response = await fetch("https://api.getxapi.com/account/me", {
  headers: { Authorization: "Bearer API_KEY" },
});
const data = await response.json();
console.log(data);
```

```python
import requests

response = requests.get(
    "https://api.getxapi.com/account/me",
    headers={"Authorization": "Bearer API_KEY"})
print(response.json())
```
