# ── Service Account ───────────────────────────────────────────────────────────
# Single SA used by both the API Cloud Run service and the ingestion Cloud Run Job.
# Principle of least privilege — only the roles it needs, nothing else.

resource "google_service_account" "app" {
  project      = var.project_id
  account_id   = "zeitgeist-app"
  display_name = "Zeitgeist App Service Account"
  description  = "Used by Cloud Run API and ingestion job"
}

# Read secrets from Secret Manager
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# Connect to Cloud SQL via Auth Proxy
resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# Write structured logs to Cloud Logging
resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# Phase 2: Call Vertex AI (Gemini + Embeddings)
resource "google_project_iam_member" "vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# ── API Cloud Run Service ─────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "api" {
  project  = var.project_id
  name     = "zeitgeist-api"
  location = var.region

  template {
    service_account = google_service_account.app.email

    scaling {
      min_instance_count = 1    # Keep 1 warm to avoid cold starts on dashboard load
      max_instance_count = 10
    }

    containers {
      image = var.api_image

      env {
        name  = "DJANGO_SETTINGS_MODULE"
        value = "config.settings.production"
      }

      # Secrets injected as env vars from Secret Manager
      dynamic "env" {
        for_each = {
          DJANGO_SECRET_KEY   = "django-secret-key"
          DB_PASSWORD         = "db-password"
          REDDIT_CLIENT_ID    = "reddit-client-id"
          REDDIT_CLIENT_SECRET = "reddit-client-secret"
          GOOGLE_CLIENT_ID    = "google-client-id"
          GOOGLE_CLIENT_SECRET = "google-client-secret"
        }
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value
              version = "latest"
            }
          }
        }
      }

      env {
        name  = "DB_HOST"
        value = "/cloudsql/${var.db_connection}"
      }

      env {
        name  = "DB_NAME"
        value = "zeitgeist"
      }

      env {
        name  = "DB_USER"
        value = "zeitgeist"
      }

      env {
        name  = "ALLOWED_HOSTS"
        value = var.allowed_hosts
      }

      env {
        name  = "CORS_ALLOWED_ORIGINS"
        value = var.cors_allowed_origins
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      # Cloud SQL Auth Proxy — connects Django to Cloud SQL without public IP
      startup_probe {
        http_get {
          path = "/api/v1/health/"
          port = 8000
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 3
      }
    }

    volumes {
      name = "cloudsql"
      cloud_sql_instance {
        instances = [var.db_connection]
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Allow unauthenticated access (JWT auth handled by Django, not Cloud Run)
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Ingestion Cloud Run Job ───────────────────────────────────────────────────
resource "google_cloud_run_v2_job" "ingest" {
  project  = var.project_id
  name     = "zeitgeist-ingest"
  location = var.region

  template {
    template {
      service_account = google_service_account.app.email

      containers {
        image = var.job_image

        # Same secret env vars as the API — ingestion needs DB + source API keys
        dynamic "env" {
          for_each = {
            DJANGO_SECRET_KEY    = "django-secret-key"
            DB_PASSWORD          = "db-password"
            REDDIT_CLIENT_ID     = "reddit-client-id"
            REDDIT_CLIENT_SECRET = "reddit-client-secret"
          }
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value
                version = "latest"
              }
            }
          }
        }

        env {
          name  = "DB_HOST"
          value = "/cloudsql/${var.db_connection}"
        }

        env {
          name  = "DB_NAME"
          value = "zeitgeist"
        }

        env {
          name  = "DB_USER"
          value = "zeitgeist"
        }

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"    # More memory for ingestion — processes many API responses
          }
        }
      }

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [var.db_connection]
        }
      }

      max_retries = 2    # Retry failed job up to 2 times before giving up
      timeout     = "3600s"    # 1 hour max — ingestion should finish in ~10 min
    }
  }
}

output "api_url" {
  value = google_cloud_run_v2_service.api.uri
}

output "ingestion_job_name" {
  value = google_cloud_run_v2_job.ingest.name
}

output "service_account_email" {
  value = google_service_account.app.email
}
