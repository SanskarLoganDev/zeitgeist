# ── Service Account ───────────────────────────────────────────────────────────
locals {
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

# ── Runtime roles — needed by the running application ─────────────────────────

# Read secrets from Secret Manager at container startup
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

# ── CD pipeline roles — needed by GitHub Actions deployment steps ──────────────

# Push Docker images to Artifact Registry
# Required by: cd.yml steps "Push API image" and "Push ingestion job image"
resource "google_project_iam_member" "artifact_registry_writer" {
  project = var.project_id
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# Full Cloud Run admin — covers create/update/delete services and jobs,
# execute jobs, describe services (smoke test), and all related operations.
# run.developer was insufficient for gcloud run jobs create --execute-now.
# Required by: all gcloud run * commands in cd.yml
resource "google_project_iam_member" "cloud_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.app.email}"
}

# Allow the service account to act as itself when creating Cloud Run Jobs/Services.
# GCP requires iam.serviceaccounts.actAs on the target SA when creating a resource
# that runs as that SA — even when caller IS that SA.
# Required by: cd.yml "Run database migrations" step (gcloud run jobs create --service-account)
resource "google_service_account_iam_member" "self_act_as" {
  service_account_id = google_service_account.app.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.app.email}"
}

# ── IAM propagation delay ─────────────────────────────────────────────────────
# GCP IAM changes are eventually consistent — wait 60s before Cloud Run
# tries to read secrets, otherwise it hits "Permission denied on secret".
resource "null_resource" "iam_propagation_delay" {
  triggers = {
    secret_accessor          = google_project_iam_member.secret_accessor.id
    cloudsql_client          = google_project_iam_member.cloudsql_client.id
    log_writer               = google_project_iam_member.log_writer.id
    vertex_user              = google_project_iam_member.vertex_user.id
    artifact_registry_writer = google_project_iam_member.artifact_registry_writer.id
    cloud_run_admin          = google_project_iam_member.cloud_run_admin.id
    self_act_as              = google_service_account_iam_member.self_act_as.id
  }

  provisioner "local-exec" {
    command     = "powershell -Command Start-Sleep -Seconds 60"
    interpreter = ["cmd", "/C"]
  }
}

# ── API Cloud Run Service ─────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "api" {
  project             = var.project_id
  name                = "zeitgeist-api"
  location            = var.region
  deletion_protection = false
  depends_on          = [null_resource.iam_propagation_delay]

  template {
    service_account = google_service_account.app.email

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    containers {
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

      # No startup_probe here — placeholder image runs on port 8080 not 8000.
      # Real health check is enforced by Cloud Run's default container liveness
      # once the real Django image is deployed by the CD pipeline.
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

# Allow unauthenticated access — JWT auth handled by Django, not Cloud Run
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
  deletion_protection = false
  depends_on          = [null_resource.iam_propagation_delay]

  template {
    template {
      service_account = google_service_account.app.email

      containers {
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
