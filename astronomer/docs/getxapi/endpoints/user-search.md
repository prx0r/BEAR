# Search Users

Search for Twitter/X users by keyword, username, or topic. $0.001 per call, ~20 users per call. GetXAPI user search endpoint with pagination.

GET`/twitter/user/search`Try it

This endpoint costs `$0.001` per API call and returns ~20 users per page.

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `q` | string | Yes | Search query (username, keyword, or topic) |
| `cursor` | string | No | Pagination cursor from previous response |

## Notes

- Searches for Twitter users matching the query (equivalent to the "People" tab in Twitter search).
- Returns up to 20 users per page.
- Pagination uses `next_cursor` until `has_more` is false.

## Response (200)

```json
{
  "query": "@eigencloud",
  "user_count": 20,
  "has_more": true,
  "next_cursor": "DAAFCgABHDho...",
  "users": [
    {
      "type": "user",
      "id": "3185716686",
      "userName": "AshCrypto",
      "name": "Ash Crypto",
      "url": "https://x.com/AshCrypto",
      "isVerified": false,
      "isBlueVerified": true,
      "profilePicture": "https://pbs.twimg.com/profile_images/.../h_vgXOAw_400x400.jpg",
      "coverPicture": "https://pbs.twimg.com/profile_banners/3185716686/...",
      "description": "News, Memes, Charts, Hopium, Market analysis and Latest crypto updates.",
      "location": "X",
      "followers": 2148334,
      "following": 342,
      "tweets": 28986,
      "listed": 7544,
      "createdAt": "Tue May 05 02:01:09 +0000 2015",
      "canDm": true
    }
  ]
}
```

## Error Responses

### 400 - Missing q

```json
{
  "error": "Missing required query param: q"
}
```

## Examples

```bash
curl -X GET "https://api.getxapi.com/twitter/user/search?q=crypto" \
  -H "Authorization: Bearer API_KEY"

# Search by username
curl -X GET "https://api.getxapi.com/twitter/user/search?q=@eigencloud" \
  -H "Authorization: Bearer API_KEY"

# With pagination
curl -X GET "https://api.getxapi.com/twitter/user/search?q=crypto&cursor=DAAFCgABHDho..." \
  -H "Authorization: Bearer API_KEY"
```

```javascript
const response = await fetch(
  "https://api.getxapi.com/twitter/user/search?q=crypto",
  {
    headers: {
      Authorization: "Bearer API_KEY",
    },
  }
);
const data = await response.json();
console.log(data);
```

```python
import requests

response = requests.get(
    "https://api.getxapi.com/twitter/user/search",
    headers={"Authorization": "Bearer API_KEY"},
    params={"q": "crypto"},
)
print(response.json())
```
