# TrendPulse — Phase & Delivery Plan

**Version:** 1.0  
**Status:** Approved  
**Last Updated:** 2026-05-11

---

## 1. Delivery Philosophy

Each phase delivers a working, testable, deployable slice of the product. No phase ends with half-built features or speculative scaffolding. The exit gate for each phase must be passed before Phase N+1 begins.

**Sequencing logic:**

1. **Phase 1 (Foundation)** answers the hardest infrastructure question first: can real data flow from external APIs into a database and out to a frontend reliably every day? Everything else builds on this.
2. **Phase 2 (Intelligence)** adds AI and additional data sources only after the data pipeline is proven stable. Gemini prompts are written against real data — not hypothetical data.
3. **Phase 3 (Polish & Ship)** deploys publicly only after the product is reliable. Cross-platform intelligence and email features require consistent, multi-week data history.

---

## 2. Phase 1 — Foundation

**Duration:** ~4 weeks  
**Goal:** End-to-end data flow working. Reddit + Hacker News → Django → Postgres → Next.js dashboard on localhost. No AI. 3 categories.  
**Deployment:** Django backend on GCP Cloud Run. Next.js on localhost.

### 2.1 Requirements in Scope

| FR ID | Requirement Summary |
|---|---|
| FR-01 | Google OAuth login + JWT auth |
| FR-04 | Home dashboard — top 5 per category |
| FR-05 | Category detail page — top 10–20 items |
| FR-06 | Trend cards (title, source badge, score, link) — no AI summary slot yet |
| FR-11 | Daily ingestion via Cloud Scheduler at 03:00 UTC |
| FR-12 | Snapshot storage — timestamped per run (no UI, data accumulates silently) |
| FR-13 | Graceful source failure — log, skip, serve last snapshot with stale indicator |
| FR-19 | Django admin — ingestion run log, manual re-fetch trigger |

### 2.2 Explicitly Not Built in Phase 1

- AI summaries (FR-14)
- Trend charts (FR-08)
- Time window filter (FR-07)
- Source platform filter (FR-09)
- Inline preference editing (FR-03)
- Interest onboarding (FR-02)
- YouTube / arXiv / PubMed / TMDB / Steam sources
- Redis cache (Postgres is sufficient at this scale)
- Subcategory UI
- Email notifications

### 2.3 GCP Services — Phase 1

| Service | Purpose | Notes |
|---|---|---|
| Cloud Run (API) | Django REST API server | 1 instance min, CORS allows localhost:3000 |
| Cloud Run Job | Daily ingestion job | Separate image from API server |
| Cloud SQL (Postgres) | Primary database | db-f1-micro during development |
| Cloud Scheduler | Triggers ingestion at 03:00 UTC daily | One additional manual trigger for testing |
| Secret Manager | API keys, Django secret key, DB credentials | Accessed at Cloud Run startup |
| Artifact Registry | Docker image storage | GitHub Actions pushes here on passing builds |
| GitHub Actions | CI/CD pipeline | Lint → test → build → push → deploy |

### 2.4 Week-by-Week Build Order

| Week | Focus | Key Deliverables |
|---|---|---|
| Week 1 | Project scaffold + CI/CD | Django project structure, Cloud SQL connected, GitHub Actions pipeline deploying to Cloud Run on green builds. Nothing functional yet — pipeline is the output. |
| Week 2 | Data models + ingestion | Category, TrendItem, IngestionRun models. Reddit + HN adapters. Cloud Run Job + Cloud Scheduler running. First real data in Postgres. Django admin showing ingestion logs. |
| Week 3 | API + auth + frontend skeleton | DRF endpoints for dashboard and category pages. Google OAuth + JWT. Next.js on localhost consuming the API. Trend cards rendering with real data. No UI polish yet. |
| Week 4 | Error handling + polish | FR-13 graceful failure. Stale data indicator. UI polish on trend cards and source badges. Phase 1 exit gate testing. |

