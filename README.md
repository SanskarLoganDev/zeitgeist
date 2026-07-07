# Zeitgeist

A personalised social media and internet trend aggregation platform. Collects
trending content daily from verified public APIs such as Hacker News, YouTube,
arXiv, PubMed, TMDB, and NASA — normalises it into a unified dashboard, and uses
Google Gemini to summarise what is trending and why.

---

## Current status

**Phase:** 2 — Public demo and source coverage
**Status:** Frontend Cloud Run deployment wiring in progress
**Last updated:** 2026-07-07

### Week 1 checklist

- [x] Django project structure created
- [x] All app stubs created (accounts, categories, trends, ingestion, ai)
- [x] User model stub added — migrations can now be generated
- [x] Settings split: base / development / production
- [x] CI/CD workflows written (ci.yml + cd.yml)
- [x] Dockerfile + Dockerfile.job written
- [x] Terraform infrastructure written (all 5 modules)
- [x] Health check endpoint + test written
- [x] GCP project created and APIs enabled
- [x] Workload Identity Federation configured
- [x] GitHub Actions secrets configured
- [x] `terraform apply` — Cloud SQL + Cloud Run + Scheduler provisioned
- [x] Secret values set in Secret Manager
- [x] First push to main — CI green, CD deploys, health check returns 200

### Current focus

Phase 1 is complete as a working end-to-end slice. Phase 2 is focused on making
the app useful as a public demo while keeping source additions evidence-based.

- Django backend deploys to Cloud Run and responds successfully at
  `https://zeitgeist-api-opowb5bpna-uc.a.run.app/api/v1/health/`.
- Hacker News, DEV, NYT Most Popular, and RAWG ingestion are implemented as
  verified sources for Tech, News, and Gaming.
- Production Cloud SQL has been verified with seeded categories, ingestion runs,
  snapshots, and trend items.
- Next.js dashboard and category detail pages render stored trend data from the
  Django API.
- Simple Django session auth is implemented locally with email/password signup,
  login, logout, CSRF protection, and saved category preferences.
- Anonymous users can view the dashboard and choose preferences locally.
- Logged-in users can save preferences to the database and restore them across
  refreshes/devices.
- GitHub Actions CD builds and deploys the API, ingestion job, and frontend
  container images to Cloud Run.

Phase 1 scope adjustment: the original design docs called for Google OAuth +
JWT in Phase 1. For current development, auth was intentionally simplified to
Django session auth with email/password so the saved-preferences product loop can
be tested before adding Google OAuth, JWT, and production email verification.

Immediate next steps:

1. Push the frontend deployment workflow changes to `main`.
2. Confirm CD builds and deploys `zeitgeist-frontend`.
3. Confirm CD updates API `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` with
   the deployed frontend URL.
4. Open the public frontend URL and verify dashboard, category pages, signup,
   login, logout, and preference save/restore.
5. Verify cloud ingestion has current data for Tech, News, and Gaming.

Reddit is deferred. As of 2026, Reddit API access for personal scripts is gated
by approval and is not reliable enough for Week 1/2 development. Do not add
Reddit back into active models, seed data, secrets, or orchestration until API
access is approved and a live fetch verifies the response shape.

Steam/IGDB is intentionally deferred because it is the riskiest source in the
initial list: IGDB requires Twitch OAuth and Steam Spy is less official than the
other APIs.

### Source verification rule

Before a source is implemented, verify the API first:

1. Confirm the API is publicly available or that required approval/key access is already granted.
2. Run a live fetch against the endpoint and save the response shape in notes/tests.
3. Confirm auth, rate limits, cost, and terms are acceptable for the project.
4. Only then add models, adapter code, secrets, CI/CD wiring, and tests.

---

## Key design decisions

### Secret Manager — values managed outside Terraform

Terraform creates Secret Manager resource shells only. Secret values are
populated via `infra\secrets.bat` AFTER `terraform apply` creates the shells.
Cloud Run secret environment variables are attached later by the CD pipeline
with `gcloud run ... --set-secrets`. This is intentional.

**Why:** Terraform writes everything it manages into `terraform.tfstate` — plain JSON.
If secret values were stored via `google_secret_manager_secret_version`, they would
appear in plaintext in the state file and risk being exposed if the file is ever
shared, committed, or accessed without authorisation.

**Why Cloud Run reads secrets at container startup, not on demand:**
Cloud Run injects secrets as environment variables before the container process starts.
Environment variables are set once at OS process creation — there is no mechanism
to inject new env vars into an already-running process. Django reads `os.environ`
at settings load time, which happens during startup.

For the Cloud Run Job (ingestion), startup and scheduler trigger are the same event —
the scheduler causes a fresh container to start, secrets are injected, the job runs,
the container exits. There is no idle container waiting between scheduler fires.

