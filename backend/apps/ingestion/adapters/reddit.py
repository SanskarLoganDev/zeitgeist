"""
backend/apps/ingestion/adapters/reddit.py
───────────────────────────────────────────
Purpose : Fetches trending posts from Reddit using the PRAW library (Python Reddit API Wrapper).

          For each category, reads the list of configured subreddits from SubredditConfig
          (stored in the DB, editable in Django admin — FR-20). Fetches the top N hot
          posts from each subreddit and normalises them into TrendItems.

          Normalised fields:
            title        → post title
            url          → link to the Reddit post (reddit.com/r/.../comments/...)
            source       → "reddit"
            score        → post upvotes
            score_label  → "upvotes"
            external_url → the URL the post links to (if it's a link post, not a text post)

          Rate limit: 60 requests/minute when authenticated via OAuth.
          Credentials: REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET from Secret Manager.

Used by : apps/ingestion/orchestrator.py — instantiated and called for categories
            where CategorySourceConfig has source="reddit"

Phase    : 1 — Week 2
"""
# Implementation coming in Phase 1 Week 2
