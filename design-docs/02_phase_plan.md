# Zeitgeist — Phase & Delivery Plan

**Version:** 2.0  
**Status:** Revised after Phase 1 implementation decisions  
**Last Updated:** 2026-07-06

---

## 1. Delivery Philosophy

Each phase delivers a working, testable, deployable slice of the product. No phase ends with half-built features or speculative scaffolding. The exit gate for each phase must be passed before Phase N+1 begins.

The source strategy was revised during implementation: new sources are added only
after live API verification proves access, response shape, rate limits, and a
usable trend signal. Do not add placeholder source models, secrets, or CD wiring
for sources that have not been verified.

**Sequencing logic:**

1. **Phase 1 (Foundation)** answers the hardest infrastructure question first: can real data flow from external APIs into a database and out to a frontend reliably every day? Everything else builds on this.
2. **Phase 2 (Useful Product)** turns the current Tech/Gaming/News baseline into a public demo with useful category pages, source filters, saved preferences, AI summaries if feasible, and a deployed frontend.
3. **Phase 3 (Intelligence & Polish)** adds cross-platform intelligence, onboarding, digest email, monitoring, and broader source/category expansion after the public baseline is stable.

---

## 2. Phase 1 — Foundation

**Duration:** Completed under revised local-first scope  
**Goal:** End-to-end data flow working from verified public APIs → Django → Postgres → backend API → Next.js dashboard. No AI. 3 starter categories.  
**Deployment:** Django backend on GCP Cloud Run. Next.js on localhost.

Original Phase 1 assumed Reddit plus Google OAuth/JWT. During implementation,
those assumptions changed:

- Reddit was deferred because API access became approval-gated and unreliable.
- Google OAuth/JWT was deferred in favor of Django session auth with
  email/password, CSRF, and saved preferences.
- Hacker News became the first proven end-to-end source; DEV, NYT, and RAWG
  were added later after live API verification.

### 2.1 Requirements in Scope

| FR ID | Requirement Summary |
|---|---|
| FR-01 | Revised auth: Django session auth with email/password, CSRF, signup, login, logout, and saved preferences |
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
- Unverified source integrations
- Reddit, unless API access is approved and verified
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
| Week 2 | Data models + ingestion | Category, TrendItem, IngestionRun models. Hacker News adapter. Cloud Run Job + Cloud Scheduler running. First real data in Postgres. Django admin showing ingestion logs. |
| Week 3 | API + auth + frontend skeleton | DRF endpoints for dashboard and category pages. Django session auth. Next.js on localhost consuming the API. Trend cards rendering with real data. |
| Week 4 | Error handling + polish | FR-13 graceful failure. Stale data indicator. UI polish on trend cards and source badges. Phase 1 exit gate testing. |

### 2.5 Phase 1 Exit Gate

Move to Phase 2 only when these conditions are met:

1. At least one verified source works end to end from external API to frontend.
2. Dashboard loads with real trend data in **under 2 seconds** from localhost.
3. User can register, log in, save preferences, refresh, and restore preferences locally.
4. CI passes and CD deploys the backend health endpoint successfully.

---

## 3. Phase 2 — Useful Product

**Duration:** In progress  
**Goal:** Turn the current Tech/Gaming/News baseline into a usable public demo: real data in all three categories, useful category pages, source filtering, saved preferences, AI summaries if feasible, and a deployed frontend URL.  
**Deployment:** Backend on GCP Cloud Run. Frontend moves from localhost to a public deployed URL during this phase.

### 3.1 Requirements in Scope

| FR ID | Requirement Summary |
|---|---|
| FR-03 | Inline category preference editing from the dashboard |
| FR-05 | Category detail pages with paginated stored trends |
| FR-07 | Time window filter: today / 7d / 30d / 90d — only after enough snapshot history exists |
| FR-08 | Trend charts per category — only after enough snapshot history exists |
| FR-09 | Source platform filter on category pages; dashboard-level filter optional |
| FR-14 | Gemini category trend summaries — generated once per ingestion run, stored, displayed |
| FR-20 | Admin-configurable categories and source mappings |

### 3.2 Current Verified Data Sources

| Source | Category | Auth | Trend Signal | Status |
|---|---|---|---|---|
| Hacker News | Tech | None | Points | Implemented |
| DEV / Forem | Tech | None | Reactions + comments | Implemented |
| New York Times Most Popular | News | API key | Most viewed rank | Implemented |
| RAWG | Gaming | API key | User library adds, rating/release metadata | Implemented |

### 3.3 Deferred Data Sources

| Source | Reason Deferred |
|---|---|
| Reddit | API access is approval-gated and unreliable for this project as of 2026. Do not re-add unless access is approved and live fetches work. |
| arXiv | Public and reliable, but weak for "trending" because it has no likes, points, views, or popularity metric. Revisit only with a research-specific ranking strategy. |
| Steam / IGDB | Useful for Gaming but more complex than RAWG because of OAuth/API complexity. |
| YouTube | Potentially useful, but quota and category mapping need separate verification. |
| PubMed | Public, but "trending" signal needs careful definition. |
| TMDB | Good later candidate for TV/Movies, not required for the current three-category demo. |
| NASA | Good later candidate for Space, not required for the current three-category demo. |

### 3.4 GCP Services — Changes in Phase 2

