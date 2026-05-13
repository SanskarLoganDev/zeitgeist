# TrendPulse — Requirements Document

**Version:** 1.0  
**Status:** Approved  
**Last Updated:** 2026-05-11

---

## 1. Project Overview

TrendPulse is a personalised social media and internet trend aggregation platform. It collects trending content daily from multiple public data sources — Reddit, Hacker News, YouTube, arXiv, PubMed, TMDB, Steam, and NASA — normalises it into a unified data model, and surfaces it to users through a categorised, searchable dashboard. An AI layer (Google Gemini) generates plain-English summaries of what is trending and why, and detects when the same topic surfaces across multiple platforms simultaneously.

### 1.1 Problem Statement

There is no single place for a person to see what is genuinely trending across their specific areas of interest — whether that is gaming, academic research, finance, or space exploration. Existing tools either cover a single platform (Reddit apps), require paid subscriptions (media monitoring tools), or surface noise rather than signal. TrendPulse solves this by aggregating multiple high-quality public sources, applying AI to summarise and contextualise trends, and delivering a personalised experience based on each user's interests.

### 1.2 Target Users

| User Type | Description |
|---|---|
| General consumer | Wants a daily digest of what is trending in their areas of interest |
| Developer / researcher | Wants to track trends in Tech, Research, and AI specifically |
| Student | Wants to stay informed on News, Health, Science categories |
| Enthusiast | Heavy focus on a specific domain — Gaming, Space, TV/Movies etc. |

### 1.3 Non-Goals (explicitly out of scope)

- Real-time trend updates (sub-hourly refresh)
- User-generated content or social features (commenting, sharing within the app)
- Paid content or paywalled data sources
- Mobile native apps (iOS / Android)
- Financial trading signals or investment advice

---

## 2. Data Sources

All data sources are free and publicly accessible. No proprietary or paywalled APIs are used.

| Source | Categories Served | API / Access Method | Rate Limit |
|---|---|---|---|
| Reddit (PRAW) | News, Gaming, Finance, Space, Food, TV/Movies | OAuth API — 60 req/min | 60 req/min authenticated |
| Hacker News API | Tech, Research, Finance | Free Firebase API — no auth | No rate limit |
| YouTube Data API | Gaming, TV/Movies, Food | OAuth API key | 10,000 units/day |
| arXiv API | Research, AI, Space, Health | Free REST API — no auth | Polite crawling |
| PubMed / NCBI | Health, Research | Free E-utilities API | 10 req/sec with API key |
| TMDB API | TV/Movies | Free API key | 40 req/10 sec |
| Steam Spy + IGDB | Gaming | Free / Twitch OAuth | Varies |
| NASA Open APIs | Space | Free API key | 1,000 req/hour |
| Google Trends (pytrends) | All categories (historical) | Unofficial scraper library | Soft limit — batch carefully |

### 2.1 Subreddit Configuration

Subreddits are curated manually and stored in the database. They are editable in the Django admin panel without a code deploy. Initial set:

| Category | Subreddits |
|---|---|
| Tech | r/technology, r/programming, r/webdev, r/MachineLearning, r/artificial, r/netsec |
| Gaming | r/gaming, r/pcgaming, r/Games, r/gamedev, r/indiegaming |
| News | r/worldnews, r/news, r/UpliftingNews, r/politics, r/science |
| Finance | r/personalfinance, r/stocks, r/CryptoCurrency, r/investing |
| Health | r/health, r/nutrition, r/fitness, r/mentalhealth |
| Space | r/space, r/SpaceX, r/Astronomy, r/astrophysics |
| Research | r/MachineLearning, r/datascience, r/science, r/AskScience |
| TV/Movies | r/television, r/movies, r/netflix, r/anime |
| Food | r/food, r/recipes, r/MealPrepSunday, r/EatCheapAndHealthy |

---

## 3. Functional Requirements

Requirements are tagged with their priority tier and the phase in which they will be implemented.

**Priority tiers:**
- **M** — Must Have (core, non-negotiable)
- **C** — Could Have (valuable, implemented after core is stable)

---

### 3.1 Authentication (FR-AUTH)

| ID | Priority | Phase | Requirement |
|---|---|---|---|
| FR-01 | M | 1 | The system shall allow users to register and log in using Google OAuth. Session shall be managed via JWT stored in an HTTP-only cookie. |
| FR-02 | C | 3 | On first login, the system shall present an interest onboarding flow where the user selects at least 3 categories. The flow is skippable; skipping defaults to all categories. |
| FR-03 | M | 2 | The user shall be able to edit their category preferences directly from the dashboard via an inline sidebar or modal — without navigating to a settings page. |

---

### 3.2 Dashboard & Display (FR-DASH)

| ID | Priority | Phase | Requirement |
|---|---|---|---|
| FR-04 | M | 1 | The system shall display a home dashboard showing the top 5 trending items per category for each of the user's selected categories. |
| FR-05 | M | 1 | The user shall be able to drill into any category to see a full ranked list of 10–20 trending items for that category. |
| FR-06 | M | 1 | Each trend card shall display: title, source platform badge, score/metric (upvotes, views, or citations depending on source), a link to the original content, and — from Phase 2 — an AI-generated one-line summary. |
| FR-07 | C | 2 | The user shall be able to filter trends by time window: today, last 7 days, last 30 days, last 90 days. Only time windows with existing snapshot data shall be selectable. |
| FR-08 | C | 2 | Each category page shall display a trend chart showing relative topic interest over the available time window. The chart shall use stored snapshots for recent windows and Google Trends data for long-term historical curves. |
| FR-09 | M | 2 | The user shall be able to filter which source platforms are shown (e.g. Reddit only, HN only, all sources). This filter operates on already-fetched data — it does not trigger new API calls. |
| FR-10 | C | 3 | The system shall surface a "trending everywhere" card at the top of a category when the same topic is detected trending on two or more platforms simultaneously. |

