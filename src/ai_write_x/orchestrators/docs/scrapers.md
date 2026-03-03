---
layout: default
title: Source Scrapers
---

# Source Scrapers

Horizon fetches content from four source types. All scrapers inherit from `BaseScraper`, share an async HTTP client, and implement a `fetch(since)` method that returns a list of `ContentItem` objects. Sources are fetched concurrently via `asyncio.gather`.

## Hacker News

**File**: `src/scrapers/hackernews.py`

Uses the [Firebase HN API](https://hacker-news.firebaseio.com/v0):

- `GET /topstories.json` — fetches top story IDs
- `GET /item/{id}.json` — fetches story/comment details

Stories and their comments are fetched concurrently. For each story, the top 5 comments are included (deleted/dead comments excluded, HTML stripped, truncated at 500 chars).

**Config** (`sources.hackernews`):

```json
{
  "enabled": true,
  "fetch_top_stories": 30,
  "min_score": 100
}
```

- `fetch_top_stories` — number of top story IDs to fetch
- `min_score` — minimum HN points to include a story

**Extracted data**: title, URL (falls back to HN discussion URL), author, score, comment count, and top comment text.

## GitHub

**File**: `src/scrapers/github.py`

Uses the [GitHub REST API](https://api.github.com):

- `GET /users/{username}/events/public` — user activity events
- `GET /repos/{owner}/{repo}/releases` — repository releases

Two source types are supported:

- **`user_events`** — tracks push, create, release, public, and watch events for a user
- **`repo_releases`** — tracks new releases for a specific repository

**Config** (`sources.github`, list of entries):

```json
{
  "type": "user_events",
  "username": "torvalds",
  "enabled": true
}
```

```json
{
  "type": "repo_releases",
  "owner": "golang",
  "repo": "go",
  "enabled": true
}
```

**Authentication**: Set `GITHUB_TOKEN` in your environment for higher rate limits (5000 req/hr vs 60 without).

## RSS

**File**: `src/scrapers/rss.py`

Fetches any Atom/RSS feed using the `feedparser` library. Tries multiple date fields (`published`, `updated`, `created`) with fallback parsing.

**Config** (`sources.rss`, list of entries):

```json
{
  "name": "Simon Willison",
  "url": "https://simonwillison.net/atom/everything/",
  "enabled": true,
  "category": "ai-tools"
}
```

- `category` — optional tag for grouping (e.g., `"programming"`, `"microblog"`)

**Extracted data**: title, URL, author, content (from `summary`/`description`/`content` fields), feed name, category, and entry tags.

## Reddit

**File**: `src/scrapers/reddit.py`

Uses Reddit's public JSON API (`www.reddit.com`):

- `GET /r/{subreddit}/{sort}.json` — subreddit posts
- `GET /user/{username}/submitted.json` — user submissions
- `GET /r/{subreddit}/comments/{post_id}.json` — post comments

Subreddits and users are fetched concurrently. Comments are sorted by score, limited to the configured count, and exclude moderator-distinguished comments. Self-text is truncated at 1500 chars, comments at 500 chars.

**Config** (`sources.reddit`):

```json
{
  "enabled": true,
  "fetch_comments": 5,
  "subreddits": [
    {
      "subreddit": "MachineLearning",
      "sort": "hot",
      "fetch_limit": 25,
      "min_score": 10
    }
  ],
  "users": [
    {
      "username": "spez",
      "sort": "new",
      "fetch_limit": 10
    }
  ]
}
```

- `sort` — `hot`, `new`, `top`, or `rising` (subreddits); `hot` or `new` (users)
- `time_filter` — for `top`/`rising` sorts: `hour`, `day`, `week`, `month`, `year`, `all`
- `min_score` — minimum post score (subreddits only)

**Rate limiting**: Detects HTTP 429 responses, reads the `Retry-After` header, waits, and retries once. Uses a descriptive `User-Agent` as required by Reddit's API guidelines.

**Extracted data**: title, URL, author, score, upvote ratio, comment count, subreddit, flair, self-text, and top comments.
