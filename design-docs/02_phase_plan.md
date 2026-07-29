# Zeitgeist - Phase and Delivery Plan

**Version:** 3.1
**Status:** Updated to match completed public demo implementation
**Last Updated:** 2026-07-29

## 1. Delivery Philosophy

Each phase must end with a working deployable slice. Avoid speculative source
setup. New source integrations require live API verification before code,
secrets, Terraform, or CD wiring.

## 2. Phase 1 - Foundation

**Status:** Complete

Delivered:

- Django project with apps for accounts, categories, trends, ingestion, and AI.
- Cloud SQL Postgres.
- Cloud Run API and Cloud Run ingestion job.
- Cloud Scheduler daily ingestion trigger.
- Secret Manager containers.
- Artifact Registry.
- GitHub Actions CI/CD with Workload Identity Federation.
- Dashboard API and category detail API.
- Stored snapshots and trend items.
- Graceful source failure logging and freshness status.
- Django admin visibility into key models.
- Initial Next.js frontend.

Phase 1 implementation decisions:

- Django session auth was chosen for the browser app.
- Source additions were deferred unless access and response shape were verified.
- Source additions were gated by live API verification.

## 3. Phase 2 - Public Demo and Product Value

**Status:** Complete

Delivered:

- Public Next.js frontend on Cloud Run.
- Public Django API on Cloud Run.
- Production domain `https://dailyzeitgeist.xyz`.
- External HTTPS load balancer with managed SSL certificate.
- HTTP to HTTPS redirect.
- Same-origin browser API calls under `/api/v1`.
- Server-side frontend API base set to `https://dailyzeitgeist.xyz/api/v1`.
- Cloud Run frontend and API ingress restricted to internal and load-balancer traffic.
- Cloud Armor attached to the API backend service for auth endpoint throttling.
- Category dashboard and `/category/[slug]` pages.
- Saved category preferences.
- Registration email OTP verification through SMTP.
- Forgot-password OTP flow through SMTP.
- App-level rate limiting on public auth endpoints.
- Gemini category summaries generated during ingestion.
- Source-specific Sports summaries for cricket and football.
- Production CORS/CSRF support for same-origin custom-domain deployment.
- Active verified sources:
  - Hacker News
  - DEV
  - New York Times Most Popular
  - RAWG
  - Football-Data
  - Cricket Data

## 4. Deferred Phase 3 Candidates

These are intentionally deferred until there is a stronger product reason or
enough historical data:

- First-login onboarding.
- Time-window filters for today/7d/30d/90d.
- Category trend charts.
- Cross-platform topic detection.
- Sentiment labels.
- Weekly digest emails.
- Monitoring around ingestion freshness and AI summary generation.
- Additional source/category integrations after live verification.

Delivery provider for future weekly email is not decided. SMTP is currently used
only for account verification and password reset.

## 5. Requirements Traceability

| ID | Status |
|---|---|
| FR-01 email/password session auth | Implemented |
| FR-01a registration OTP | Implemented |
| FR-01b forgot-password OTP | Implemented |
| FR-01c auth endpoint rate limiting | Implemented |
| FR-02 onboarding | Deferred |
| FR-03 saved preferences | Implemented |
| FR-04 dashboard | Implemented |
| FR-05 category detail | Implemented |
| FR-06 trend cards | Implemented |
| FR-06a sports match-first cards | Implemented |
| FR-07 time windows | Deferred |
| FR-08 charts | Deferred |
| FR-09 source filters | Implemented |
| FR-09a Sports page without mixed "All" source | Implemented |
| FR-10 trending everywhere | Deferred |
| FR-11 scheduled ingestion | Implemented |
| FR-12 snapshots | Implemented |
| FR-13 graceful source failure | Implemented |
| FR-14 category AI summaries | Implemented |
| FR-14a Sports source-specific AI summaries | Implemented |
| FR-15 Cricket Data current/recent match ingestion | Implemented |
| FR-16 production HTTPS load balancer and security routing | Implemented |
| FR-19 admin ingestion visibility | Implemented |
| FR-20 DB-backed categories/source mappings | Implemented |

## 6. Final Archive Checklist

Before taking down the demo environment:

1. Commit source, infrastructure, design docs, README, and troubleshooting notes.
2. Verify no real secrets, `.env` files, Terraform state, Terraform variable
   values, or local secret scripts are staged.
3. Disable or avoid triggering CD after teardown.
4. Run `terraform destroy` from `infra` only after confirming Cloud SQL data can
   be deleted.
5. Verify Cloud Run, Cloud SQL, Scheduler, Artifact Registry, Secret Manager,
   Load Balancer, and Cloud Armor resources are removed or no longer billable.
