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
    # Wait 60 seconds for IAM to propagate before Cloud Run tries to read secrets.
    # Without this delay, Cloud Run is created in parallel with IAM grants and
    # hits "Permission denied on secret" because the secretAccessor role isn't live yet.
    command     = "powershell -Command Start-Sleep -Seconds 60"
    interpreter = ["cmd", "/C"]
  }
}

# ── API Cloud Run Service ─────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "api" {
  project             = var.project_id
  name                = "zeitgeist-api"
  location            = var.region
  deletion_protection = false    # Allow terraform destroy to work cleanly

  # Wait for ALL IAM roles to be fully propagated before creating Cloud Run.
  # Without this, Cloud Run is created in parallel with IAM and hits
  # "Permission denied on secret" because the secretAccessor role isn't live yet.
  depends_on = [null_resource.iam_propagation_delay]

  template {
    service_account = google_service_account.app.email

    scaling {
      # min_instance_count = 0 — scale to zero when idle, no cost when not in use.
      # During development this is critical — min=1 costs ~$1.40/day constantly.
      # Set to 1 only when actively testing or before public launch.
      # Switch back to 0 after each development session to save money.
      min_instance_count = 0
      max_instance_count = 10
    }

    containers {
      # Uses placeholder on first apply, real image after CD pipeline runs.
      # Controlled by use_placeholder_image in terraform.tfvars.
      image = local.api_image

      # Port 8000 — gunicorn binds to 0.0.0.0:8000 in the Dockerfile CMD.
      # Cloud Run defaults to 8080. Without this, the startup probe checks
      # port 8080, gets no response, and marks the container unhealthy.
      ports {
        container_port = 8000
      }

      env {
        name  = "DJANGO_SETTINGS_MODULE"
        value = "config.settings.production"
      }

      # Secrets injected from Secret Manager at container startup.
      # Never stored in environment variable plaintext — Cloud Run fetches
      # the value directly from Secret Manager using the service account.
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
        # Cloud SQL Auth Proxy socket path — Django connects via Unix socket,
        # not TCP. The proxy handles authentication using the service account.
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
        # Set to Cloud Run URL in terraform.tfvars after first apply.
        # Unknown before first apply — chicken-and-egg with Cloud Run URL.
        value = var.allowed_hosts
      }

      env {
        name  = "CORS_ALLOWED_ORIGINS"
        # Phase 1-2: localhost:3000 (Next.js dev server)
        # Phase 3: replace with production frontend domain
        value = var.cors_allowed_origins
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      # NOTE: No startup_probe defined here intentionally.
      # The placeholder image runs on port 8080 not 8000.
      # Adding a probe here would fail the placeholder on first apply.
      # Cloud Run uses the ports block above to know where to health check.
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

# Allow unauthenticated access to the API.
# JWT authentication is handled by Django itself, not Cloud Run.
# Without this, every request would need a Google identity token.
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Ingestion Cloud Run Job ───────────────────────────────────────────────────
# This is NOT a service — it doesn't run continuously.
# Cloud Scheduler triggers it once per day at 03:00 UTC.
# It starts, runs the ingestion pipeline, and exits.
resource "google_cloud_run_v2_job" "ingest" {
  project             = var.project_id
  name                = "zeitgeist-ingest"
  location            = var.region
  deletion_protection = false    # Allow terraform destroy to work cleanly

  # Same IAM propagation wait as the API service
  depends_on = [null_resource.iam_propagation_delay]

  template {
    template {
      service_account = google_service_account.app.email

      containers {
        # Uses placeholder on first apply, real job image after CD pipeline runs
        image = local.job_image

        # Secrets needed by the ingestion job at runtime
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
            memory = "1Gi"    # More memory than API — ingestion processes large datasets
          }
        }
      }

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [var.db_connection]
        }
      }

      max_retries = 2          # Retry up to 2 times on transient failures
      timeout     = "3600s"   # 1 hour max — ingestion should never take this long
    }
  }
}

output "api_url" {
  value       = google_cloud_run_v2_service.api.uri
  description = "Cloud Run service URL — use as ALLOWED_HOSTS in terraform.tfvars after first apply"
}

output "ingestion_job_name" {
  value       = google_cloud_run_v2_job.ingest.name
  description = "Cloud Run Job name — passed to the scheduler module"
}

output "service_account_email" {
  value       = google_service_account.app.email
  description = "Service account email — used in WIF binding and GitHub Actions secrets"
}
