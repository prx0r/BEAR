# User Tweets

Fetch all tweets posted by a Twitter user via API. $0.001 per call, ~20 tweets per call, just $0.05 per 1,000 tweets. GetXAPI user tweets endpoint.

GET`/twitter/user/tweets`Try it

This endpoint costs `$0.001` per API call and returns ~20 tweets per page.

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `userName` | string | Conditional | Screen name (without @). Required if `userId` is not provided. |
| `userId` | string | Conditional | Numeric Twitter user ID. Required if `userName` is not provided. Faster than `userName` (~1s saved) since it skips the username-to-ID lookup. |
| `cursor` | string | No | Pagination cursor |

## Notes

- Provide either `userName` or `userId`, if both are given, `userId` takes priority.
- Using `userId` is recommended for high-throughput use cases as it skips an internal API call.
- Returns tweets posted by the user (their profile "Posts" tab). This is NOT their home feed, it only includes tweets they authored.
- Pagination uses `next_cursor` until `has_more` is false.
- Each tweet includes an `entities` object (`hashtags`, `symbols`, `timestamps`, `urls`, `user_mentions`) so you can read `expanded_url` directly without HEAD-resolving `t.co` links. Works for both standard tweets and Note Tweets.

## Response (200)

```json
{
  "userName": "example_user",
  "userId": "1234567890123456789",
  "tweet_count": 20,
  "has_more": true,
  "next_cursor": "DAABCgABHAY...",
  "tweets": [
    {
      "type": "tweet",
      "id": "2010705621524292007",
      "url": "https://x.com/example_user/status/2010705621524292007",
      "twitterUrl": "https://twitter.com/example_user/status/2010705621524292007",
      "text": "Check out our latest update https://t.co/abc123",
      "source": "Twitter Web App",
      "retweetCount": 3,
      "replyCount": 12,
      "likeCount": 87,
      "quoteCount": 1,
      "viewCount": 4521,
      "createdAt": "Mon Jan 12 13:44:55 +0000 2026",
      "lang": "en",
      "bookmarkCount": 6,
      "isReply": false,
      "inReplyToId": null,
      "conversationId": "2010705621524292007",
      "media": [
        {
          "type": "photo",
          "url": "https://pbs.twimg.com/media/abc123.jpg",
          "expanded_url": "https://x.com/example_user/status/2010705621524292007/photo/1",
          "video_url": null
        }
      ],
      "entities": {
        "hashtags": [],
        "symbols": [],
        "timestamps": [],
        "urls": [
          {
            "url": "https://t.co/abc123",
            "expanded_url": "https://docs.getxapi.com/changelog",
            "display_url": "docs.getxapi.com/changelog",
            "indices": [29, 52]
          }
        ],
        "user_mentions": []
      },
      "author": {
        "type": "user",
        "userName": "example_user",
        "url": "https://x.com/example_user",
        "id": "1234567890123456789",
        "name": "Example User",
        "isVerified": false,
        "isBlueVerified": true,
        "profilePicture": "https://pbs.twimg.com/profile_images/.../abc_normal.jpg",
        "coverPicture": "https://pbs.twimg.com/profile_banners/1234567890123456789/...",
        "description": "Building things on the internet",
        "location": "San Francisco, CA",
        "followers": 1280,
        "following": 312,
        "createdAt": "Fri Jan 01 23:45:21 +0000 2021"
      },
      "quoted_tweet": null
    }
  ]
}
```

## Error Responses

### 400 - Missing params

```json
{
  "error": "Missing required query param: userName or userId"
}
```

## Example

```bash
# By userName
curl -H "Authorization: Bearer API_KEY" "https://api.getxapi.com/twitter/user/tweets?userName=example_user"

# By userId (faster)
curl -H "Authorization: Bearer API_KEY" "https://api.getxapi.com/twitter/user/tweets?userId=44196397"

# With pagination
curl -H "Authorization: Bearer API_KEY" "https://api.getxapi.com/twitter/user/tweets?userId=44196397&cursor=DAABCgABHAY..."
```