---

### 3.3 Data Ingestion (FR-INGEST)

| ID | Priority | Phase | Requirement |
|---|---|---|---|
| FR-11 | M | 1 | The system shall automatically fetch trend data from all configured sources once per day at 03:00 UTC via Cloud Scheduler. No manual trigger shall be required for normal operation. |
| FR-12 | M | 1 | Each ingestion run shall store a timestamped snapshot of the top items per category. This snapshot data is the basis for all historical trend views. Snapshot storage begins from the first run — retroactive collection is not possible. |
| FR-13 | M | 1 | If a source API fails or rate-limits during ingestion, the system shall log the failure, skip that source, continue with remaining sources, and serve the most recent successful snapshot for the affected category with a visible "last updated X hours ago" indicator. |

---

### 3.4 AI Features (FR-AI)

| ID | Priority | Phase | Requirement |
|---|---|---|---|
| FR-14 | M | 2 | The system shall generate a natural-language trend summary per category once per daily ingestion run using Google Gemini. The summary shall describe what is trending and why. It shall be stored in the database and displayed at the top of each category page. Gemini shall not be called per user request — only during the batch ingestion job. |
| FR-15 | C | 3 | Post-ingestion, the system shall run a cross-platform topic detection job using Vertex AI text embeddings to identify semantically similar topics trending across multiple sources. Results shall be stored and surfaced via FR-10. |
| FR-16 | C | 3 | Each trending item shall be tagged with a sentiment label — Positive, Negative, or Neutral — computed by Gemini during the ingestion run. The label shall be displayed as a colour-coded badge on trend cards. |

---

### 3.5 Notifications (FR-NOTIF)

| ID | Priority | Phase | Requirement |
|---|---|---|---|
| FR-18 | M | 3 | The system shall send each user a weekly personalised digest email every Monday at 08:00 UTC. The email shall summarise the top 5 trends per subscribed category over the past 7 days in plain English, generated by Gemini. Delivery shall be via SendGrid. |

---

### 3.6 Administration (FR-ADMIN)

| ID | Priority | Phase | Requirement |
|---|---|---|---|
| FR-19 | M | 1 | The Django admin panel shall display a log of all ingestion runs: source, items fetched, status (success/failure), error message if applicable, and timestamp. Admins shall be able to manually trigger a re-fetch for a specific source. |
| FR-20 | C | 2 | Categories, subcategories, and the subreddit list per category shall be configurable via the Django admin panel without a code deploy. New categories that use existing source adapters (Reddit, HN, YouTube, arXiv) shall require only admin configuration. New source types require a code deploy. |

---

## 4. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | Dashboard API responses shall return in under 1 second. All trend data is pre-computed at ingestion time and served from cache — no live external API calls on user request. |
| NFR-02 | Trend data shall be at most 24 hours stale. Each category page shall display a visible "last updated" timestamp. |
| NFR-03 | If a data source fails, the failure shall not cascade to other sources or crash the ingestion job. Each adapter runs independently. |
| NFR-04 | All API calls shall respect the rate limits of each source. The ingestion scheduler shall budget calls per source accordingly. |
| NFR-05 | During Phase 1 and Phase 2, the Next.js frontend runs on localhost. The Django backend is deployed on GCP Cloud Run and accessible over HTTPS. CORS shall allow localhost:3000 during development. |
| NFR-06 | All Gemini API calls shall occur only during the nightly ingestion batch job — never per user request. AI cost is fixed and predictable regardless of user count. |
| NFR-07 | All API keys, credentials, and secrets shall be stored in GCP Secret Manager. They shall never be hardcoded in source code or committed to the repository. |
| NFR-08 | Every push to the main branch shall trigger the CI/CD pipeline: lint (ruff), type check (mypy), tests (pytest), Docker build, push to Artifact Registry, deploy to Cloud Run. |
| NFR-09 | The system shall be deployable entirely on GCP free tier or near-free tier during development. Production costs at small scale (< 500 DAU) shall not exceed $30/month. |

---

## 5. Categories & Subcategory Model

Subcategories are defined in the data model from Phase 1 (self-referential FK on Category) but the UI for subcategory browsing is not activated until Phase 2 or later.

| Category | Planned Subcategories (Phase 2+) |
|---|---|
| Tech | AI/ML, Web Dev, Security, Mobile, Open Source |
| Gaming | RPG, FPS, Indie, Mobile, Game Dev |
| News | World, Technology, Science, Politics, Uplifting |
| Finance | Stocks, Crypto, Personal Finance, Economy |
| Health | Mental Health, Nutrition, Fitness, Medical |
| Space | NASA, SpaceX, Astronomy, Astrophysics |
| Research | Computer Science, Biology, Physics, Mathematics |
| TV/Movies | Netflix, HBO/Max, Anime, Bollywood, Hollywood |
| Food | Recipes, Meal Prep, Restaurants, Diet |

---

## 6. Removed Requirements

| ID | Requirement | Reason Removed |
|---|---|---|
| FR-17 | Topic alerts (notify when a keyword trends) | Descoped — adds significant complexity (background monitoring, threshold logic, per-user matching) for a feature that overlaps with the weekly digest. Can be added post-launch if demand exists. |

---

*End of Requirements Document*
