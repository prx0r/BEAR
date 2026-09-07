# Tweet Thread

Resolve a linear Twitter/X self-thread from any tweet in the thread. $0.005 per call. GetXAPI tweet thread endpoint documentation.

GET`/twitter/tweet/thread`Try it

This endpoint costs `$0.005` per API call and returns the ordered self-thread for a tweet.

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Numeric tweet id. Can be the root tweet or any tweet in the thread. |

## Notes

- Resolves the conversation root automatically, so mid-thread tweet ids return the full thread from the first tweet.
- Follows `inReplyToId` links from the root author and excludes side replies from other users or replies the author made to commenters.
- `complete` is `false` only when the internal pagination cap is reached on a very long thread.
- Pool-based read: no customer `auth_token` or proxy parameter is needed.

## Response (200)

```json
{
  "conversationId": "2057796375233073524",
  "author": {
    "type": "user",
    "id": "123456789",
    "userName": "thedefiedge",
    "name": "The Defi Edge"
  },
  "thread_length": 2,
  "complete": true,
  "tweets": [
    {
      "type": "tweet",
      "id": "2057796375233073524",
      "text": "Thread opener...",
      "conversationId": "2057796375233073524",
      "inReplyToId": null,
      "author": {
        "id": "123456789",
        "userName": "thedefiedge",
        "name": "The Defi Edge"
      }
    },
    {
      "type": "tweet",
      "id": "2057796380000000000",
      "text": "Thread continuation...",
      "conversationId": "2057796375233073524",
      "inReplyToId": "2057796375233073524",
      "author": {
        "id": "123456789",
        "userName": "thedefiedge",
        "name": "The Defi Edge"
      }
    }
  ]
}
```

## Error Responses

### 400 - Missing or invalid id

```json
{ "error": "Missing required query param: id" }
```

```json
{ "error": "id must be a numeric tweet id" }
```

## Example

```bash
curl -H "Authorization: Bearer API_KEY" "https://api.getxapi.com/twitter/tweet/thread?id=2057796375233073524"
```
