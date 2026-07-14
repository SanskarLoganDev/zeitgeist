# Zeitgeist - High-Level Design

**Version:** 2.0
**Status:** Updated to current implementation
**Last Updated:** 2026-07-14

## 1. System Overview

Zeitgeist is a decoupled web app:

- Next.js frontend hosted on Cloud Run.
- Django REST Framework API hosted on Cloud Run.
- Cloud Run Job for ingestion and AI summaries.
- Cloud Scheduler triggers ingestion daily.
- Cloud SQL Postgres stores users, categories, preferences, snapshots, items,
  ingestion logs, OTPs, and AI summaries.
- Secret Manager stores runtime credentials.

External source APIs are called only by the ingestion job. User requests read
stored data from Postgres.

## 2. System Context

```text
Browser
  |
  v
Next.js Frontend (Cloud Run)
  |
  v
Django API (Cloud Run)
  |
  v
Cloud SQL Postgres

Cloud Scheduler
  |
  v
Cloud Run Job
  |
  +--> Hacker News
  +--> DEV
  +--> NYT Most Popular
  +--> RAWG
  +--> Football-Data
  +--> Gemini via Vertex AI / Google Gen AI SDK
  |
  v
Cloud SQL Postgres
```

## 3. Key Principles

| Principle | Decision |
|---|---|
| Precompute trends | Source APIs run in ingestion only. Page requests use stored data. |
| Keep failures isolated | One source failure logs an `IngestionRun` failure and does not stop other sources. |
| Batch AI only | Gemini summaries are generated during ingestion and stored. |
| Source verification first | No placeholder adapters, secrets, or seed rows for unverified sources. |
| Browser auth | Django session cookies and CSRF protection. |
| Terraform/CD split | Terraform owns infrastructure; CD owns runtime revisions and secret attachment. |

## 4. Main Components

### Django API

- Serves `/api/v1/dashboard/`.
- Serves category detail data.
- Handles signup, signin, logout, email verification, password reset, CSRF, and
  current-user endpoints.
- Reads and writes saved category preferences.
- Does not call source APIs during requests.

### Next.js Frontend

- Renders dashboard and category detail pages.
- Calls the Django API with browser session cookies.
- Shows stored AI summaries.
- Shows source-specific trend cards.

### Ingestion Job

- Reads active `CategorySourceConfig` rows.
- Runs each registered adapter.
- Writes `IngestionRun`, `TrendSnapshot`, and `TrendItem` rows.
- Generates `CategoryAISummary` rows after snapshots are written.

Registered adapters:

- `hackernews`
- `devto`
- `nytimes`
- `rawg`
- `football_data`

### Cloud SQL

Primary application store:

- users
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

On pushes to `main`, CD:

1. Builds API, job, and frontend images.
2. Pushes images to Artifact Registry.
3. Runs migrations in a reusable Cloud Run maintenance job.
4. Runs `python manage.py seed_categories`.
5. Deploys API, ingestion job, and frontend to Cloud Run.
6. Attaches runtime secrets through `--set-secrets`.
7. Smoke-tests backend health.

CI runs ruff, mypy, migrations, and pytest.

## 8. Security

| Concern | Approach |
|---|---|
| User auth | Django session auth with CSRF-protected browser requests. |
| Email verification | One-time code stored hashed with TTL and attempt limits. |
| Password reset | Separate OTP model using the same TTL/cooldown pattern. |
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
