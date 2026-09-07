# Tweet Detail

Get a single tweet with full author, media, and engagement data via API. $0.001 per call. GetXAPI tweet detail endpoint with response examples.

GET`/twitter/tweet/detail`

This endpoint costs `$0.001` per API call.

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | Tweet id |

## Notes

- Returns a single tweet with full author and media details.

## Response (200)

```json
{
  "status": "success",
  "msg": "success",
  "data": {
    "type": "tweet",
    "id": "2019264360682778716",
    "url": "https://x.com/elonmusk/status/2019264360682778716",
    "twitterUrl": "https://twitter.com/elonmusk/status/2019264360682778716",
    "text": "@Gaurab Yes, it is extremely difficult",
    "source": "Twitter for iPhone",
    "retweetCount": 136,
    "replyCount": 396,
    "likeCount": 3676,
    "quoteCount": 11,
    "viewCount": 298555,
    "createdAt": "Thu Feb 05 04:18:34 +0000 2026",
    "lang": "en",
    "bookmarkCount": 121,
    "isReply": true,
    "inReplyToId": "2019199325365227607",
    "conversationId": "2019199325365227607",
    "media": [],
    "inReplyToUserId": "18433952",
    "author": {
      "type": "user",
      "userName": "elonmusk",
      "url": "https://x.com/elonmusk",
      "id": "44196397",
      "name": "Elon Musk",
      "isVerified": false,
      "isBlueVerified": true,
      "profilePicture": "https://pbs.twimg.com/profile_images/.../57KcqsTA_normal.jpg",
      "coverPicture": "https://pbs.twimg.com/profile_banners/44196397/...",
      "description": "",
      "location": "",
      "followers": 233932369,
      "following": 1283,
      "createdAt": "Tue Jun 02 20:12:29 +0000 2009"
    },
    "quoted_tweet": null
  }
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
curl -H "Authorization: Bearer API_KEY" "https://api.getxapi.com/twitter/tweet/detail?id=2019264360682778716"
```

```javascript
const response = await fetch(
  "https://api.getxapi.com/twitter/tweet/detail?id=2019264360682778716",
  {
    headers: { Authorization: "Bearer API_KEY" },
  }
);
const data = await response.json();
console.log(data);
```

```python
import requests

response = requests.get(
    "https://api.getxapi.com/twitter/tweet/detail",
    params={"id": "2019264360682778716"},
    headers={"Authorization": "Bearer API_KEY"},
)
print(response.json())
```
