# Zeitgeist - High-Level Design

**Version:** 2.1
**Status:** Updated to current production architecture
**Last Updated:** 2026-07-29

## 1. System Overview

Zeitgeist is a decoupled web app:

- Next.js frontend hosted on Cloud Run.
- Django REST Framework API hosted on Cloud Run.
- Cloud Run Job for ingestion and AI summaries.
- Reusable Cloud Run database maintenance job for migrations and seed commands.
- Cloud Scheduler triggers ingestion daily.
- Cloud SQL Postgres stores users, sessions, categories, preferences,
  snapshots, items, ingestion logs, OTPs, and AI summaries.
- Secret Manager stores runtime credentials.
- External HTTPS load balancer serves `dailyzeitgeist.xyz` with managed TLS.
- Cloud Armor protects the API backend service, scoped to auth endpoint bursts.

External source APIs are called only by the ingestion job. User requests read
stored data from Postgres.

## 2. System Context

```text
Browser
  |
  v
dailyzeitgeist.xyz
  |
  v
External HTTPS Load Balancer
  |                         |
  | /api/*                  | all other paths
  v                         v
Cloud Armor              Cloud Run Frontend
  |                         |
  v                         | server-side API fetches use dailyzeitgeist.xyz/api/v1
Cloud Run API <-----------+
  |
  v
Cloud SQL Postgres

Cloud Scheduler
  |
  v
Cloud Run Ingestion Job
  |
  +--> Hacker News
  +--> DEV
  +--> NYT Most Popular
  +--> RAWG
  +--> Football-Data
  +--> Cricket Data
  +--> Gemini via Vertex AI / Google Gen AI SDK
  |
  v
Cloud SQL Postgres

GitHub Actions
  |
  +--> Artifact Registry
  +--> Cloud Run Frontend
  +--> Cloud Run API
  +--> Cloud Run Ingestion Job
  +--> Cloud Run DB Maintenance Job
```

## 3. Key Principles

| Principle | Decision |
|---|---|
| Precompute trends | Source APIs run in ingestion only. Page requests use stored data. |
| Keep failures isolated | One source failure logs an `IngestionRun` failure and does not stop other sources. |
| Batch AI only | Gemini summaries are generated during ingestion and stored. |
| Source verification first | No placeholder adapters, secrets, or seed rows for unverified sources. |
| Browser auth | Django session cookies and CSRF protection. |
| Same-origin API | Browser calls use `/api/v1` under `dailyzeitgeist.xyz`. |
| Controlled public edge | Cloud Run ingress is restricted; public traffic enters through the load balancer. |
| Terraform/CD split | Terraform owns infrastructure; CD owns runtime revisions and secret attachment. |

## 4. Main Components

### Django API

- Serves `/api/v1/dashboard/`.
- Serves category detail data.
- Handles signup, signin, logout, email verification, password reset, CSRF, and
  current-user endpoints.
- Rate-limits public auth mutations by IP and email.
- Reads and writes saved category preferences.
- Reads stored snapshots, trend items, ingestion freshness, and AI summaries.
- Does not call source APIs or Gemini during user requests.

### Next.js Frontend

- Renders dashboard and category detail pages.
- Uses same-origin browser calls to `/api/v1`.
- Uses `SERVER_API_BASE_URL=https://dailyzeitgeist.xyz/api/v1` for server-side
  API fetches.
- Shows stored AI summaries.
- Shows source-specific trend cards and sports match cards.
- Defaults the Sports page to cricket and keeps cricket and football separate.

### Ingestion Job

- Reads active `CategorySourceConfig` rows.
- Runs each registered adapter.
- Writes `IngestionRun`, `TrendSnapshot`, and `TrendItem` rows.
- Generates `CategoryAISummary` rows after snapshots are written.
- Generates source-specific Sports summaries for cricket and football.

Registered adapters:

- `hackernews`
- `devto`
- `nytimes`
- `rawg`
- `football_data`
- `cricket_data`

### DB Maintenance Job

