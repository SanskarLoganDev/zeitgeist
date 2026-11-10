# CLAUDE.md - Zeitgeist Project Context

This file gives an AI assistant enough current project context to continue work
without relying on chat history.

## Project Overview

Zeitgeist is a personalized internet trend aggregation dashboard. It collects
trending items from verified APIs during a scheduled ingestion job, stores them
in Postgres, and serves dashboard/category pages from stored data.

Repo: `E:\Coding-practice\Projects\zeitgeist`  
GCP project: `zeitgeist-499322`  
Region: `us-central1`  
Frontend: Next.js on Cloud Run  
Backend: Django + Django REST Framework on Cloud Run  
Batch: Cloud Run Job triggered by Cloud Scheduler  
Database: Cloud SQL Postgres  
AI: Gemini category summaries through Vertex AI / Google Gen AI SDK

## Current Status

Phase 1 is complete. Phase 2 is in progress.

Implemented:

- Public backend and frontend are deployed and working.
- Dashboard and `/category/[slug]` pages render stored DB data.
- Active verified sources:
  - Tech: Hacker News, DEV
  - News: New York Times Most Popular
  - Gaming: RAWG
  - Sports: Football-Data
- Session auth, CSRF, signup, signin, logout, and saved preferences.
- SMTP OTP email verification for registration.
- Forgot-password OTP flow.
- App-level rate limiting on public auth endpoints.
- Gemini category summaries generated during ingestion and stored in Postgres.
- Production CORS/CSRF supports both observed Cloud Run frontend URL formats.
- React hydration issue #418 was fixed by deterministic UTC timestamp formatting.

Not implemented:

- Time-window charts.
- Cross-platform topic detection.
- Sentiment labels.
- Weekly digest emails.
- Google OAuth/JWT.
- Reddit, NASA, PubMed, TMDB, YouTube, Steam/IGDB, SendGrid.

## Source Rules

Do not add a source unless it has first been API-verified with a live fetch.
Show the live fetch result before coding. Do not add placeholder adapters,
models, secrets, seed rows, or CD wiring for sources we are not implementing now.

Active source keys only:

- `nytimes-api-key`
- `rawg-api-key`
- `football-data-api-key`

## Secret and Infra Rules

Terraform creates Secret Manager containers only. It must not insert secret
values. Secret values are supplied by `infra\secrets.bat` or by CD.

Current active Secret Manager containers:

- `django-secret-key`
- `db-password`
- `nytimes-api-key`
- `rawg-api-key`
- `football-data-api-key`
- `smtp-host`
- `smtp-host-user`
- `smtp-host-password`

Terraform owns stable infrastructure. CD owns runtime Cloud Run images, runtime
environment variables, secret attachment, migrations, and seed execution.

Never run `terraform apply` on behalf of the user. Produce a plan or tell the
user exactly when an apply is needed.

## Local Commands

Backend setup:

```cmd
cd backend
python -m pip install -r requirements-dev.txt
python manage.py migrate
python manage.py seed_categories
python manage.py runserver localhost:8000
```

Local ingestion:

```powershell
cd backend
$env:DJANGO_SETTINGS_MODULE="config.settings.development"
python run_job.py
```

Backend checks:

```cmd
python manage.py makemigrations --check --dry-run
python -m pytest --no-cov
python -m ruff check .
python -m mypy apps config
```

Frontend checks:

```cmd
cd frontend
npm run typecheck
npm run lint
npm run build
```

Terraform checks:

```cmd
cd infra
terraform fmt -check -recursive
terraform validate
terraform plan
```

## Deployment Notes

CD on `main`:

1. Builds API, ingestion job, and frontend images.
2. Runs migrations through the reusable Cloud Run maintenance job.
3. Runs `python manage.py seed_categories`.
4. Deploys API/job/frontend to Cloud Run.
5. Attaches runtime secrets with `--set-secrets`.
6. Runs a backend health smoke test.

If a change adds or removes Terraform-managed resources, the user must review:

```cmd
cd infra
terraform plan
```

Then the user decides whether to run:

```cmd
terraform apply
```

## Troubleshooting Pointers

