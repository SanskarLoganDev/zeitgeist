# ── Service Account ───────────────────────────────────────────────────────────
# Single SA used by both the API Cloud Run service and the ingestion Cloud Run Job.
# Principle of least privilege — only the roles it needs, nothing else.

locals {
  # On first apply, real images don't exist yet — use Google's public hello-world.
  # After first successful CD pipeline run, set use_placeholder_image = false
  # in terraform.tfvars and run terraform apply to lock in the real image reference.
  placeholder = "us-docker.pkg.dev/cloudrun/container/hello:latest"
  api_image   = var.use_placeholder_image ? local.placeholder : var.api_image
  job_image   = var.use_placeholder_image ? local.placeholder : var.job_image
}

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
  project             = var.project_id
  name                = "zeitgeist-api"
  location            = var.region
  deletion_protection = false    # Allow terraform destroy to work cleanly

  template {
    service_account = google_service_account.app.email

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    containers {
      # Uses placeholder on first apply, real image after CD pipeline runs
      image = local.api_image

      env {
        name  = "DJANGO_SETTINGS_MODULE"
        value = "config.settings.production"
      }

      dynamic "env" {
        for_each = {
          DJANGO_SECRET_KEY    = "django-secret-key"
          DB_PASSWORD          = "db-password"
          REDDIT_CLIENT_ID     = "reddit-client-id"
          REDDIT_CLIENT_SECRET = "reddit-client-secret"
          GOOGLE_CLIENT_ID     = "google-client-id"
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
  project             = var.project_id
  name                = "zeitgeist-ingest"
  location            = var.region
  deletion_protection = false    # Allow terraform destroy to work cleanly

  template {
    template {
      service_account = google_service_account.app.email

      containers {
        # Uses placeholder on first apply, real image after CD pipeline runs
        image = local.job_image

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
            memory = "1Gi"
          }
        }
      }

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [var.db_connection]
        }
      }

      max_retries = 2
      timeout     = "3600s"
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
