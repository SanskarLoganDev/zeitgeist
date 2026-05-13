# ── Cloud Scheduler ───────────────────────────────────────────────────────────
# Job 1: Daily ingestion trigger — 03:00 UTC every day
# Job 2: Weekly digest email trigger — 08:00 UTC every Monday (Phase 3)

resource "google_cloud_scheduler_job" "daily_ingest" {
  project     = var.project_id
  name        = "zeitgeist-daily-ingest"
  description = "Triggers the Zeitgeist ingestion Cloud Run Job at 03:00 UTC daily"
  schedule    = "0 3 * * *"
  time_zone   = "UTC"
  region      = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${var.job_name}:run"

    oauth_token {
      service_account_email = var.service_account
    }
  }

  retry_config {
    retry_count          = 1
    max_retry_duration   = "0s"
    min_backoff_duration = "5s"
    max_backoff_duration = "3600s"
    max_doublings        = 5
  }
}

# Manual trigger job — same job, can be fired on demand for testing
resource "google_cloud_scheduler_job" "manual_ingest_trigger" {
  project     = var.project_id
  name        = "zeitgeist-manual-ingest"
  description = "Manual trigger for ingestion job — use for testing and re-runs"
  schedule    = "0 0 31 2 *"    # Never fires automatically (Feb 31 doesn't exist)
  time_zone   = "UTC"
  region      = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${var.job_name}:run"

    oauth_token {
      service_account_email = var.service_account
    }
  }
}

# ── Phase 3: Weekly digest email trigger ─────────────────────────────────────
# Uncomment when FR-18 is implemented
#
# resource "google_cloud_scheduler_job" "weekly_digest" {
#   project     = var.project_id
#   name        = "zeitgeist-weekly-digest"
#   description = "Triggers weekly personalised digest email every Monday 08:00 UTC"
#   schedule    = "0 8 * * 1"
#   time_zone   = "UTC"
#   region      = var.region
#
#   http_target {
#     http_method = "POST"
#     uri         = "${var.api_url}/api/v1/internal/digest/trigger/"
#     oauth_token {
#       service_account_email = var.service_account
#     }
#   }
# }