| Service | Change | Notes |
|---|---|---|
| Cloud Run (Frontend) | **Added** | Deploy Next.js to a public URL so the demo can be shared. |
| Secret Manager | **Updated** | Add only verified source keys and Gemini key if AI summaries are implemented. |
| Cloud Run Job | **Updated** | Ingestion job runs verified adapters only: HN, DEV, NYT, RAWG. |
| Vertex AI / Gemini | **Optional in Phase 2** | Called during ingestion only, never per user request. |
| Memorystore (Redis) | **Deferred unless needed** | Current traffic is small; Postgres-backed reads are acceptable until performance requires cache. |

### 3.5 Build Order

| Step | Focus | Key Deliverables |
|---|---|---|
| 1 | Category page polish | Stable `/category/[slug]` pages, generic source filter buttons, clean pagination, consistent rank display |
| 2 | Ingestion volume | Store up to 50 items per source; local/cloud ingestion should be rerun after deploy to populate the larger snapshots |
| 3 | Preference UX | Finalize logged-in preference editing and anonymous behavior |
| 4 | Public frontend deployment | Deploy Next.js and configure CORS/CSRF/session behavior for frontend + backend |
| 5 | Cloud smoke testing | Verify public dashboard, category pages, auth, preferences, and ingestion freshness |
| 6 | Gemini summaries | Add category summary model/management flow and generate summaries during ingestion, if still in Phase 2 scope |

### 3.6 Phase 2 Exit Gate

Move to Phase 3 only when these conditions are met:

1. Public frontend URL works for anonymous users.
2. Dashboard and category pages show real data for Tech, Gaming, and News.
3. Source filters work from stored data and do not trigger external API calls.
4. Logged-in users can save and restore category preferences in the deployed environment.
5. Cloud ingestion runs successfully with HN, DEV, NYT, and RAWG.
6. CI/CD deploys backend changes without manual database fixes.
7. Gemini category summaries are generated once per ingestion run and displayed, or AI summaries are explicitly deferred with the rest of the product still public-demo ready.

Time-window filters and charts require accumulated snapshot history. They should
not block the first public demo unless enough daily snapshots exist.

---

## 4. Phase 3 — Intelligence & Polish

**Duration:** ~2–3 weeks  
**Goal:** Add cross-platform topic intelligence, digest email, onboarding, monitoring, and broader source/category expansion after the public Phase 2 baseline is stable.  
**Deployment:** Frontend and backend already public from Phase 2; Phase 3 hardens the product.

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
| Cloud Run (Frontend) | **Hardened** | Frontend should already be deployed from Phase 2; Phase 3 adds monitoring/custom domain polish if needed. |
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
| Week 11 | Launch hardening | Custom domain + SSL if needed. Load test (50 concurrent users, all responses < 500ms with warm cache). Phase 3 exit gate. Ship. |

### 4.4 Phase 3 Exit Gate — Public Launch Checklist

| Check | Condition |
|---|---|
| Monitoring | Cloud Monitoring alerts fire correctly for: ingestion failure, API error rate > 1%, response time > 2s |
| Email digest | Digest has been sent to internal testers for at least 2 weeks and reads well across all categories |
| Cross-platform detection | Known cross-platform events (major AI release, game launch) are correctly surfaced with the badge |
| Load test | 50 concurrent users on dashboard — all responses under 500ms with Redis warm |
| Auth | Session auth works on production domain; OAuth remains optional future enhancement |
| CORS | Localhost:3000 origin removed from production CORS config |

---

## 5. Requirements Traceability Matrix

| FR ID | Phase | Must/Could | Status |
|---|---|---|---|
| FR-01 | 1 | Must | Revised and implemented with Django session auth |
| FR-02 | 3 | Could | Planned |
| FR-03 | 2 | Must | In progress |
| FR-04 | 1 | Must | Implemented |
| FR-05 | 1/2 | Must | Implemented; polishing in Phase 2 |
| FR-06 | 1 | Must | Implemented |
| FR-07 | 2/3 | Could | Deferred until enough snapshots exist |
| FR-08 | 2/3 | Could | Deferred until enough snapshots exist |
| FR-09 | 2 | Must | Implemented on category pages |
| FR-10 | 3 | Could | Planned |
| FR-11 | 1 | Must | Implemented |
| FR-12 | 1 | Must | Implemented |
| FR-13 | 1 | Must | Initial implementation; continue polishing |
| FR-14 | 2 | Must | Planned |
| FR-15 | 3 | Could | Planned |
| FR-16 | 3 | Could | Planned |
| FR-17 | — | Removed | Descoped |
| FR-18 | 3 | Must | Planned |
| FR-19 | 1 | Must | Implemented |
| FR-20 | 2 | Could | Partially implemented |
| NFR-01 to NFR-09 | All | Must | In progress |

---

## 6. Near-Term Plan

The next work should stay focused on getting a successful public Phase 2 demo:

1. Finish category detail polish and verify it locally with Tech, Gaming, and News.
2. Store up to 50 items per source and rerun ingestion locally/cloud after deploy.
3. Run local ingestion and verify dashboard/category pages from the database.
4. Deploy backend changes through CI/CD.
5. Deploy the Next.js frontend to a public URL.
6. Configure cloud CORS, CSRF, and session cookie behavior for frontend + backend.
7. Add Gemini category summaries only after the public dashboard flow is stable.

---

*End of Phase & Delivery Plan*