Known production-only issues are documented in
`troubleshooting\terraform_cicd_issues.md`. Update that file only for issues
actually encountered.

When local works but production fails, check:

- Cloud Run env vars and secret attachment.
- CORS/CSRF exact origins.
- Cloud SQL mount at `/cloudsql`.
- UTC vs browser-local rendering differences.
- CD overwriting manual Cloud Run changes.

## User Preferences

- Explain Django/DRF/Next.js/infra concepts before implementing.
- Keep changes scoped.
- Avoid broad refactors.
- Give one-line commands when asking the user to run commands.
- Remind the user when secrets must be redeployed or Terraform apply is needed.
- For every commit, suggest a clear commit message.

## Redeployment and Security Plan — November 9, 2026

This section supersedes the historical project/status notes above for the new
deployment. Active project: `zeitgeist-514220`; region: `us-central1`; domain:
`dailyzeitgeist.xyz`; Terraform workspace: `default`.

**Current authorized scope:** the user authorized removing Cloud Armor from
Terraform and documenting the reason/change in the existing troubleshooting
files. That configuration change is implemented and validated; the user has
confirmed a successful apply. Do not bundle application, workflow, DNS, billing, or replacement
security-service changes into this task. Never execute `terraform apply` for
the user. No new files are authorized.

### Confirmed blocker and decision

- The project reports zero quota and zero usage for `SECURITY_POLICIES`,
  `SECURITY_POLICY_RULES`, and `SECURITY_POLICY_CEVAL_RULES`.
- Creating a test policy in the console also failed, as confirmed by the user.
- Proceed with deployment without Cloud Armor using the prepared configuration.
- Zero quota is verified; its account-specific cause is not. Do not claim that
  all free-trial accounts prohibit Cloud Armor or that a recent rule change is
  established. The previous trial deployment reportedly used Cloud Armor.
- The Terraform security policy and API backend policy attachment are disabled;
  the user confirmed successful apply. Both are now retained as commented-out
  configuration with the zero-quota reason, at the user's request. Live
  checks now show HTTPS forwarding on port 443. App images are still placeholders
  and TLS is provisioning; application deployment is not yet confirmed.
- User constraints: GCP services only; no Cloudflare, Turnstile, external
  security vendors, or substantial architecture changes. Do not add a gateway,
  proxy tier, shared cache, or replacement service just to replace Cloud Armor.
  If no suitable minimal-change GCP replacement exists, proceed without one.

### Inventory verified by read-only checks

Live service checks and a Terraform refresh/plan produced the following:

| Component | Current status | Work remaining |
|---|---|---|
| API Cloud Run service | Ready with Google's `hello:latest` placeholder | Deploy actual Django image and runtime secrets through CD |
| Frontend Cloud Run service | Ready with the same placeholder | Deploy actual Next.js image through CD |
| `zeitgeist-ingest` job | Exists with the placeholder image | Attach source secrets, deploy job image, then execute ingestion |
| `zeitgeist-pg` Cloud SQL | `RUNNABLE`; database and user tracked | Run migrations and category seed through CD; data contents not inspected |
| Artifact Registry repository | Exists in refreshed Terraform state | Actual app images have not been verified |
| App service account, IAM, WIF pool/provider | Present in refreshed Terraform state | Verify the five GitHub Actions secrets reference this project |
| Ten Secret Manager containers | Present in refreshed Terraform state | Secret version availability has not been verified; do not read values in logs |
| API/frontend serverless NEGs | Present in refreshed Terraform state | API NEG still needs its backend service |
| Frontend backend service | Exists | HTTPS URL map/proxy still needed |
| Global static IP | `34.111.88.93` on HTTP forwarding rule | Verify public DNS points here before HTTPS validation |
| HTTP redirect URL map, proxy, forwarding rule | Exist on port 80 | Redirect destination HTTPS is not ready yet |
| Managed TLS certificate | `PROVISIONING` | Complete HTTPS resources and verify DNS; wait for `ACTIVE` |
| Daily ingestion Scheduler | User confirmed resumed after deployment | Keep enabled for the regular 03:00 UTC refresh; ad hoc refreshes execute Cloud Run directly |
| Database maintenance job | Not shown in live job inventory | CD creates it and runs migrations/seed |