### 2.5 Phase 1 Exit Gate

Move to Phase 2 only when all three conditions are met:

1. Daily ingestion has run successfully (data in Postgres) at least **3 consecutive times**
2. Dashboard loads with real trend data in **under 2 seconds** from localhost
3. Google OAuth login works reliably — user persists in DB, JWT is valid across page refreshes

---

## 3. Phase 2 — Intelligence

**Duration:** ~3–4 weeks  
**Goal:** Make the data genuinely useful. Add AI summaries, trend charts, all 9 categories, additional sources, source filtering, and inline preference editing.  
**Deployment:** Backend still on GCP Cloud Run. Frontend still on localhost. Redis cache added.

### 3.1 Requirements in Scope

| FR ID | Requirement Summary |
|---|---|
| FR-14 | Gemini category trend summaries — generated once per daily ingestion run, stored, displayed |
| FR-09 | Source platform filter on dashboard and category pages |
| FR-03 | Inline category preference editing from the dashboard |
| FR-07 | Time window filter: today / 7d / 30d / 90d (only windows with real snapshot data) |
| FR-08 | Trend charts per category using stored snapshots + Google Trends long-term curves |
| FR-20 | Admin-configurable categories and subreddit lists (remaining 6 categories added here) |

### 3.2 New Data Sources Added

| Source | Categories Fed | Notes |
|---|---|---|
| YouTube Data API | Gaming, TV/Movies, Food | Trending videos by category + region. 10k units/day free. |
| arXiv API | Research, AI, Space | Most-submitted papers by field. Completely free. |
| PubMed / NCBI | Health, Research | Most-cited recent papers. Free with API key. |
| TMDB API | TV/Movies | Trending movies and TV shows globally. Free API key. |
| Steam Spy + IGDB | Gaming | Player counts + trending games. Free / Twitch OAuth. |
| NASA Open APIs | Space | Astronomy, near-Earth objects, mission data. Free. |

### 3.3 GCP Services — Changes in Phase 2

| Service | Change | Notes |
|---|---|---|
| Vertex AI (Gemini) | **Added** | Called in ingestion Cloud Run Job only. ~9 calls/day. Near-zero cost at this volume. |
| Memorystore (Redis) | **Added** | Cache for category dashboard responses. TTL 23 hours. Refreshed post-ingestion. |
| Secret Manager | **Updated** | YouTube, TMDB, NASA, Gemini credentials added. |
| Cloud Run Job | **Updated** | Ingestion job now runs all 9 source adapters + Gemini summary generation in sequence. |

### 3.4 Week-by-Week Build Order

| Week | Focus | Key Deliverables |
|---|---|---|
| Week 5 | New sources + Gemini summaries | YouTube, arXiv, PubMed, TMDB, Steam, NASA adapters. 6 remaining categories configured in admin. Gemini summary generation added to ingestion job. Prompt iteration against real data. |
| Week 6 | Trend charts + time window filter | Recharts integration in Next.js. Snapshot-based recent curves. pytrends for long-term historical. Redis cache wired. |
| Week 7–8 | Source filter + inline preferences + polish | FR-09 source filter UI. FR-03 inline category toggle. FR-20 admin category config validated. Phase 2 exit gate testing. |

### 3.5 Phase 2 Exit Gate

Move to Phase 3 only when all three conditions are met:

1. Gemini summaries read **sensibly and usefully** for all 9 categories — iterate the prompt until they do
2. Trend charts render correctly with **at least 2 weeks** of real snapshot data
3. API responses stay **under 1 second** with Redis cache warm on a category page

---

## 4. Phase 3 — Polish & Ship

**Duration:** ~2–3 weeks  
**Goal:** Deploy the frontend publicly, add cross-platform topic intelligence, email digest, onboarding, and sentiment tags. Full public launch.  
**Deployment:** Next.js frontend deployed (Cloud Run or Vercel). Backend on GCP Cloud Run with production configuration.

