# Tweet Replies

Fetch all replies to a tweet via API. $0.001 per call, ~20 replies per call. GetXAPI tweet replies endpoint documentation.

GET`/twitter/tweet/replies`Try it

This endpoint costs `$0.001` per API call and returns ~20 replies per page.

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Tweet id |
| `cursor` | string | No | Pagination cursor |

## Notes

- Returns replies for a tweet.
- Pagination uses `next_cursor` until `has_more` is false.

## Response (200)

```json
{
  "tweetId": "2019199325365227607",
  "reply_count": 38,
  "has_more": false,
  "next_cursor": null,
  "replies": [
    {
      "type": "tweet",
      "id": "2019264360682778716",
      "url": "https://x.com/elonmusk/status/2019264360682778716",
      "text": "@Gaurab Yes, it is extremely difficult",
      "likeCount": 3718,
      "replyCount": 396,
      "viewCount": 300017,
      "author": {
        "userName": "elonmusk",
        "name": "Elon Musk"
      }
    }
  ]
}
```

## Error Responses

### 400 - Missing id

```json
{
  "error": "Missing required query param: id"
}
```

## Example

```bash
curl -H "Authorization: Bearer API_KEY" "https://api.getxapi.com/twitter/tweet/replies?id=2019199325365227607"

# With pagination
curl -H "Authorization: Bearer API_KEY" "https://api.getxapi.com/twitter/tweet/replies?id=2019199325365227607&cursor=DAABCgABG..."
```
