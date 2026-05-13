# TrendPulse — High-Level Design (HLD)

**Version:** 1.0  
**Status:** Draft  
**Last Updated:** 2026-05-11

---

## 1. System Overview

TrendPulse is a web application with a decoupled frontend and backend. The backend is a Django REST API deployed on GCP Cloud Run. The frontend is a Next.js application (localhost in Phase 1–2, publicly deployed in Phase 3). A separate batch ingestion system runs daily to collect trend data from all configured sources and run AI processing. No external API calls are made at request time — all trend data served to users is pre-computed and cached.

### 1.1 High-Level System Context

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                            │
│                                                             │
│  ┌──────────────┐    HTTPS/REST    ┌─────────────────────┐  │
│  │  Next.js     │ ◄──────────────► │  Django API         │  │
│  │  Frontend    │                  │  (Cloud Run)        │  │
│  │  (localhost  │                  └──────────┬──────────┘  │
│  │  → Phase 3:  │                             │             │
│  │  Cloud Run)  │                             │             │
│  └──────────────┘                  ┌──────────▼──────────┐  │
│                                    │  Cloud SQL          │  │
│                                    │  (Postgres)         │  │
│  ┌──────────────────────────────┐  └──────────▲──────────┘  │
│  │  Daily Ingestion Job         │             │             │
│  │  (Cloud Run Job)             │─────────────┘             │
│  │  Reddit · HN · YouTube ·     │                           │
│  │  arXiv · PubMed · TMDB ·     │  ┌──────────────────────┐ │
│  │  Steam · NASA · Google Trends│  │  Vertex AI (Gemini)  │ │
│  └──────────────────────────────┘  │  Called from Job only│ │
│                ▲                   └──────────────────────┘ │
│  ┌─────────────┴──────────────┐                             │
│  │  Cloud Scheduler           │                             │
│  │  03:00 UTC daily trigger   │                             │
│  └────────────────────────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Key Design Principles

| Principle | Decision |
|---|---|
| Pre-compute, never live-fetch | All trend data is fetched and processed during the nightly batch job. The API serves pre-computed results only. No external API calls on user request. |
| Fail gracefully, always serve something | If a source fails during ingestion, the job continues, logs the failure, and the API serves the last successful snapshot with a stale indicator. |
| AI is a batch process, not a live feature | Gemini is called once per daily ingestion run per category. AI cost is fixed and predictable regardless of user count. |
| Data model supports history from day one | Snapshot storage begins in Phase 1. UI to display history comes in Phase 2. You cannot collect yesterday's data retroactively. |
| Categories are database-driven | Category definitions, subreddit lists, and source adapter mappings are stored in Postgres and editable in Django admin. New categories using existing adapters require no code deploy. |

---

## 2. Component Architecture

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  GCP Project: trendpulse-prod                                       │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  Serving Layer                                             │     │
│  │                                                            │     │
│  │  ┌─────────────────┐    ┌──────────────────────────────┐   │     │
│  │  │  Cloud Run      │    │  Memorystore (Redis)         │   │     │
│  │  │  Django API     │◄──►│  Category response cache     │   │     │
│  │  │  trendpulse-api │    │  TTL: 23h, invalidated       │   │     │
│  │  └────────┬────────┘    │  post-ingestion              │   │     │
│  │           │             └──────────────────────────────┘   │     │
│  └───────────┼────────────────────────────────────────────────┘     │ 
│              │                                                      │
│  ┌───────────▼────────────────────────────────────────────────┐     │
│  │  Data Layer                                                │     │
│  │                                                            │     │
│  │  ┌─────────────────┐    ┌──────────────────────────────┐   │     │
│  │  │  Cloud SQL      │    │  Secret Manager              │   │     │
│  │  │  Postgres       │    │  All API keys + credentials  │   │     │
│  │  │  Primary store  │    └──────────────────────────────┘   │     │
│  │  └────────▲────────┘                                       │     │
│  └───────────┼────────────────────────────────────────────────┘     │
│              │                                                      │
│  ┌───────────┼────────────────────────────────────────────────┐     │
│  │  Batch Layer                                               │     │
│  │           │                                                │     │
│  │  ┌────────┴────────┐    ┌──────────────────────────────┐   │     │
│  │  │  Cloud Run Job  │    │  Vertex AI                   │   │     │
│  │  │  Ingestion +    │───►│  Gemini: summaries +         │   │     │
│  │  │  AI processing  │    │  sentiment tags              │   │     │
│  │  └────────▲────────┘    │  Embeddings: cross-platform  │   │     │
│  │           │             └──────────────────────────────┘   │     │
│  │  ┌────────┴────────┐                                       │     │
│  │  │  Cloud Scheduler│                                       │     │
│  │  │  03:00 UTC daily│                                       │     │
│  │  └─────────────────┘                                       │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  DevOps Layer                                                │   │
│  │  Artifact Registry · Cloud Monitoring · GitHub Actions       │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