Before the configuration change, the verified plan was **5 to add, 0 to change, 0 to
destroy**. It reports that the failed security-policy object is absent remotely,
even though its address is still in local state. The five additions are:

1. `module.load_balancer.google_compute_security_policy.api` — blocked policy.
2. `module.load_balancer.google_compute_backend_service.api`.
3. `module.load_balancer.google_compute_url_map.https`.
4. `module.load_balancer.google_compute_target_https_proxy.main`.
5. `module.load_balancer.google_compute_global_forwarding_rule.https`.

After removing the policy resource and API backend's `security_policy`
attribute, formatting and validation passed. The refreshed plan confirms
**4 to add, 0 to change, 0 to destroy**: API backend, HTTPS URL map, HTTPS proxy,
and HTTPS forwarding rule. The user subsequently confirmed successful apply;
end-to-end application confirmation remains pending. Do not destroy the existing stack or manually remove state to retry
a partial apply.

### Deployment sequence and status

1. Completed in configuration: commented out only the Cloud Armor resource and
   API backend attachment in `infra/modules/load_balancer/main.tf`; updated the
   main README and existing troubleshooting files. TLS, routing, ingress,
   logs, and the static IP remain configured.
2. Formatting, validation, refreshed plan, and user-run apply completed. Do not
   reuse the saved plan from the failed apply.
3. Verify secret versions and the five GitHub Actions secrets, then complete
   DNS/TLS and CD deployment. The current workflow also contains an obsolete
   `API_LEGACY_HOST` assignment; plan to remove that old hostname reference.
   An infra-only push does not trigger CD under its current path filter.
4. Run migrations/seed through CD, execute ingestion, verify homepage/API data
   and email verification, and resume daily scheduling.
5. Preserve and verify the existing controls below. Do not introduce additional
   security services or application changes as part of this redeployment.

### Security decision under the GCP-only, minimal-change constraint

**Preserve the existing baseline during deployment.** Keep Cloud Run ingress
restricted to internal/load-balancer traffic, same-origin API routing, HTTPS,
secure session/CSRF cookies, CSRF checks, host validation, OTP expiry/attempt
limits, resend cooldowns, Secret Manager, and WIF. Read-only checks confirm
the security settings in code, but placeholder services do not yet run them.
Check deployed values and negative security cases after CD.

**Decision: no replacement security service for this deployment.** No
drop-in alternative was identified that reproduces Cloud Armor's edge request
filtering/per-client throttle on the existing external HTTPS load balancer and
Cloud Run path while meeting the user's constraints. Keep the request flow:
browser -> Google HTTPS load balancer -> Cloud Run frontend/API.

GCP options considered, not selected:

| Option | Why it is not the replacement for this deployment |
|---|---|
| VPC firewall rules | Do not filter requests at the public Google Front End/load balancer; not an HTTP WAF or auth-endpoint rate limiter |
| API Gateway | Supports API quotas, but introduces a gateway and API configuration changes; not a drop-in equivalent to the current per-client edge throttle |
| Google reCAPTCHA | GCP-native option for form/bot protection, requiring frontend and backend integration; not a general WAF or rate-limit replacement; do not add now |
| Memorystore/shared Redis | Could share app-level counters but adds a service/networking/cost and does not block requests before they reach the app; out of scope |
| IAM/IAP | Identity/access controls rather than a public-app WAF or throttle; do not put a Google sign-in requirement in front of the public dashboard |

Retain the existing Django auth rate limits and OTP controls as implemented.
Document their current limits accurately: Django's default local-memory counters
are isolated per worker/instance, and `_client_ip` trusts the first forwarded
address. They do not provide the same guarantees as edge throttling. Correcting
proxy trust can be proposed later as a small application hardening change, but
is not authorized by this planning request. Do not silently provision a shared
cache or replace the rate limiter.

Use existing GCP Logging/Monitoring and billing facilities for visibility.
Optional alert configuration for error rates, auth/OTP abuse, database pressure,
failed ingestion, and spending can be proposed separately. Keep secrets out of
logs. Review existing Cloud Run scaling/concurrency and database connection
limits without treating them as WAF controls or guaranteed spending caps.

