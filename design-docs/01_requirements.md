# Zeitgeist — Requirements Document

**Version:** 2.0  
**Status:** Revised after Phase 1 implementation decisions  
**Last Updated:** 2026-07-06

---

## 1. Project Overview

Zeitgeist is a personalised internet trend aggregation platform. It collects
trending content daily from verified public APIs, normalises it into a unified
data model, and surfaces it through a categorised dashboard. The current
verified baseline covers Tech, Gaming, and News through Hacker News, DEV, RAWG,
and New York Times Most Popular. An AI layer (Google Gemini) may generate
plain-English summaries of what is trending and why after the public dashboard
flow is stable.

### 1.1 Problem Statement

There is no single place for a person to see what is genuinely trending across
their specific areas of interest. Existing tools either cover a single platform,
require paid subscriptions, or surface noise rather than signal. Zeitgeist
solves this by aggregating verified public sources, storing daily snapshots, and
delivering a personalised experience based on each user's interests.

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

All active data sources must be verified with a live API fetch before code,
schema, secrets, or deployment wiring are added.

Verification must confirm:

1. Access method: public, API key, OAuth, approval-gated, or paid.
2. Response shape and required fields.
3. A usable trend signal such as points, reactions, views, rank, adds, ratings,
   or another defensible popularity metric.
4. Rate limits and free-tier limits.
5. Fit with the current `CategorySourceConfig` → adapter → `TrendSnapshot` →
   `TrendItem` architecture.

### 2.1 Current Verified Sources

| Source | Categories Served | API / Access Method | Trend Signal | Status |
|---|---|---|---|---|
| Hacker News API | Tech | Free Firebase API — no auth | Points | Implemented |
| DEV / Forem API | Tech | Public REST API — no auth | Reactions + comments | Implemented |
| New York Times Most Popular API | News | API key | Most viewed rank | Implemented |
| RAWG API | Gaming | API key | User library adds, rating/release metadata | Implemented |

### 2.2 Deferred Sources

| Source | Reason Deferred |
|---|---|
| Reddit | API access is approval-gated and unreliable for this project as of 2026. Do not add Reddit back until access is approved and live fetches work. |
| arXiv | Public and reliable, but weak for "trending" because it has no likes, points, views, or popularity metric. Revisit only with a research-specific ranking strategy. |
| Steam / IGDB | Potentially useful for Gaming, but OAuth/API complexity is higher than RAWG. |
| YouTube | Potentially useful, but quota and category mapping need separate verification. |
| PubMed / NCBI | Public, but "trending" signal needs careful definition. |
| TMDB | Good later candidate for TV/Movies, not required for the current three-category demo. |
| NASA Open APIs | Good later candidate for Space, not required for the current three-category demo. |
| Google Trends / pytrends | Useful for historical context, but unofficial and rate-limit sensitive. Not required for the first public demo. |

### 2.3 Source Configuration

Category and source mappings live in the database through
`CategorySourceConfig`. Existing source adapters can be assigned to categories
without changing the schema. A brand-new source type still requires a code
deploy because it needs a new adapter and tests.

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
| FR-01 | M | 1 | The system shall allow users to register and log in using Django session authentication with email/password credentials. Session cookies and CSRF protection shall be used for browser clients. Google OAuth/JWT may be added later but is not required for the current public demo. |
| FR-02 | C | 3 | On first login, the system shall present an interest onboarding flow where the user selects at least 3 categories. The flow is skippable; skipping defaults to all categories. |
| FR-03 | M | 2 | The user shall be able to edit their category preferences directly from the dashboard via an inline sidebar or modal — without navigating to a settings page. |

---

### 3.2 Dashboard & Display (FR-DASH)

| ID | Priority | Phase | Requirement |
|---|---|---|---|
| FR-04 | M | 1 | The system shall display a home dashboard showing the top 5 trending items per category for each of the user's selected categories. |
| FR-05 | M | 1 | The user shall be able to drill into any category at `/category/[slug]` to see a paginated ranked list of stored trending items for that category. |
| FR-06 | M | 1 | Each trend card shall display: title, source platform, score/metric (points, reactions, views, rank, adds, or source-specific equivalent), and links to the original/platform content. From Phase 2 onward it may also display an AI-generated one-line summary. |
| FR-07 | C | 2/3 | The user shall be able to filter trends by time window: today, last 7 days, last 30 days, last 90 days. Only time windows with existing snapshot data shall be selectable. This should not block the first public demo if enough snapshot history has not accumulated. |
| FR-08 | C | 2/3 | Each category page should display trend charts only after enough snapshot history exists to make the chart meaningful. |
| FR-09 | M | 2 | The user shall be able to filter which source platforms are shown. This filter operates on already-fetched stored data and shall not trigger external API calls. |
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
| FR-20 | C | 2 | Categories, subcategories, and category-to-source mappings shall be configurable via the Django admin panel where possible. New categories that use existing source adapters require only configuration. New source types require live API verification, adapter code, tests, secrets if needed, and a code deploy. |

---

## 4. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | Dashboard API responses shall return in under 1 second. All trend data is pre-computed at ingestion time and served from cache — no live external API calls on user request. |
| NFR-02 | Trend data shall be at most 24 hours stale. Each category page shall display a visible "last updated" timestamp. |
| NFR-03 | If a data source fails, the failure shall not cascade to other sources or crash the ingestion job. Each adapter runs independently. |
| NFR-04 | All API calls shall respect the rate limits of each source. The ingestion scheduler shall budget calls per source accordingly. |
| NFR-05 | During Phase 1, the Next.js frontend runs on localhost. During Phase 2, the frontend should be deployed to a public URL. CORS, CSRF trusted origins, and session cookie settings shall be configured separately for local and cloud environments. |
| NFR-06 | All Gemini API calls shall occur only during the nightly ingestion batch job — never per user request. AI cost is fixed and predictable regardless of user count. |
| NFR-07 | All API keys, credentials, and secrets shall be stored in GCP Secret Manager. They shall never be hardcoded in source code or committed to the repository. |
| NFR-08 | Every push to the main branch shall trigger the CI/CD pipeline: lint (ruff), type check (mypy), tests (pytest), Docker build, push to Artifact Registry, deploy to Cloud Run. |
| NFR-09 | The system shall be deployable entirely on GCP free tier or near-free tier during development. Production costs at small scale (< 500 DAU) shall not exceed $30/month. |

---

## 5. Categories & Subcategory Model

The current public-demo baseline focuses on Tech, Gaming, and News because each
has at least one verified source. Additional categories should be activated only
after a suitable source is live-verified.

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

## 7. Revised / Deferred Assumptions

| Topic | Current Decision |
|---|---|
| Reddit | Deferred because API access is approval-gated and unreliable for this project. |
| Google OAuth + JWT | Deferred; Django session auth is the current implementation. |
| Public frontend deployment | Moved into Phase 2 so the project can be shared through a URL. |
| Time windows and charts | Deferred until enough daily snapshots exist. |
| New sources | Must be live API-verified before implementation. |

---

*End of Requirements Document*
