# Zeitgeist - Requirements Document

**Version:** 3.1
**Status:** Updated to match current deployed architecture and source set
**Last Updated:** 2026-07-29

## 1. Project Overview

Zeitgeist is a personalized internet trend dashboard. It collects trends and
recent activity from verified public APIs, normalizes them into a common model,
stores daily snapshots, and serves a category dashboard from Postgres. AI
summaries are generated during ingestion and stored for display so user-facing
pages do not call Gemini on demand.

## 2. Current Verified Sources

| Source | Category | Access | Trend/display signal | Status |
|---|---|---|---|---|
| Hacker News | Tech | No auth | Points | Implemented |
| DEV | Tech | No auth | Reactions + comments | Implemented |
| New York Times Most Popular | News | API key | Most viewed rank | Implemented |
| RAWG | Gaming | API key | Adds, ratings, release metadata | Implemented |
| Football-Data | Sports | API token | Recent match data and status | Implemented |
| Cricket Data | Sports | API key | Current and recently completed match data | Implemented |

Source rule: a new source must be live API-verified before adding code, secrets,
seed rows, Terraform resources, or CD wiring.

## 3. Functional Requirements

### Authentication

| ID | Requirement | Status |
|---|---|---|
| FR-01 | Users can register and sign in with email/password using Django session authentication and CSRF protection. | Implemented |
| FR-01a | Users must verify registration email with a one-time code before completing the account flow. | Implemented |
| FR-01b | Users can reset a forgotten password using an emailed one-time code. | Implemented |
| FR-01c | Public auth endpoints are rate-limited by IP and email to reduce abuse before expensive password checks or email sends. | Implemented |
| FR-02 | Onboarding flow for first login category selection. | Deferred |
| FR-03 | Users can save category preferences from the dashboard. | Implemented |

### Dashboard and Display

| ID | Requirement | Status |
|---|---|---|
| FR-04 | Dashboard shows stored top trends grouped by active category and source. | Implemented |
| FR-05 | `/category/[slug]` shows a paginated category detail view. | Implemented |
| FR-06 | Trend cards show title, source, score/status, and relevant links/metadata. | Implemented |
| FR-06a | Sports cards show match-first metadata such as teams, status, date, and score summary rather than generic discussion links or synthetic popularity scores. | Implemented |
| FR-07 | Time-window filters for today/7d/30d/90d. | Deferred until enough snapshot history exists |
| FR-08 | Category trend charts. | Deferred |
| FR-09 | Category source filters operate on stored data only. | Implemented |
| FR-09a | Sports category detail view separates individual sports sources and does not offer an "All" option that mixes football and cricket match lists. | Implemented |
| FR-10 | Cross-platform "trending everywhere" cards. | Deferred |

### Ingestion

| ID | Requirement | Status |
|---|---|---|
| FR-11 | Cloud Scheduler triggers ingestion daily. | Implemented |
| FR-12 | Each source writes timestamped snapshots and trend items. | Implemented |
| FR-13 | Source failures are logged and do not block other sources. | Implemented |
| FR-14 | Gemini generates one category summary per ingestion batch, stored in Postgres. | Implemented |
| FR-14a | Sports category detail view can display source-specific AI summaries for cricket and football using the same summary format as other categories. | Implemented |
| FR-15 | Cricket ingestion includes current matches and recently completed matches from the last two weeks, excludes future fixtures, and caps displayed data at 50 matches. | Implemented |

### Production Delivery and Security

| ID | Requirement | Status |
|---|---|---|
| FR-16 | Production is served from `https://dailyzeitgeist.xyz` through an HTTPS load balancer with HTTP to HTTPS redirect. | Implemented |
| FR-16a | Browser API calls use same-origin `/api/v1` paths; server-side frontend calls use `SERVER_API_BASE_URL=https://dailyzeitgeist.xyz/api/v1`. | Implemented |
| FR-16b | Cloud Run frontend and API services accept ingress only from internal and load-balancer traffic, blocking direct public `run.app` access. | Implemented |
| FR-16c | Cloud Armor is attached to the API backend service behind the load balancer to throttle sensitive API/auth traffic without applying the policy to the frontend backend. | Implemented |
| FR-16d | Production cookies and CSRF behavior support the same-origin deployment model with `SameSite=Lax`. | Implemented |

### Administration

| ID | Requirement | Status |
|---|---|---|
| FR-19 | Django admin exposes ingestion run history and key models. | Implemented |
| FR-20 | Categories and source mappings are database-backed. | Implemented |

## 4. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-01 | User-facing pages must read stored data, never live-fetch source APIs. |
| NFR-02 | External source calls run only in ingestion jobs. |
| NFR-03 | Gemini calls run only during ingestion, never per page request. |
| NFR-04 | Secrets are stored in Secret Manager and never committed. |
| NFR-05 | Terraform owns stable infrastructure; CD owns runtime images/env/secrets. |
| NFR-06 | Production CORS and CSRF trusted origins must include the custom domain and required Cloud Run frontend origins used by browsers. |
| NFR-07 | Auth abuse protection must reject excessive attempts with HTTP 429 before doing expensive auth or email work. |
| NFR-08 | Production API traffic must enter through the HTTPS load balancer so path routing, managed TLS, HTTP redirects, and Cloud Armor policy are consistently applied. |
| NFR-09 | Frontend rendering must use deterministic formatting for numbers, dates, and labels to avoid server/client hydration mismatches. |
| NFR-10 | External API credentials, including NYT, RAWG, Football-Data, and Cricket Data keys, must be provided to ingestion through Secret Manager. |

## 5. Deferred Sources and Services

Deferred sources and alternate auth/email providers are not part of the current
implementation and should not have active adapters, seed rows, Terraform
secrets, or CD wiring. They may be reconsidered later only after live
verification and a clear product reason.

## 6. Active Categories

| Category | Notes |
|---|---|
| Tech | Hacker News and DEV content. |
| News | New York Times most-viewed stories. |
| Gaming | RAWG game popularity metadata. |
| Sports | Football-Data and Cricket Data recent matches, displayed by match recency/status rather than a synthetic trend score. |

## 7. Removed Requirement

| ID | Requirement | Reason |
|---|---|---|
| FR-17 | Keyword topic alerts | Descoped because it overlaps with digest/email features and adds background matching complexity. |

## 8. Minimum Must-Have Requirements

These are the core requirements needed for a basic but functional Zeitgeist
release. Other implemented requirements improve polish, reliability, or security,
but these define the smallest useful product.

| Requirement | Why it is must-have |
|---|---|
| Users can view stored top trends grouped by active category and source. | This is the main product experience. |
| User-facing pages read from Postgres and never live-fetch external source APIs. | Keeps the app fast, predictable, and protected from source API limits. |
| A scheduled ingestion job collects data from the active verified sources and writes snapshots/trend items. | Keeps the dashboard populated without manual work. |
| Source failures are isolated so one broken API does not block the whole ingestion run. | Makes a multi-source platform reliable enough to operate. |
| Gemini summaries are generated during ingestion and stored for display. | Provides the plain-English value layer without slowing page requests. |
| Secrets are stored in Secret Manager and attached through deployment/runtime configuration. | Prevents API keys and application secrets from being committed or exposed. |
| Production traffic is served through the HTTPS load balancer on `dailyzeitgeist.xyz` with API routing under `/api/v1`. | Gives users one stable public domain and keeps browser API calls same-origin. |
