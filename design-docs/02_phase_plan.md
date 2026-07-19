# Zeitgeist - Phase and Delivery Plan

**Version:** 3.0
**Status:** Updated to match current Phase 2 implementation
**Last Updated:** 2026-07-14

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
- Graceful source failure logging.
- Django admin visibility into key models.
- Initial Next.js frontend.

Phase 1 implementation decisions:

- Django session auth was chosen for the current demo.
- Source additions were deferred unless access and response shape were verified.
- Source additions were gated by live API verification.

## 3. Phase 2 - Public Demo and Product Value

**Status:** In progress

Delivered so far:

- Public Next.js frontend on Cloud Run.
- Public Django API on Cloud Run.
- Category dashboard and `/category/[slug]` pages.
- Saved category preferences.
- Registration email OTP verification through SMTP.
- Forgot-password OTP flow through SMTP.
- App-level rate limiting on public auth endpoints.
- Gemini category summaries generated during ingestion.
- Production CORS/CSRF support for both observed Cloud Run frontend URL formats.
- Active verified sources:
  - Hacker News
  - DEV
  - New York Times Most Popular
  - RAWG
  - Football-Data

Remaining Phase 2 candidates:

- Improve dashboard/category page polish.
- Add enough snapshot history to support useful time-window UI.
- Add charts only after the data history makes them meaningful.
- Add monitoring around ingestion freshness and AI summary generation.
- Add another category/source only after live verification.

## 4. Phase 3 - Intelligence and Polish

Planned after the public demo is stable:

- Cross-platform topic detection.
- Sentiment labels.
- Weekly digest emails.
- First-login onboarding.
- Custom domain and launch monitoring.

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
| FR-07 time windows | Deferred |
| FR-08 charts | Deferred |
| FR-09 source filters | Implemented |
| FR-10 trending everywhere | Deferred |
| FR-11 scheduled ingestion | Implemented |
| FR-12 snapshots | Implemented |
| FR-13 graceful source failure | Implemented |
| FR-14 category AI summaries | Implemented |
| FR-15 topic embeddings | Deferred |
| FR-16 sentiment | Deferred |
| FR-18 weekly digest | Deferred |
| FR-19 admin ingestion visibility | Implemented |
| FR-20 DB-backed categories/source mappings | Implemented |

## 6. Near-Term Plan

1. Keep the repo clean by removing unused source placeholders and secret shells.
2. Review `terraform plan` after cleanup because unused Secret Manager resources
   are being removed from Terraform.
3. Push through CI/CD.
4. Run cloud ingestion and verify Tech, News, Gaming, Sports, AI summaries, OTP
   auth, and password reset in production.
5. Decide the next source/category only after a live fetch proves it is useful.
