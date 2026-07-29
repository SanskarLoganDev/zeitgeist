# Zeitgeist Workflow Reference

This file explains the main runtime flows in plain English.

## Scheduled Ingestion Flow

Cloud Scheduler does not call source APIs directly. It only triggers the Cloud
Run ingestion job.

```text
Cloud Scheduler
  -> Cloud Run Job: zeitgeist-ingest
  -> backend/run_job.py
  -> apps/ingestion/orchestrator.py
  -> source adapter
  -> external API
  -> normalized trend items
  -> Cloud SQL Postgres
  -> Django API endpoints
  -> Next.js dashboard
```

Current active source adapters:

```text
hackernews      -> Hacker News
devto           -> DEV
nytimes         -> New York Times Most Popular
rawg            -> RAWG
football_data   -> Football-Data
cricket_data    -> Cricket Data
```

## Adapter And Orchestrator Roles

The orchestrator is the coordinator. It asks the database:

```text
Which categories are active?
Which sources are enabled for each category?
Which adapter handles each source?
```

Each adapter is source-specific. It knows how to call one external API, handle
that API's authentication, parse that API's response shape, and convert the
result into Zeitgeist's internal trend item format.

Example normalized item shape:

```json
{
  "rank": 1,
  "title": "Example story or match",
  "url": "https://example.com",
  "external_url": "https://example.com/original",
  "score": 123,
  "score_label": "points",
  "metadata": {
    "source_specific": "values live here"
  }
}
```

The orchestrator saves adapter output into:

```text
IngestionRun   -> audit log for source status, timestamps, errors, item counts
TrendSnapshot  -> one stored batch for a category/source
TrendItem      -> individual stories, articles, games, or matches in a snapshot
CategoryAISummary -> stored Gemini summary text generated during ingestion
```

## User Request Flow

When a user opens the frontend, the frontend does not call Hacker News, DEV,
NYT, RAWG, Football-Data, Cricket Data, or Gemini.

The frontend calls the Django API:

```text
GET /api/v1/dashboard/
GET /api/v1/categories/
GET /api/v1/categories/{slug}/trends/
```

The Django trends API reads stored rows from Postgres:

```text
Category
CategorySourceConfig
IngestionRun
TrendSnapshot
TrendItem
CategoryAISummary
```

This separation is deliberate:

- External API failures are isolated to the ingestion job.
- The dashboard can keep serving the last successful snapshot.
- Old data can be marked `stale`.
- Gemini latency and cost never affect live page requests.

## Production HTTP Flow

```text
Browser
  -> https://dailyzeitgeist.xyz
  -> HTTPS Load Balancer
      -> /api/* -> Cloud Armor -> Cloud Run API
      -> all other paths -> Cloud Run Frontend
```

Browser API calls use:

```text
/api/v1
```

Server-side frontend calls use:

```text
https://dailyzeitgeist.xyz/api/v1
```

Both paths go through the custom domain and load balancer. The frontend does not
call the API by a raw internal Cloud Run URL.

## Deployment Flow

```text
GitHub Actions
  -> authenticate to GCP with Workload Identity Federation
  -> build API image
  -> build ingestion job image
  -> build frontend image
  -> push images to Artifact Registry
  -> run migrations with Cloud Run DB maintenance job
  -> run seed_categories with Cloud Run DB maintenance job
  -> deploy frontend service
  -> deploy API service
  -> update ingestion job image
  -> smoke test dailyzeitgeist.xyz
```

## Database Maintenance Flow

The database maintenance job is a Cloud Run Job that reuses the backend API
image. It is not a public service.

It currently runs:

```text
python manage.py migrate --noinput
python manage.py seed_categories
```

`migrate` updates the database schema. `seed_categories` creates or updates the
required starter category/source rows.