**Why Terraform does not attach secrets to Cloud Run during bootstrap:**
After `terraform destroy`, Secret Manager resources and all secret versions are gone.
The first `terraform apply` can create empty secret shells, but there is no
`latest` version yet. If Terraform attaches `django-secret-key:latest` to Cloud
Run in that same apply, GCP validates the missing version and Cloud Run creation
fails. Terraform therefore creates the Cloud Run service/job with a placeholder
image and no secret refs. CD attaches populated secrets to the real Django
revision after `infra\secrets.bat` has created secret versions.

**Why Terraform ignores Cloud Run image/env drift after CD:**
GitHub Actions CD owns runtime deployments: it updates the real API/job images
and attaches secret environment variables. Terraform owns the surrounding
infrastructure shape. The Cloud Run service/job therefore use lifecycle ignores
for container image and env fields so a later `terraform plan` does not try to
roll production back to placeholder images or remove CD-attached secrets.

**In production:** `terraform destroy` is almost never run. Infrastructure is permanent.
Secrets are populated once during initial project setup and never wiped.
`secrets.bat` exists only because we destroy/recreate infrastructure during
development to save cost. In a production system, secret population would be
automated in the CD pipeline.

### Correct order after every terraform destroy

```
1. cd infra && terraform apply    ← creates infra, empty secret shells, placeholder Cloud Run with no secret refs
2. Copy terraform output api_url hostname into infra\terraform.tfvars allowed_hosts
3. cd .. && infra\secrets.bat     ← fills the secret shells with values
4. cd infra && terraform apply    ← updates non-secret Cloud Run env vars such as ALLOWED_HOSTS
5. cd .. && git push origin main  ← CD deploys Django image and attaches secrets with --set-secrets
```

### Cost management during development

Cloud Run with `min_instance_count = 1` costs ~$1.40/day even with zero traffic.
All Cloud Run services are set to `min_instance_count = 0` in Terraform.
The only persistent cost is Cloud SQL (~$7/month, ~$0.23/day).

End of day:

```cmd
# Pause scheduled ingestion so it does not run while Cloud SQL is stopped
gcloud scheduler jobs pause zeitgeist-daily-ingest --location us-central1 --project zeitgeist-499322

# Stop Cloud SQL compute billing
gcloud sql instances patch zeitgeist-pg --activation-policy=NEVER --project zeitgeist-499322
```

Start of day:

```cmd
# Restart Cloud SQL
gcloud sql instances patch zeitgeist-pg --activation-policy=ALWAYS --project zeitgeist-499322

# Resume scheduled ingestion
gcloud scheduler jobs resume zeitgeist-daily-ingest --location us-central1 --project zeitgeist-499322
```

Optional status checks:

```cmd
gcloud sql instances describe zeitgeist-pg --project zeitgeist-499322 --format="value(settings.activationPolicy,state)"
gcloud scheduler jobs describe zeitgeist-daily-ingest --location us-central1 --project zeitgeist-499322 --format="value(state)"
```

You do not need to stop Cloud Run services/jobs manually. They are configured
with `min_instance_count = 0`, so they scale to zero when idle.

### Database maintenance job

The CD workflow uses one reusable Cloud Run Job for production database setup:

```text
zeitgeist-db-maintenance
```

This is not an API. It is a maintenance job that CD updates and executes before
deploying the API. It runs:

```cmd
python manage.py migrate --noinput
python manage.py seed_categories
```

`seed_categories` is idempotent, so it is safe to run every deploy. This keeps
production Cloud SQL from having the schema without the starter application data
that ingestion depends on.

Older deployments created one-off jobs named `zeitgeist-migrate-N`. Those can
be deleted after CD finishes.

List Cloud Run jobs:

```cmd
gcloud run jobs list --region us-central1 --project zeitgeist-499322
```

Delete old migration jobs:

```cmd
gcloud run jobs delete zeitgeist-migrate-15 --region us-central1 --project zeitgeist-499322 --quiet
gcloud run jobs delete zeitgeist-migrate-16 --region us-central1 --project zeitgeist-499322 --quiet
gcloud run jobs delete zeitgeist-migrate-17 --region us-central1 --project zeitgeist-499322 --quiet
gcloud run jobs delete zeitgeist-migrate-18 --region us-central1 --project zeitgeist-499322 --quiet
gcloud run jobs delete zeitgeist-migrate-20 --region us-central1 --project zeitgeist-499322 --quiet
```

Do not delete:

```text
zeitgeist-api
zeitgeist-ingest
zeitgeist-db-maintenance
```

---

## Requirements progress

### Phase 1 — Foundation

