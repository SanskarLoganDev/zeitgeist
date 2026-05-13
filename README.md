# Zeitgeist

A personalised social media and internet trend aggregation platform. Collects
trending content daily from Reddit, Hacker News, YouTube, arXiv, PubMed, TMDB,
Steam, and NASA — normalises it into a unified dashboard, and uses Google Gemini
to summarise what is trending and why.

---

## Current status

**Phase:** 1 — Foundation  
**Week:** 1 — Project scaffold + CI/CD  
**Last updated:** 2026-05-13

---

## Requirements progress

### Phase 1 — Foundation (current)

| ID | Requirement | Status |
|---|---|---|
| FR-01 | Google OAuth login + JWT auth | ⬜ Pending |
| FR-04 | Home dashboard — top 5 per category | ⬜ Pending |
| FR-05 | Category detail page — top 10–20 items | ⬜ Pending |
| FR-06 | Trend cards (title, source badge, score, link) | ⬜ Pending |
| FR-11 | Daily ingestion via Cloud Scheduler at 03:00 UTC | ⬜ Pending |
| FR-12 | Snapshot storage — timestamped per run | ⬜ Pending |
| FR-13 | Graceful source failure with stale indicator | ⬜ Pending |
| FR-19 | Django admin — ingestion run log + manual trigger | ⬜ Pending |

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

### Status key

| Symbol | Meaning |
|---|---|
| ⬜ | Not started |
| 🔧 | In progress |
| ✅ | Complete |
| 🧪 | Complete — pending test |

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

### 1. Start local Postgres

```bash
docker-compose up -d
```

### 2. Set up Python environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your Reddit API and Google OAuth credentials
```

### 4. Run migrations and start the server

```bash
python manage.py migrate
python manage.py runserver
```

API is now at `http://localhost:8000`  
Health check: `http://localhost:8000/api/v1/health/`  
Admin panel: `http://localhost:8000/admin/`

### 5. Run tests

```bash
pytest
```

### 6. Lint and type check

```bash
ruff check .
mypy apps config
```

---

## Infrastructure — GCP (Terraform)

All GCP infrastructure is managed by Terraform. One `apply` provisions everything.
One `destroy` tears it all down.

### First-time setup

```bash
cd infra

# Copy and fill in your GCP project ID
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars — set gcp_project_id

# Initialise Terraform
terraform init

# Preview what will be created
terraform plan

# Provision everything
terraform apply
```

### Teardown

```bash
cd infra
terraform destroy
```

### What Terraform manages

| Resource | Phase | Notes |
|---|---|---|
| Artifact Registry | 1 | Docker image repo |
| Cloud SQL (Postgres) | 1 | db-f1-micro |
| Secret Manager secrets | 1 | Resources only — values set manually |
| Cloud Run (API) | 1 | Django REST API |
| Cloud Run Job (ingest) | 1 | Daily ingestion + AI |
| Cloud Scheduler (daily) | 1 | Fires ingestion at 03:00 UTC |
| Memorystore (Redis) | 2 | Added in Phase 2 |
| Cloud Run (frontend) | 3 | Next.js — added in Phase 3 |
| Cloud Load Balancer | 3 | HTTPS + custom domain |
| Cloud Monitoring | 3 | Alerts before public launch |

### GitHub Actions secrets required

Set these in your GitHub repo → Settings → Secrets → Actions:

| Secret | Description |
|---|---|
| `GCP_PROJECT_ID` | Your GCP project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | WIF provider resource name |
| `GCP_DEPLOY_SA_EMAIL` | Deployment service account email |
| `GCP_APP_SA_EMAIL` | App service account email |
| `CLOUD_SQL_CONNECTION_NAME` | From `terraform output cloud_sql_connection_name` |

---

## Project structure

```
zeitgeist/
├── .github/
│   └── workflows/
│       ├── ci.yml              # Lint + test on every push
│       └── cd.yml              # Build + deploy on merge to main
├── backend/
│   ├── apps/
│   │   ├── accounts/           # User model, Google OAuth, JWT
│   │   ├── categories/         # Category, SubredditConfig models + API
│   │   ├── trends/             # TrendItem, TrendSnapshot, dashboard API
│   │   ├── ingestion/          # Ingestion orchestrator + source adapters
│   │   │   └── adapters/       # Reddit, HN, YouTube, arXiv, PubMed, TMDB, Steam, NASA
│   │   └── ai/                 # Vertex AI client, Gemini prompts, embeddings
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── tests/
│   ├── Dockerfile              # API server image
│   ├── Dockerfile.job          # Ingestion job image
│   ├── manage.py
│   ├── run_job.py              # Cloud Run Job entrypoint
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pyproject.toml          # ruff + mypy + pytest config
│   └── .env.example
├── frontend/                   # Next.js — scaffolded in Phase 1 Week 3
├── infra/
│   ├── main.tf                 # Root module — composes all modules
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars.example
│   └── modules/
│       ├── artifact_registry/
│       ├── cloud_sql/
│       ├── cloud_run/          # API service + ingestion job + service account
│       ├── scheduler/          # Daily ingestion + weekly digest (Phase 3)
│       └── secrets/            # Secret Manager resources
├── design-docs/                # READ ONLY — do not modify
│   ├── 01_requirements.md
│   ├── 02_phase_plan.md
│   └── 03_high_level_design.md
├── docker-compose.yml          # Local Postgres (and Redis in Phase 2)
└── .gitignore
```

---

## Design documents

Full requirements, phase plan, and high-level architecture are in [`design-docs/`](./design-docs/).  
These documents are the source of truth — code follows the design, not the other way around.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Django 5.1 + Django REST Framework |
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind |
| Database | Postgres 16 (Cloud SQL) |
| Cache | Redis (Memorystore) — Phase 2 |
| AI | Vertex AI — Gemini (summaries + sentiment), text-embedding-004 (cross-platform detection) |
| Infrastructure | GCP — Cloud Run, Cloud SQL, Cloud Scheduler, Secret Manager, Artifact Registry |
| IaC | Terraform |
| CI/CD | GitHub Actions + Workload Identity Federation |
| Linting | ruff |
| Type checking | mypy (strict) |
| Testing | pytest + pytest-django |