#### Django API Server (Cloud Run)
- Exposes REST API consumed by Next.js frontend
- Handles authentication (Google OAuth flow, JWT issuance and validation)
- Reads pre-computed trend data from Postgres
- Reads/writes user preferences and profile data
- Returns cached category responses from Redis where available
- Does **not** call any external source APIs at request time
- Hosts Django admin panel for ingestion monitoring and category management

#### Ingestion Cloud Run Job
- Triggered by Cloud Scheduler at 03:00 UTC daily
- Runs each source adapter independently and sequentially
- Each adapter fetches trending items from its source API, normalises to a common schema, and writes to Postgres
- After all adapters complete, triggers AI processing (Gemini summaries, sentiment tags)
- Writes an `IngestionRun` record per source with status, item count, and any errors
- Invalidates Redis cache for affected categories on successful completion
- In Phase 3: runs embedding-based cross-platform topic detection after ingestion

#### Next.js Frontend
- Runs on localhost during Phase 1 and Phase 2
- Deployed to Cloud Run or Vercel in Phase 3
- Communicates exclusively with the Django API — no direct calls to external services
- Handles rendering of dashboard, category pages, trend cards, charts
- Manages client-side JWT storage and auth state

#### Cloud SQL (Postgres)
- Single source of truth for all application data
- Stores: users, preferences, categories, subreddit config, trend items, ingestion snapshots, AI summaries, ingestion run logs
- No time-series database needed — daily snapshot frequency does not require TimescaleDB at this scale

#### Memorystore (Redis) — Phase 2
- Caches API responses for category dashboard and category detail pages
- Cache key: `category:{slug}:top` and `category:{slug}:summary`
- TTL: 23 hours — ensures users always see fresh data within one day
- Cache is invalidated by the ingestion job after a successful run

#### Vertex AI (Gemini + Embeddings) — Phase 2 / Phase 3
- **Gemini:** Called once per category per day during ingestion job to generate trend summary and sentiment tags. ~9 calls/day in Phase 2. ~45 calls/day in Phase 3 (adding sentiment per item).
- **Embeddings (Phase 3):** text-embedding-004 model used post-ingestion to compute vector representations of trending topics per source. Cosine similarity across sources detects cross-platform topics.

---

## 3. Data Architecture

### 3.1 Core Entity Model (High-Level)

```
User
 ├── has many UserCategoryPreference → Category
 └── has many DigestSubscription

Category
 ├── parent → Category (self-referential, subcategories)
 ├── has many SubredditConfig
 ├── has many CategorySourceConfig → SourceAdapter
 └── has many TrendSnapshot

TrendSnapshot
 ├── belongs to Category
 ├── belongs to IngestionRun
 └── has many TrendItem

TrendItem
 ├── belongs to TrendSnapshot
 ├── source: (reddit | hackernews | youtube | arxiv | pubmed | tmdb | steam | nasa)
 ├── title, url, score, score_label
 ├── ai_summary (one-line, Phase 2)
 └── sentiment: (positive | negative | neutral | null) (Phase 3)

IngestionRun
 ├── source_adapter
 ├── status: (success | partial | failed)
 ├── items_fetched
 ├── error_message (nullable)
 └── started_at, completed_at

CategoryAISummary
 ├── belongs to Category
 ├── belongs to IngestionRun
 ├── summary_text (Gemini-generated)
 └── generated_at

CrossPlatformTopic (Phase 3)
 ├── belongs to Category
 ├── topic_label
 ├── sources: [] (list of source names)
 └── detected_at
```

### 3.2 Data Flow — Daily Ingestion

```
03:00 UTC
    │
    ▼
Cloud Scheduler fires HTTP POST → Cloud Run Job
    │
    ▼
For each Category:
    │
    ├── Reddit adapter     → fetches hot posts from configured subreddits
    ├── HN adapter         → fetches top/best stories
    ├── YouTube adapter    → fetches trending videos by category
    ├── arXiv adapter      → fetches most-submitted papers by field
    ├── PubMed adapter     → fetches most-cited recent papers
    ├── TMDB adapter       → fetches trending movies/TV
    ├── Steam adapter      → fetches top-played games
    └── NASA adapter       → fetches featured content
    │
    ▼
Normalise each item to TrendItem schema
Write TrendSnapshot + TrendItems to Postgres
Write IngestionRun record (success/failure per source)
    │
    ▼
[Phase 2+] Gemini: generate CategoryAISummary per category
[Phase 3]  Gemini: generate sentiment tag per TrendItem
[Phase 3]  Embeddings: detect CrossPlatformTopics
    │
    ▼
Invalidate Redis cache for all affected categories
    │
    ▼
Job complete — next run in 24h
```

