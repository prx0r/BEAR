# GetXAPI Documentation

Base URL: https://api.getxapi.com
Auth: Bearer token in Authorization header

## 73 Endpoints

### Tweets (/bin/bash.001/call unless noted)
- GET /twitter/tweet/advanced_search — Search tweets (/bin/bash.001)
- GET /twitter/tweet/detail — Single tweet (/bin/bash.001)
- GET /twitter/tweet/thread — Tweet thread (/bin/bash.005)
- GET /twitter/tweet/replies — Tweet replies (/bin/bash.001)
- GET /twitter/tweet/retweeters — Retweeters (/bin/bash.001)
- POST /twitter/tweet/create — Create tweet (/bin/bash.002)
- POST /twitter/tweet/edit — Edit tweet (/bin/bash.002)
- POST /twitter/tweet/favorite — Like tweet (/bin/bash.001)
- POST /twitter/tweet/retweet — Retweet (/bin/bash.001)

### Articles
- GET /twitter/article/get — Get article (/bin/bash.001)
- POST /twitter/article/create — Create article (/bin/bash.01)
- POST /twitter/article/update — Update article (/bin/bash.005)
- POST /twitter/article/list — List articles (/bin/bash.005)
- POST /twitter/article/publish — Publish (/bin/bash.005)
- POST /twitter/article/unpublish — Unpublish (/bin/bash.005)
- POST /twitter/article/delete — Delete (/bin/bash.005)

### Users (/bin/bash.001/call unless noted)
- GET /twitter/user/search — Search users
- GET /twitter/user/status — User status
- GET /twitter/user/info — User info
- GET /twitter/user/info_by_id — User info by ID
- GET /twitter/user/user_about — User about
- GET /twitter/user/tweets — User tweets
- GET /twitter/user/tweets_and_replies — User tweets & replies
- GET /twitter/user/tweets/complete — User tweets complete (/bin/bash.003)
- GET /twitter/user/media — User media
- POST /twitter/user/likes — User likes
- GET /twitter/user/followers — Followers
- GET /twitter/user/followers_v2 — Followers v2
- GET /twitter/user/following — Following
- GET /twitter/user/following_v2 — Following v2
- GET /twitter/user/verified_followers — Verified followers
- POST /twitter/user/followers_you_know — Followers you know
- GET /twitter/user/check_follow_relationship — Check relationship
- POST /twitter/user/follow — Follow user
- POST /twitter/user/unfollow — Unfollow user
- POST /twitter/user/home_timeline — Home timeline
- POST /twitter/user/bookmark_search — Bookmark search
- GET /twitter/user/affiliates — User affiliates
- POST /twitter/user_login — User login (/bin/bash.01)
- POST /twitter/user_login_v2 — User login v2 (/bin/bash.005)
- POST /twitter/reset-password/send-code — Reset password send (/bin/bash.005)
- POST /twitter/reset-password/confirm — Reset password confirm (/bin/bash.005)

### Lists
- GET /twitter/list/members — List members (/bin/bash.001)

### DM
- POST /twitter/dm/send — Send DM (/bin/bash.002)
- POST /twitter/dm/list — List DMs (/bin/bash.002)

### Media
- POST /twitter/media/upload — Upload media (/bin/bash.001)

### Community
- GET /twitter/community/info — Community info (/bin/bash.001)
- POST /twitter/community/join — Join community (/bin/bash.002)

### Spaces
- GET /twitter/spaces/info — Space info (/bin/bash.001)
- POST /twitter/spaces/download — Download space (/bin/bash.05 + /bin/bash.015/min)

### Trends
- GET /twitter/trends — Get trends (/bin/bash.001)
- GET /twitter/trends/locations — Trend locations (/bin/bash.001)

### Notifications
- POST /twitter/notifications — Notifications (/bin/bash.002)

### Account (Free)
- GET /account/me — Account info
- GET /account/payments — Payment history

## Pricing
- Most read endpoints: /bin/bash.001/call (~20 tweets, so /bin/bash.05/1K tweets)
- User Tweets Complete: /bin/bash.003/call
- Tweet Thread: /bin/bash.005/call
- DM endpoints: /bin/bash.002/call
- No subscription required
- No endpoint-specific quotas
- Free /bin/bash.10 credit on signup (~2,000 tweets)

## Pagination
- Cursor-based: pass next_cursor from response
- ~20 items per page (some endpoints up to 200)
- Stop when has_more is false

## Historical Data
- Supports since:/until: date operators
- Tested: works from 2024 onwards
- Before 2024: unclear, may have gaps
