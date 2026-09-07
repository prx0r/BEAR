# User Followers

Get a Twitter user's followers list with profile details via API. $0.001 per call, ~200 users per call. GetXAPI followers endpoint docs.

GET`/twitter/user/followers`Try it

This endpoint costs `$0.001` per API call and returns ~200 users per page.

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userName` | string | Yes | Screen name (without @) |
| `cursor` | string | No | Pagination cursor |

## Notes

- Uses the REST followers endpoint.
- Returns up to 200 followers per page (ordered by follow time desc).
- **No total-user cap**: you can paginate all the way through to the full follower list. Use this endpoint when you need the complete list.

## Response

```json
{
  "userName": "elonmusk",
  "user_count": 200,
  "has_more": true,
  "next_cursor": "DAABCgABG...",
  "followers": [
    {
      "type": "user",
      "id": "1335924847940079620",
      "userName": "0xumarkhatab",
      "name": "Umar",
      "url": "https://x.com/0xumarkhatab",
      "isVerified": false,
      "isBlueVerified": true,
      "profilePicture": "https://pbs.twimg.com/profile_images/...",
      "coverPicture": "https://pbs.twimg.com/profile_banners/...",
      "description": "Founding EVM Engineer @ViFi_Labs",
      "location": "Metaverse",
      "followers": 599,
      "following": 307,
      "tweets": 2002,
      "listed": 12,
      "createdAt": "Mon Dec 07 12:32:21 +0000 2020",
      "canDm": false
    }
  ]
}
```

## Example

```bash
curl -H "Authorization: Bearer API_KEY" "https://api.getxapi.com/twitter/user/followers?userName=elonmusk"

# With pagination
curl -H "Authorization: Bearer API_KEY" "https://api.getxapi.com/twitter/user/followers?userName=elonmusk&cursor=DAABCgABG..."
```