### 3.3 Data Flow — User Request

```
User opens dashboard
    │
    ▼
Next.js → GET /api/v1/dashboard/
    │
    ▼
Django API: check Redis for cached response
    │
    ├── Cache HIT  → return cached JSON (< 50ms)
    └── Cache MISS → query Postgres for latest snapshot per user categories
                      → write result to Redis
                      → return JSON (< 500ms)
    │
    ▼
Next.js renders dashboard from JSON
No external API calls made at any point in this flow
```

---

## 4. API Design (High-Level)

All endpoints are versioned under `/api/v1/`. Authentication uses JWT in HTTP-only cookie.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/google/` | Public | Google OAuth callback — issues JWT |
| `POST` | `/api/v1/auth/logout/` | JWT | Clears session |
| `GET` | `/api/v1/auth/me/` | JWT | Returns current user + preferences |
| `GET` | `/api/v1/dashboard/` | JWT | Top 5 items per user's selected categories |
| `GET` | `/api/v1/categories/` | JWT | List of all categories with metadata |
| `PATCH` | `/api/v1/categories/preferences/` | JWT | Update user's selected categories (FR-03) |
| `GET` | `/api/v1/categories/{slug}/` | JWT | Category detail: top items, AI summary, source filter |
| `GET` | `/api/v1/categories/{slug}/trends/` | JWT | Trend chart data for a category over a time window |
| `GET` | `/api/v1/categories/{slug}/items/` | JWT | Paginated list of trend items with source + time filters |
| `POST` | `/api/v1/admin/ingestion/trigger/` | Staff | Manually trigger ingestion for a specific source |
| `GET` | `/api/v1/admin/ingestion/runs/` | Staff | Ingestion run history and status |

All responses follow a consistent envelope:

```json
{
  "data": { ... },
  "meta": {
    "last_updated": "2026-05-11T03:14:22Z",
    "source_statuses": {
      "reddit": "ok",
      "hackernews": "ok",
      "youtube": "stale_24h"
    }
  }
}
```

---

## 5. Source Adapter Design

Each source is implemented as a Python class that inherits from a `BaseSourceAdapter`. This enforces a consistent interface across all sources and makes adding new sources straightforward.

```
BaseSourceAdapter
    ├── fetch() → list[RawItem]         # calls the external API
    ├── normalise(raw) → TrendItem      # maps to common schema
    └── get_source_name() → str

RedditAdapter(BaseSourceAdapter)
HackerNewsAdapter(BaseSourceAdapter)
YouTubeAdapter(BaseSourceAdapter)
ArxivAdapter(BaseSourceAdapter)
PubMedAdapter(BaseSourceAdapter)
TMDBAdapter(BaseSourceAdapter)
SteamAdapter(BaseSourceAdapter)
NASAAdapter(BaseSourceAdapter)
GoogleTrendsAdapter(BaseSourceAdapter)   # historical curves only
```

The ingestion job loops over configured adapters per category, calls `fetch()` and `normalise()` on each, and writes the results. Adding a new adapter for an existing source type requires only creating a new class — the job loop picks it up from the category configuration in the database.

---

## 6. AI Processing Design

### 6.1 Gemini Category Summary (FR-14)

Called once per category per ingestion run. Input is the list of top trending item titles and scores for that category. Output is a 2–4 sentence plain-English summary stored as `CategoryAISummary`.

**Prompt structure:**
```
System: You are a trend analyst. Summarise what is trending in {category} 
        today in 2-4 plain English sentences. Be specific — name the topics, 
        explain why they are significant. Do not use filler phrases.

User:   Top trending items in {category} right now:
        1. {title} — {score} upvotes (Reddit)
        2. {title} — {score} points (HN)
        ...
        Summarise what is happening and why it matters.
```

### 6.2 Sentiment Tagging (FR-16) — Phase 3

Called per trending item during ingestion. Batch-processed (multiple items per Gemini call to stay within cost budget). Classifies each item as Positive, Negative, or Neutral.

### 6.3 Cross-Platform Topic Detection (FR-15) — Phase 3

After ingestion completes, the job generates text embeddings (Vertex AI `text-embedding-004`) for all trending item titles within each category. Cosine similarity above a threshold (0.82) between items from different sources identifies cross-platform topics. Results written to `CrossPlatformTopic` table and surfaced via FR-10.

---

## 7. CI/CD Pipeline

```
Developer pushes to main branch
    │
    ▼