| ID | Requirement | Status |
|---|---|---|
| FR-01 | Auth | ✅ Revised — Django session auth with email/password, CSRF, signup/login/logout, saved preferences |
| FR-04 | Home dashboard — top 5 per category | ✅ Done — Next.js dashboard renders real Hacker News data |
| FR-05 | Category detail page — top 10–20 items | ✅ Done — `/category/{slug}` consumes category trends API |
| FR-06 | Trend cards (title, source, score, link) | ✅ Done |
| FR-11 | Daily ingestion via Cloud Scheduler at 03:00 UTC | ✅ Provisioned — manual Cloud Run job execution verified |
| FR-12 | Snapshot storage — timestamped per run | ✅ Done |
| FR-13 | Graceful source failure with stale indicator | ✅ Initial support — API returns fresh/stale/missing status |
| FR-19 | Django admin — ingestion run log | ✅ Done — models registered and ingestion runs visible |

### Phase 2 — Public demo and intelligence

| ID | Requirement | Status |
|---|---|---|
| FR-03 | Inline category preference editing from dashboard | ⬜ Not started |
| FR-07 | Time window filter (today / 7d / 30d / 90d) | ⬜ Not started |
| FR-08 | Trend charts per category | ⬜ Not started |
| FR-09 | Source platform filter | ✅ Initial category-page source buttons |
| FR-14 | Gemini AI trend summary per category | ⬜ Not started |
| FR-20 | Admin-configurable categories and source mappings | ⬜ Not started |
| DEP-01 | Public frontend deployment | 🚧 CD wiring in progress — Cloud Run service `zeitgeist-frontend` |

### Phase 3 — Polish & Ship (not started)

| ID | Requirement | Status |
|---|---|---|
| FR-02 | Interest onboarding flow on first login | ⬜ Not started |
| FR-10 | "Trending everywhere" cross-platform cards | ⬜ Not started |
| FR-15 | Cross-platform topic detection via embeddings | ⬜ Not started |
| FR-16 | Sentiment tags on trend cards | ⬜ Not started |
| FR-18 | Weekly personalised digest email (SendGrid) | ⬜ Not started |

---

## Phase 1 exit gate

Revised local-first Phase 1 gate:

- [x] End-to-end Hacker News data path works from external API to frontend.
- [x] Dashboard loads with real data from localhost.
- [x] User can create an account, sign in, save preferences, refresh, and restore
  saved preferences locally.
- [x] After commit/push, CI and CD must pass with the new backend code.

Deferred from original Phase 1 gate:

- Google OAuth + JWT is replaced for now by Django session auth.
- Email verification is not implemented yet.
- Production/cloud frontend auth is moving into Phase 2 with a Cloud Run
  frontend origin and explicit production cross-origin cookie/CSRF settings.

---

## Local development setup

### Prerequisites

