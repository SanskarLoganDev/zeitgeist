"""
backend/apps/categories/models.py
───────────────────────────────────
Purpose : Defines the data models for categories, subreddit configuration,
          and the mapping between categories and source adapters.

          Models:
            Category
              - The top-level interest areas: Tech, Gaming, News, etc.
              - Self-referential FK (parent) enables subcategories — the FK
                exists from day 1 so migrations don't need retrofitting, but
                the subcategory UI is not activated until Phase 2.
              - slug field used in all API URLs: /api/v1/categories/gaming/

            SubredditConfig
              - Maps a subreddit name to a Category.
              - Stored in the DB (not hardcoded) so admins can add/remove
                subreddits without a code deploy (FR-20).
              - Example: { category: Gaming, subreddit: "pcgaming", active: True }

            CategorySourceConfig
              - Maps a Category to a source adapter (reddit, hackernews, youtube…)
              - Controls which adapters run for which category during ingestion.
              - Example: { category: Tech, source: "hackernews", active: True }

            UserCategoryPreference
              - Join table: which categories a user has selected for their dashboard.
              - Created during onboarding (Phase 3) or inline edit (Phase 2, FR-03).

Used by : apps/categories/views.py   — CategoryListView, PreferencesView
          apps/ingestion/orchestrator.py — reads CategorySourceConfig to know
                                           which adapters to run per category
          apps/ingestion/adapters/reddit.py — reads SubredditConfig to get subreddit list
          apps/trends/views.py       — reads UserCategoryPreference to filter dashboard
          Django admin               — admins edit SubredditConfig and CategorySourceConfig

Phase    : 1 — Week 2
"""
# Implementation coming in Phase 1 Week 2