GitHub Actions workflow triggered
    │
    ├── ruff lint
    ├── mypy type check
    ├── pytest (unit + integration tests)
    │       │
    │       └── FAIL → pipeline stops, no deploy
    │
    ▼
Docker build (multi-stage — separate images for API server and ingestion job)
    │
    ▼
Push images to GCP Artifact Registry
    │
    ▼
Authenticate to GCP via Workload Identity Federation (no stored keys in GitHub)
    │
    ├── Deploy API image → Cloud Run (trendpulse-api)
    └── Deploy Job image → Cloud Run Job (trendpulse-ingest)
    │
    ▼
Post-deploy smoke test: GET /api/v1/health/ must return 200
    │
    ├── PASS → deployment complete
    └── FAIL → Cloud Run automatically serves previous revision
```

**Branch strategy:**

| Branch | Trigger | Action |
|---|---|---|
| `feat/*` | Push | Lint + type check + tests only. No deploy. |
| `main` | Push (merge) | Full pipeline → auto-deploy to Cloud Run |
| Manual | Cloud Scheduler | Ingestion job — not triggered by Git |

---

## 8. Security Design

| Concern | Approach |
|---|---|
| API credentials | All keys stored in GCP Secret Manager. Accessed at Cloud Run startup via environment injection. Never in code or `.env` files committed to Git. |
| GCP authentication from GitHub Actions | Workload Identity Federation — GitHub Actions OIDC token exchanged for short-lived GCP credentials. No long-lived service account JSON keys stored in GitHub. |
| User authentication | Google OAuth 2.0. JWT issued by Django, stored in HTTP-only cookie (not accessible to JavaScript). |
| CORS | In Phase 1–2: localhost:3000 allowed. In Phase 3: production domain only. |
| Django admin | Restricted to `is_staff` users only. Not exposed publicly in Phase 3 — accessed via Cloud Run's Identity-Aware Proxy or VPN. |
| SQL injection | Django ORM used throughout. Raw SQL queries avoided. |

---

## 9. Django Project Structure

```
trendpulse/
├── apps/
│   ├── accounts/          # User model, Google OAuth, JWT issuance
│   ├── categories/        # Category, SubredditConfig, CategorySourceConfig models
│   ├── trends/            # TrendItem, TrendSnapshot, CategoryAISummary models + API views
│   ├── ingestion/         # IngestionRun model, ingestion job orchestration, adapters/
│   │   └── adapters/
│   │       ├── base.py
│   │       ├── reddit.py
│   │       ├── hackernews.py
│   │       ├── youtube.py
│   │       ├── arxiv.py
│   │       ├── pubmed.py
│   │       ├── tmdb.py
│   │       ├── steam.py
│   │       └── nasa.py
│   └── ai/                # Vertex AI client wrappers, prompt templates, embedding utils
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── Dockerfile
├── Dockerfile.job          # Separate image for ingestion Cloud Run Job
├── manage.py
└── pyproject.toml          # ruff, mypy, pytest config
```

---

## 10. GCP Service Summary

| Service | Phase Introduced | Purpose | Cost Tier |
|---|---|---|---|
| Cloud Run (API) | Phase 1 | Django REST API server | Pay-per-use — free tier covers dev |
| Cloud Run Job | Phase 1 | Daily ingestion + AI processing | Pay-per-use — cents/day |
| Cloud SQL (Postgres) | Phase 1 | Primary database | db-f1-micro ~$7/month |
| Cloud Scheduler | Phase 1 | Daily ingestion trigger + weekly email trigger | Free (3 jobs free/month) |
| Secret Manager | Phase 1 | API keys and credentials | Free up to 6 secrets |
| Artifact Registry | Phase 1 | Docker image storage | Free up to 0.5GB |
| GitHub Actions | Phase 1 | CI/CD pipeline | Free for public repos |
| Memorystore (Redis) | Phase 2 | API response cache | ~$15/month (M1 basic) |
| Vertex AI (Gemini) | Phase 2 | Trend summaries + sentiment | ~$0.01–$0.05/day at this volume |
| Vertex AI (Embeddings) | Phase 3 | Cross-platform topic detection | ~$0.001/day at this volume |
| SendGrid | Phase 3 | Weekly digest emails | Free up to 100 emails/day |
| Cloud Run (Frontend) | Phase 3 | Next.js frontend hosting | Pay-per-use — free tier covers launch |
| Cloud Load Balancer | Phase 3 | HTTPS + custom domain | ~$18/month |
| Cloud Monitoring | Phase 3 | Alerts and uptime checks | Free tier covers basic use |

**Estimated monthly cost at launch (< 500 DAU):** ~$30–$45/month

---

*End of High-Level Design Document*
