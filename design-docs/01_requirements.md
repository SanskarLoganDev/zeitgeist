# Zeitgeist - Requirements Document

**Version:** 3.0
**Status:** Updated to match current Phase 2 implementation
**Last Updated:** 2026-07-14

## 1. Project Overview

Zeitgeist is a personalized internet trend dashboard. It collects trends from
verified public APIs, normalizes them into a common model, stores daily
snapshots, and serves a category dashboard from Postgres. AI summaries are
generated during ingestion and stored for display.

## 2. Current Verified Sources

| Source | Category | Access | Trend/display signal | Status |
|---|---|---|---|---|
| Hacker News | Tech | No auth | Points | Implemented |
| DEV | Tech | No auth | Reactions + comments | Implemented |
| New York Times Most Popular | News | API key | Most viewed rank | Implemented |
| RAWG | Gaming | API key | Adds, ratings, release metadata | Implemented |
| Football-Data | Sports | API token | Recent match data and status | Implemented |

Source rule: a new source must be live API-verified before adding code, secrets,
seed rows, Terraform resources, or CD wiring.

## 3. Functional Requirements

### Authentication

| ID | Requirement | Status |
|---|---|---|
| FR-01 | Users can register and sign in with email/password using Django session authentication and CSRF protection. | Implemented |
| FR-01a | Users must verify registration email with a one-time code before completing the account flow. | Implemented |
| FR-01b | Users can reset a forgotten password using an emailed one-time code. | Implemented |
| FR-02 | Onboarding flow for first login category selection. | Deferred |
| FR-03 | Users can save category preferences from the dashboard. | Implemented |

### Dashboard and Display

| ID | Requirement | Status |
|---|---|---|
| FR-04 | Dashboard shows stored top trends grouped by active category and source. | Implemented |
| FR-05 | `/category/[slug]` shows a paginated category detail view. | Implemented |
| FR-06 | Trend cards show title, source, score/status, and relevant links/metadata. | Implemented |
| FR-07 | Time-window filters for today/7d/30d/90d. | Deferred until enough snapshot history exists |
| FR-08 | Category trend charts. | Deferred |
| FR-09 | Category source filters operate on stored data only. | Implemented |
| FR-10 | Cross-platform "trending everywhere" cards. | Deferred |

### Ingestion

| ID | Requirement | Status |
|---|---|---|
| FR-11 | Cloud Scheduler triggers ingestion daily. | Implemented |
| FR-12 | Each source writes timestamped snapshots and trend items. | Implemented |
| FR-13 | Source failures are logged and do not block other sources. | Implemented |
| FR-14 | Gemini generates one category summary per ingestion batch, stored in Postgres. | Implemented |

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
| NFR-06 | Production CORS and CSRF trusted origins must include the Cloud Run frontend URLs used by browsers. |

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
| Sports | Football-Data recent matches, currently displayed by recency rather than a synthetic trend score. |

## 7. Removed Requirement

| ID | Requirement | Reason |
|---|---|---|
| FR-17 | Keyword topic alerts | Descoped because it overlaps with digest/email features and adds background matching complexity. |