### 4.1 Requirements in Scope

| FR ID | Requirement Summary |
|---|---|
| FR-02 | Interest onboarding flow on first login |
| FR-18 | Weekly personalised digest email via SendGrid (Monday 08:00 UTC) |
| FR-10 | "Trending everywhere" cards for cross-platform topics |
| FR-15 | Cross-platform topic detection via Vertex AI embeddings (post-ingestion job) |
| FR-16 | Sentiment tags (Positive / Negative / Neutral) on trend cards via Gemini |

### 4.2 GCP Services — Changes in Phase 3

| Service | Change | Notes |
|---|---|---|
| Cloud Run (Frontend) | **Added** | Next.js deployed as a Cloud Run service, or Vercel. CORS updated to production domain. |
| Cloud Scheduler | **Updated** | Second job added: weekly digest email trigger every Monday 08:00 UTC. |
| SendGrid | **Added** | Email delivery for weekly digest. Free tier: 100 emails/day. API key in Secret Manager. |
| Cloud Monitoring | **Added** | Uptime checks, ingestion failure alerts, error rate alerts. Required before public launch. |
| Vertex AI (Embeddings) | **Added** | text-embedding-004 for cross-platform topic matching. Batched post-ingestion. Not per-user. |
| Cloud Load Balancer | **Added** | HTTPS termination and custom domain routing for frontend. |

### 4.3 Week-by-Week Build Order

| Week | Focus | Key Deliverables |
|---|---|---|
| Week 9 | Cross-platform detection + sentiment | FR-15 embedding job post-ingestion. FR-10 "trending everywhere" cards in frontend. FR-16 Gemini sentiment tags on cards. |
| Week 10 | Email digest + onboarding | FR-18 weekly digest with SendGrid. FR-02 first-login onboarding flow. Cloud Monitoring alerts configured. |
| Week 11 | Public deploy + launch | Next.js deployed to Cloud Run or Vercel. Custom domain + SSL. Load test (50 concurrent users, all responses < 500ms with warm cache). Phase 3 exit gate. Ship. |

### 4.4 Phase 3 Exit Gate — Public Launch Checklist

| Check | Condition |
|---|---|
| Monitoring | Cloud Monitoring alerts fire correctly for: ingestion failure, API error rate > 1%, response time > 2s |
| Email digest | Digest has been sent to internal testers for at least 2 weeks and reads well across all categories |
| Cross-platform detection | Known cross-platform events (major AI release, game launch) are correctly surfaced with the badge |
| Load test | 50 concurrent users on dashboard — all responses under 500ms with Redis warm |
| Auth | OAuth login works on production domain (not just localhost) |
| CORS | Localhost:3000 origin removed from production CORS config |

---

## 5. Requirements Traceability Matrix

| FR ID | Phase | Must/Could | Status |
|---|---|---|---|
| FR-01 | 1 | Must | Planned |
| FR-02 | 3 | Could | Planned |
| FR-03 | 2 | Must | Planned |
| FR-04 | 1 | Must | Planned |
| FR-05 | 1 | Must | Planned |
| FR-06 | 1 | Must | Planned |
| FR-07 | 2 | Could | Planned |
| FR-08 | 2 | Could | Planned |
| FR-09 | 2 | Must | Planned |
| FR-10 | 3 | Could | Planned |
| FR-11 | 1 | Must | Planned |
| FR-12 | 1 | Must | Planned |
| FR-13 | 1 | Must | Planned |
| FR-14 | 2 | Must | Planned |
| FR-15 | 3 | Could | Planned |
| FR-16 | 3 | Could | Planned |
| FR-17 | — | Removed | Descoped |
| FR-18 | 3 | Must | Planned |
| FR-19 | 1 | Must | Planned |
| FR-20 | 2 | Could | Planned |
| NFR-01 to NFR-09 | All | Must | Planned |

---

*End of Phase & Delivery Plan*
