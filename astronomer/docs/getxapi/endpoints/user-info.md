# User Info

Get Twitter user profiles, followers, verified status via API. $0.001 per call. GetXAPI user info endpoint documentation with examples.

GET`/twitter/user/info`Try it

This endpoint costs `$0.001` per API call.

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userName` | string | Yes | Screen name (without @) |

## Notes

- Returns full profile information for a Twitter user.
- No pagination needed - returns complete profile in one call.

## Response

```json
{
  "status": "success",
  "msg": "success",
  "data": {
    "id": "1234567890123456789",
    "name": "Example User",
    "userName": "example_user",
    "location": "Worldwide",
    "url": "https://example.com/",
    "description": "Building on GetXAPI.",
    "protected": false,
    "isVerified": false,
    "isBlueVerified": true,
    "verifiedType": null,
    "followers": 229,
    "following": 233,
    "favouritesCount": 4079,
    "statusesCount": 986,
    "mediaCount": 113,
    "createdAt": "2021-01-01T23:45:21.000000Z",
    "coverPicture": null,
    "profilePicture": "https://pbs.twimg.com/profile_images/.../pj0DTqs2_400x400.jpg",
    "canDm": false,
    "pinnedTweetIds": []
  }
}
```

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique user ID |
| `name` | string | Display name |
| `userName` | string | @handle (screen name) |
| `location` | string | User's location |
| `url` | string | Website URL (expanded) |
| `description` | string | Bio |
| `protected` | boolean | Is account private? |
| `isVerified` | boolean | Legacy verification |
| `isBlueVerified` | boolean | Twitter Blue subscriber |
| `verifiedType` | string | Verification type (usually null) |
| `followers` | number | Follower count |
| `following` | number | Following count |
| `favouritesCount` | number | Likes count |
| `statusesCount` | number | Tweet count |
| `mediaCount` | number | Media posts count |
| `createdAt` | string | Account creation date (ISO 8601) |
| `coverPicture` | string | Banner image URL |
| `profilePicture` | string | Avatar URL (400x400) |
| `canDm` | boolean | Can receive DMs |
| `pinnedTweetIds` | array | IDs of pinned tweets |

## Error Responses

### 404 - User not found

```json
{
  "error": "Could not find user @nonexistent_user"
}
```

## Example

```bash
curl -H "Authorization: Bearer API_KEY" "https://api.getxapi.com/twitter/user/info?userName=example_user"
```

```javascript
const response = await fetch(
  "https://api.getxapi.com/twitter/user/info?userName=example_user",
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
    "https://api.getxapi.com/twitter/user/info",
    params={"userName": "example_user"},
    headers={"Authorization": "Bearer API_KEY"},
)
print(response.json())
```