- Reuses the backend API image.
- Runs deployment-time management commands such as:
  - `python manage.py migrate --noinput`
  - `python manage.py seed_categories`
- Connects to Cloud SQL using the same runtime DB configuration as the API.
- Starts, runs the command, and exits.

### Cloud SQL

Primary application store:

- users
- Django sessions
- email verification OTPs
- password reset OTPs
- categories
- category source configs
- user category preferences
- ingestion runs
- trend snapshots
- trend items
- category AI summaries

### Secret Manager

Current required secret containers:

- `django-secret-key`
- `db-password`
- `nytimes-api-key`
- `rawg-api-key`
- `football-data-api-key`
- `cricket-data-api-key`
- `smtp-host`
- `smtp-host-user`
- `smtp-host-password`

## 5. Data Model

```text
User
  -> EmailVerificationOTP
  -> PasswordResetOTP
  -> UserCategoryPreference -> Category

Category
  -> CategorySourceConfig
  -> TrendSnapshot
  -> CategoryAISummary

TrendSnapshot
  -> IngestionRun
  -> TrendItem
```

## 6. API Shape

Important endpoints:

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/health/` | Health check |
| GET | `/api/v1/dashboard/` | Dashboard categories, source groups, items, summaries |
| GET | `/api/v1/categories/` | Active category list |
| GET | `/api/v1/categories/{slug}/trends/` | Category detail payload |
| GET/PATCH | `/api/v1/categories/preferences/` | Saved category preferences |
| GET | `/api/v1/auth/csrf/` | CSRF cookie bootstrap |
| POST | `/api/v1/auth/signup/` | Create account and send OTP |
| POST | `/api/v1/auth/verify-email/` | Verify registration OTP |
| POST | `/api/v1/auth/resend-verification/` | Resend registration OTP |
| POST | `/api/v1/auth/login/` | Sign in |
| POST | `/api/v1/auth/logout/` | Sign out |
| GET | `/api/v1/auth/me/` | Current user |
| POST | `/api/v1/auth/password-reset/request/` | Send password reset OTP |
| POST | `/api/v1/auth/password-reset/confirm/` | Verify OTP and set new password |

## 7. CI/CD

CI runs on every push and pull request:

1. Starts a Postgres service container.
2. Installs Python 3.12 dependencies.
3. Runs Ruff.
4. Runs mypy.
5. Runs migrations.
6. Runs pytest.

On pushes to `main`, CD:

1. Builds API, ingestion job, and frontend images.
2. Pushes images to Artifact Registry.
3. Creates or updates a reusable Cloud Run DB maintenance job.
4. Runs migrations.
5. Runs `python manage.py seed_categories`.
6. Deploys frontend and API to Cloud Run.
7. Updates the ingestion Cloud Run Job image.
8. Attaches runtime secrets through `--set-secrets`.
9. Smoke-tests backend health and frontend availability at the custom domain.

## 8. Security

| Concern | Approach |
|---|---|
| User auth | Django session auth with CSRF-protected browser requests. |
| Email verification | One-time code stored hashed with TTL and attempt limits. |
| Password reset | Separate OTP model using the same TTL/cooldown pattern. |
| Auth abuse | Cloud Armor throttles `/api/v1/auth/`; Django also applies app-level IP/email rate limits. |
| Same-origin cookies | Production browser API calls stay under `dailyzeitgeist.xyz/api/v1`. |
| Cloud Run exposure | Frontend and API ingress are restricted to internal/load-balancer traffic. |
| Secrets | Secret Manager env injection at Cloud Run startup. |
| Terraform state | No secret values are stored in Terraform state. |
| GitHub to GCP | Workload Identity Federation, no JSON service account key. |
| SQL | Django ORM; no raw SQL for request paths. |

## 9. Deferred Design Areas

These are intentionally not active in the current implementation:

- Response caching beyond Postgres-backed reads.
- Alternate auth providers.
- Weekly digest email provider.
- Cross-platform topic embeddings.
- Sentiment classification.
- Additional source adapters that have not completed live verification.