- Python 3.12+
- Docker Desktop (for local Postgres)
- Node.js 20+ (for Next.js frontend — Phase 1 Week 3)
- [Terraform](https://developer.hashicorp.com/terraform/install) (for infra provisioning)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install) (for GCP operations)

### 1. Start local Postgres

```cmd
docker compose up -d
```

### 2. Set up Python environment

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 3. Configure environment variables

```cmd
copy .env.example .env
# Edit .env — fill in DJANGO_SECRET_KEY and DB credentials
```

### 4. Run migrations and start the server

```cmd
python manage.py migrate
python manage.py runserver localhost:8000
```

API: `http://localhost:8000`
Health check: `http://localhost:8000/api/v1/health/`
Admin: `http://localhost:8000/admin/`

### 5. Seed categories and run local ingestion

`seed_categories` creates the starter categories and source mappings in your
local database. The ingestion job then reads those mappings, fetches external
source data, and writes `IngestionRun`, `TrendSnapshot`, and `TrendItem` rows.

```cmd
python manage.py seed_categories
```

For local ingestion, force development settings so Django loads `backend\.env`.
This is needed because `run_job.py` defaults to production settings for Cloud
Run, where secrets are injected by GCP Secret Manager instead of read from
`.env`.

```powershell
$env:DJANGO_SETTINGS_MODULE="config.settings.development"
python run_job.py
```

After it finishes, check:

```text
http://localhost:8000/api/v1/dashboard/
```

For Tech, you should see source groups such as `hackernews` and `devto`.

### 6. Run tests

```cmd
pytest
```

### 7. Lint and type check

```cmd
ruff check .
mypy apps config
```

### 8. Run the local frontend

```cmd
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:3000`

For local auth testing, `frontend\.env.local` should point at the local backend:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

`frontend\.env.local` is gitignored and should not be committed.

### 9. Local auth test flow

1. Open `http://localhost:3000`.
2. Click `Create account`.
3. Create an email/password account.
4. Select category preferences and save.
5. Refresh the page and confirm preferences restore.
6. Sign out and sign back in.

---

## Infrastructure — GCP (Terraform)

### Every time after terraform destroy — exact order

```cmd
cd E:\Coding-practice\Projects\zeitgeist\infra
terraform apply                        ← step 1: creates infra + placeholder Cloud Run, no secret refs

terraform output api_url               ← step 2: copy hostname only, no https://
# Edit infra\terraform.tfvars:
# allowed_hosts = "zeitgeist-api-xxxxx-uc.a.run.app"

cd E:\Coding-practice\Projects\zeitgeist
infra\secrets.bat                      ← step 3: fills shells with values
cd infra
terraform apply                        ← step 4: update allowed_hosts
cd E:\Coding-practice\Projects\zeitgeist
git push origin main                   ← step 5: deploy Django image + attach secrets via CD
```

### Cost management

```cmd
# End of day
gcloud scheduler jobs pause zeitgeist-daily-ingest --location us-central1 --project zeitgeist-499322
gcloud sql instances patch zeitgeist-pg --activation-policy=NEVER --project zeitgeist-499322

# Start of day
gcloud sql instances patch zeitgeist-pg --activation-policy=ALWAYS --project zeitgeist-499322
gcloud scheduler jobs resume zeitgeist-daily-ingest --location us-central1 --project zeitgeist-499322
```

### What Terraform manages

| Resource | Phase | Notes |
|---|---|---|
| Artifact Registry | 1 | Docker image repo |
| Cloud SQL (Postgres) | 1 | db-f1-micro, ~$7/month |
| Secret Manager secrets | 1 | Shells only — values set via secrets.bat |
| Cloud Run API | 1 | Placeholder during Terraform bootstrap; Django image + secrets attached by CD |
| Cloud Run Job | 1 | Placeholder during Terraform bootstrap; ingestion image + secrets attached by CD |
| Cloud Scheduler | 1 | Fires ingestion at 03:00 UTC daily |
| Memorystore (Redis) | 2 | Added in Phase 2 |
| Cloud Run Frontend | 2 | Next.js image deployed by CD as `zeitgeist-frontend` |
| Cloud Load Balancer | 3 | HTTPS + custom domain |
| Cloud Monitoring | 3 | Alerts before public launch |

---

## GitHub Actions secrets (already configured)

| Secret | Value |
|---|---|
| `GCP_PROJECT_ID` | `zeitgeist-499322` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/82456441710/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `GCP_DEPLOY_SA_EMAIL` | `zeitgeist-app@zeitgeist-499322.iam.gserviceaccount.com` |
| `GCP_APP_SA_EMAIL` | `zeitgeist-app@zeitgeist-499322.iam.gserviceaccount.com` |
| `CLOUD_SQL_CONNECTION_NAME` | `zeitgeist-499322:us-central1:zeitgeist-pg` |

---

## Project structure

```
zeitgeist/
├── .github/workflows/
│   ├── ci.yml              # Lint + test on every push
│   └── cd.yml              # Build + deploy on merge to main
├── backend/
│   ├── apps/
│   │   ├── accounts/       # User model, session auth, future Google OAuth/JWT
│   │   ├── categories/     # Category, source config models + API
│   │   ├── trends/         # TrendItem, TrendSnapshot, dashboard API
│   │   ├── ingestion/      # Orchestrator + source adapters
│   │   └── ai/             # Vertex AI client, Gemini prompts, embeddings
│   ├── config/settings/    # base.py, development.py, production.py
│   ├── Dockerfile          # API server image (gunicorn, port 8000)
│   ├── Dockerfile.job      # Ingestion job image
│   ├── manage.py
│   ├── run_job.py          # Cloud Run Job entrypoint
│   └── pyproject.toml      # ruff + mypy + pytest config
├── frontend/               # Next.js — Phase 1 Week 3
├── infra/
│   ├── main.tf
│   ├── variables.tf
│   ├── terraform.tfvars    # gitignored — contains real values
│   ├── secrets.bat         # gitignored — populates Secret Manager values
│   └── modules/
│       ├── artifact_registry/
│       ├── cloud_sql/
│       ├── cloud_run/
│       ├── scheduler/
│       └── secrets/
├── troubleshooting/        # gitignored — all bugs and fixes documented here
├── design-docs/            # READ ONLY
└── docker-compose.yml
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 5.1 + Django REST Framework |
| Frontend | Next.js 16 (App Router) + TypeScript + plain CSS |
| Database | Postgres 16 (Cloud SQL) |
| Cache | Redis (Memorystore) — Phase 2 |
| AI | Vertex AI — Gemini + text-embedding-004 |
| Infrastructure | GCP — Cloud Run, Cloud SQL, Cloud Scheduler, Secret Manager, Artifact Registry |
| IaC | Terraform |
| CI/CD | GitHub Actions + Workload Identity Federation |
| Linting | ruff |
| Type checking | mypy (strict) |
| Testing | pytest + pytest-django |
