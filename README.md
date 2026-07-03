# Zeitgeist

A personalised social media and internet trend aggregation platform. Collects
trending content daily from Reddit, Hacker News, YouTube, arXiv, PubMed, TMDB,
Steam, and NASA — normalises it into a unified dashboard, and uses Google Gemini
to summarise what is trending and why.

---

## Current status

**Phase:** 1 — Foundation
**Week:** 1 — Project scaffold + CI/CD
**Last updated:** 2026-07-03

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
- [ ] `terraform apply` — Cloud SQL + Cloud Run + Scheduler provisioned
- [ ] Secret values set in Secret Manager
- [ ] First push to main — CI green, CD deploys, health check returns 200

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

```cmd
# Shut down between sessions (stops Cloud SQL billing)
gcloud sql instances patch zeitgeist-pg --activation-policy=NEVER --project zeitgeist-499322

# Resume when starting work again
gcloud sql instances patch zeitgeist-pg --activation-policy=ALWAYS --project zeitgeist-499322
```

---

## Requirements progress

### Phase 1 — Foundation (current)

| ID | Requirement | Status |
|---|---|---|
| FR-01 | Google OAuth login + JWT auth | ⬜ Pending — Week 3 |
| FR-04 | Home dashboard — top 5 per category | ⬜ Pending — Week 3 |
| FR-05 | Category detail page — top 10–20 items | ⬜ Pending — Week 3 |
| FR-06 | Trend cards (title, source badge, score, link) | ⬜ Pending — Week 3 |
| FR-11 | Daily ingestion via Cloud Scheduler at 03:00 UTC | ⬜ Pending — Week 2 |
| FR-12 | Snapshot storage — timestamped per run | ⬜ Pending — Week 2 |
| FR-13 | Graceful source failure with stale indicator | ⬜ Pending — Week 4 |
| FR-19 | Django admin — ingestion run log + manual trigger | ⬜ Pending — Week 2 |

### Phase 2 — Intelligence (not started)

| ID | Requirement | Status |
|---|---|---|
| FR-03 | Inline category preference editing from dashboard | ⬜ Not started |
| FR-07 | Time window filter (today / 7d / 30d / 90d) | ⬜ Not started |
| FR-08 | Trend charts per category | ⬜ Not started |
| FR-09 | Source platform filter | ⬜ Not started |
| FR-14 | Gemini AI trend summary per category | ⬜ Not started |
| FR-20 | Admin-configurable categories and subreddit lists | ⬜ Not started |

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

Move to Phase 2 only when **all three** are true:

- [ ] Daily ingestion has run successfully at least **3 consecutive times**
- [ ] Dashboard loads with real data in **under 2 seconds** from localhost
- [ ] Google OAuth login works — user persists in DB, JWT valid across page refreshes

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
python manage.py runserver
```

API: `http://localhost:8000`
Health check: `http://localhost:8000/api/v1/health/`
Admin: `http://localhost:8000/admin/`

### 5. Run tests

```cmd
pytest
```

### 6. Lint and type check

```cmd
ruff check .
mypy apps config
```

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
# Shut down (stops Cloud SQL billing ~$0.23/day)
gcloud sql instances patch zeitgeist-pg --activation-policy=NEVER --project zeitgeist-499322

# Resume
gcloud sql instances patch zeitgeist-pg --activation-policy=ALWAYS --project zeitgeist-499322
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
| Cloud Run Frontend | 3 | Next.js — Phase 3 |
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
│   │   ├── accounts/       # User model, Google OAuth, JWT
│   │   ├── categories/     # Category, SubredditConfig models + API
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
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind |
| Database | Postgres 16 (Cloud SQL) |
| Cache | Redis (Memorystore) — Phase 2 |
| AI | Vertex AI — Gemini + text-embedding-004 |
| Infrastructure | GCP — Cloud Run, Cloud SQL, Cloud Scheduler, Secret Manager, Artifact Registry |
| IaC | Terraform |
| CI/CD | GitHub Actions + Workload Identity Federation |
| Linting | ruff |
| Type checking | mypy (strict) |
| Testing | pytest + pytest-django |