Supported framework updates and narrower IAM remain normal maintenance items,
not prerequisites or architecture changes to bundle into this redeployment.
Cloud Armor can be reconsidered later if usable quota becomes available. Do
not upgrade billing, request quota, add services, or implement hardening without
a subsequent user instruction. Application controls and operational limits are
not equivalent to managed edge WAF/L7 abuse protection.

### CMD commands for inspection and eventual continuation

All commands below are Windows CMD. Inspection does not deploy anything:

```cmd
cd /d E:\Coding-practice\Projects\zeitgeist\infra
terraform workspace show
terraform state list
terraform plan
```

`state list` shows tracked addresses, not application health or a complete list
of things left to create. `plan` refreshes tracked resources and shows pending
changes; a placeholder reporting ready does not mean the real app is deployed.
For current live service images:

```cmd
gcloud run services list --region=us-central1 --project=zeitgeist-514220 --format="table(metadata.name,status.conditions[0].status,spec.template.spec.containers[0].image)"
gcloud sql instances list --project=zeitgeist-514220
gcloud compute forwarding-rules list --global --project=zeitgeist-514220
```

The configuration change is implemented. To review and continue:

```cmd
terraform fmt -check -recursive
terraform validate
terraform plan
terraform apply
```

The final command is for the user after reviewing the fresh plan. Cloud Armor
is no longer requested. The incident, configuration change, reasoning, and plan
results are recorded in `troubleshooting/terraform_cicd_issues.md` (T-15) and
`troubleshooting/README.md`. Update the deployment status there after the user
confirms apply and verification. Do not create a separate production log document.

### Primary references

- Cloud Armor quotas: https://docs.cloud.google.com/armor/quotas
- Django cache behavior: https://docs.djangoproject.com/en/5.1/topics/cache/
- Load balancer firewall scope: https://docs.cloud.google.com/load-balancing/docs/https#firewall_rules
- API Gateway quotas: https://docs.cloud.google.com/api-gateway/docs/quotas-overview
- Google reCAPTCHA website integration: https://docs.cloud.google.com/recaptcha/docs/setup-overview-web

## Scheduler cleanup — November 10, 2026

The user confirmed that the application is running, manual Cloud Run ingestion
populated the website, and daily scheduling has resumed. This supersedes the
older deployment-pending notes above.

Removed the redundant `google_cloud_scheduler_job.manual_ingest_trigger`
resource (`zeitgeist-manual-ingest`) from
`infra/modules/scheduler/main.tf`. It existed as a console convenience for
testing/re-runs, but direct Cloud Run execution already provides that behavior.
Its `0 0 28 2 *` schedule actually ran every February 28 at midnight UTC; the
old comment incorrectly claimed it fired only in leap years. Remove this
resource entirely rather than retaining a misleading manual-only schedule.

Keep `zeitgeist-daily-ingest` on `0 3 * * *` UTC. The actual Cloud Run job,
service account/IAM, and daily trigger are not removed. No replacement scheduler
or service is needed. For manual refreshes use Windows CMD:

```cmd
gcloud run jobs execute zeitgeist-ingest --region=us-central1 --project=zeitgeist-514220 --wait
```

Deletion from the cloud is pending the user's reviewed Terraform apply; removing
the resource from configuration lets Terraform plan its graceful deletion from
the existing state. Do not edit/remove state or delete the job out of band.
Do not use an untargeted `terraform destroy`: that destroys the whole stack.

```cmd
cd /d E:\Coding-practice\Projects\zeitgeist\infra
terraform fmt -check -recursive
terraform validate
terraform plan
terraform apply
```

Review the plan before the final command. The intended change is deletion of
only the redundant Scheduler job; investigate any unrelated changes rather
than applying them automatically. The assistant must not execute apply/destroy.

Validation passed: Terraform formatting and configuration checks succeeded.
The refreshed plan reports **0 to add, 0 to change, 1 to destroy**, naming only
`module.scheduler.google_cloud_scheduler_job.manual_ingest_trigger` for
deletion. No apply or destroy has been executed by the assistant.
