# Advanced Search

Search tweets with advanced operators using GetXAPI. $0.001 per call, ~20 tweets per call, just $0.05 per 1,000 tweets. Twitter API search endpoint with code examples.

GET`/twitter/tweet/advanced_search`Try it

This endpoint costs `$0.001` per API call and returns ~20 tweets per page.

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query (supports advanced operators) |
| `product` | enum | No | `Latest` (default) or `Top` |
| `cursor` | string | No | Pagination cursor |

## Limits and Behaviour

- Returns up to 20 tweets per page; use `cursor` to page further.
- Paginate with `next_cursor` from the previous response and stop when `has_more` is `false`.
- Each page is a separate billable call at `$0.001`.
- For large historical pulls, split the query into `since:`/`until:` date-range chunks rather than paging one long cursor chain.
- `q` must be URL-encoded: `min_faves:1000` becomes `min_faves%3A1000` and spaces become `+`.
- Supports the full web advanced search operator set. Syntax walkthrough with tested examples: [Twitter advanced search operators guide](https://www.getxapi.com/blogs/twitter-advanced-search-operators). Community operator reference: [https://github.com/igorbrigadir/twitter-advanced-search](https://github.com/igorbrigadir/twitter-advanced-search)

## Query Examples

- `from:elonmusk`, tweets from elonmusk
- `"AI" OR "crypto" from:elonmusk`, tweets containing AI or crypto
- `from:elonmusk since:2024-01-01`, tweets since Jan 1, 2024
- `to:elonmusk`, tweets replying to elonmusk
- `#crypto min_faves:100`, tweets with at least 100 likes
- `solana memecoin`, tweets mentioning solana and memecoin

## Response (200)

```json
{
  "query": "from:0xsweep",
  "tweet_count": 20,
  "has_more": true,
  "next_cursor": "DAABCgABG...",
  "tweets": [
    {
      "type": "tweet",
      "id": "2015410770834591992",
      "url": "https://x.com/0xsweep/status/2015410770834591992",
      "twitterUrl": "https://twitter.com/0xsweep/status/2015410770834591992",
      "text": "Thread on the latest memecoin trends...",
      "source": "Twitter Web App",
      "retweetCount": 12,
      "replyCount": 5,
      "likeCount": 89,
      "quoteCount": 3,
      "viewCount": 4500,
      "createdAt": "Sun Jan 25 13:05:46 +0000 2026",
      "lang": "en",
      "bookmarkCount": 10,
      "isReply": false,
      "inReplyToId": null,
      "conversationId": "2015410770834591992",
      "media": [],
      "inReplyToUserId": null,
      "author": {
        "type": "user",
        "userName": "0xsweep",
        "url": "https://x.com/0xsweep",
        "id": "1234567890",
        "name": "Sweep",
        "isVerified": false,
        "isBlueVerified": true,
        "profilePicture": "https://pbs.twimg.com/profile_images/...",
        "coverPicture": "https://pbs.twimg.com/profile_banners/...",
        "description": "Crypto researcher",
        "location": "",
        "followers": 15000,
        "following": 500,
        "createdAt": "Mon Jan 01 00:00:00 +0000 2022"
      },
      "quoted_tweet": null
    }
  ]
}
```

## Errors

| Status | Meaning |
|--------|---------|
| `400` | Missing or empty `q`, or an invalid `product` value |
| `401` | Missing, malformed, or revoked API key in the `Authorization` header |
| `402` | Credit balance exhausted. Top up, then retry |

### 400 - Missing q

```json
{
  "error": "Missing required query param: q"
}
```

An empty `tweets` array with `has_more: false` is a successful response, not an error: it means the query is valid but matched nothing.

## Example

```bash
# Latest tweets
curl -H "Authorization: Bearer API_KEY" "https://api.getxapi.com/twitter/tweet/advanced_search?q=from:0xsweep&product=Latest"

# Top tweets
curl -H "Authorization: Bearer API_KEY" "https://api.getxapi.com/twitter/tweet/advanced_search?q=from:0xsweep&product=Top"

# With pagination
curl -H "Authorization: Bearer API_KEY" "https://api.getxapi.com/twitter/tweet/advanced_search?q=from:0xsweep&product=Latest&cursor=DAABCgABG..."
```

```javascript
const response = await fetch(
  "https://api.getxapi.com/twitter/tweet/advanced_search?q=from:0xsweep&product=Latest",
  {
    headers: { Authorization: "Bearer API_KEY" },
  }
);
const data = await response.json();
console.log(data.tweets);
```

```python
import requests

response = requests.get(
    "https://api.getxapi.com/twitter/tweet/advanced_search",
    params={"q": "from:0xsweep", "product": "Latest"},
    headers={"Authorization": "Bearer API_KEY"})
print(response.json()["tweets"])
```
