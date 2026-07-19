# ── Service Account ───────────────────────────────────────────────────────────
# Single SA used by both the API Cloud Run service and the ingestion Cloud Run Job.
# Principle of least privilege — only the roles it needs, nothing else.

locals {
  # On first apply, real images don't exist yet — use Google's public hello-world.
  # CD owns the live image and secret env vars after bootstrap, so Terraform
  # ignores those fields below instead of rolling them back on later applies.
  placeholder    = "us-docker.pkg.dev/cloudrun/container/hello:latest"
  api_image      = var.use_placeholder_image ? local.placeholder : var.api_image
  frontend_image = var.use_placeholder_image ? local.placeholder : var.frontend_image
  job_image      = var.use_placeholder_image ? local.placeholder : var.job_image
}

data "google_project" "current" {
  project_id = var.project_id
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

# Allow GitHub Actions identities from this repository to impersonate the deploy
# service account through Workload Identity Federation. Without this binding,
# google-github-actions/auth can exchange the OIDC token but cannot mint an
# access token for Docker pushes or gcloud commands.
resource "google_service_account_iam_member" "github_wif_user" {
  service_account_id = google_service_account.app.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/projects/${data.google_project.current.number}/locations/global/workloadIdentityPools/${var.wif_pool_id}/attribute.repository/${var.github_repository}"
}

# ── IAM propagation delay ─────────────────────────────────────────────────────
# GCP IAM changes are eventually consistent. Wait 60s before returning from
# terraform apply so the first CD run is less likely to hit IAM propagation
# errors when it pushes images, attaches secrets, or creates migration jobs.
resource "null_resource" "iam_propagation_delay" {
  triggers = {
    secret_accessor          = google_project_iam_member.secret_accessor.id
    cloudsql_client          = google_project_iam_member.cloudsql_client.id
    log_writer               = google_project_iam_member.log_writer.id
    vertex_user              = google_project_iam_member.vertex_user.id
    artifact_registry_writer = google_project_iam_member.artifact_registry_writer.id
    cloud_run_admin          = google_project_iam_member.cloud_run_admin.id
    self_act_as              = google_service_account_iam_member.self_act_as.id
    github_wif_user          = google_service_account_iam_member.github_wif_user.id
  }

  provisioner "local-exec" {
    # Wait 60 seconds for IAM to propagate before the first CD deployment.
    command     = "powershell -Command Start-Sleep -Seconds 60"
    interpreter = ["cmd", "/C"]
  }
}

# ── API Cloud Run Service ─────────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "api" {
  project             = var.project_id
  name                = "zeitgeist-api"
  location            = var.region
  deletion_protection = false # Allow terraform destroy to work cleanly

  # Wait for IAM roles to be fully propagated before the first CD deployment.
  depends_on = [null_resource.iam_propagation_delay]

  lifecycle {
    # GitHub Actions CD deploys the real image and attaches secret env vars.
    # Terraform keeps owning infrastructure shape while leaving runtime
    # deployment fields alone, which prevents rollback to placeholder config.
    ignore_changes = [
      client,
      client_version,
      scaling,
      template[0].containers[0].image,
      template[0].containers[0].env,
    ]
  }

  template {
    service_account = google_service_account.app.email

    scaling {
      # min_instance_count = 0 — scale to zero when idle, no cost when not in use.
      # During development this is critical — min=1 costs ~$1.40/day constantly.
      # Set to 1 only when actively testing or before public launch.
      # Switch back to 0 after each development session to save money.
      min_instance_count = 1
      max_instance_count = 10
    }

    containers {
      # Bootstrap image only. CD replaces this with the real app image.
      image = local.api_image

      # Port 8000 — gunicorn binds to 0.0.0.0:8000 in the Dockerfile CMD.
      # Cloud Run defaults to 8080. Without this, the startup probe checks
      # port 8080, gets no response, and marks the container unhealthy.
      ports {
        container_port = 8000
      }

      # Mount the Cloud SQL Auth Proxy socket volume so DB_HOST=/cloudsql/...
      # resolves inside the Django container.
      volume_mounts {
        name       = "cloudsql"
        mount_path = "/cloudsql"
      }

      env {
        name  = "DJANGO_SETTINGS_MODULE"
        value = "config.settings.production"
      }

      # Secret env vars are intentionally NOT attached by Terraform.
      # Terraform creates Secret Manager shells only; values are added by
      # infra/secrets.bat after the first apply. The CD pipeline then attaches
      # the populated secrets to the real Django revision with --set-secrets.
      # This avoids both plaintext secrets in terraform.tfstate and the
      # chicken-and-egg failure where Cloud Run validates :latest before any
      # secret versions exist.

      env {
        name = "DB_HOST"
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
        name = "ALLOWED_HOSTS"
        # Set to the Cloud Run hostname in terraform.tfvars after first apply.
        # Unknown before first apply because the service URL is generated by GCP.
        value = var.allowed_hosts
      }

      env {
        name = "CORS_ALLOWED_ORIGINS"
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
# Browser authentication is handled by Django itself, not Cloud Run.
# Without this, every request would need a Google identity token.
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Frontend Cloud Run Service ────────────────────────────────────────────────
resource "google_cloud_run_v2_service" "frontend" {
  project             = var.project_id
  name                = "zeitgeist-frontend"
  location            = var.region
  deletion_protection = false # Allow terraform destroy to work cleanly

  depends_on = [null_resource.iam_propagation_delay]

  lifecycle {
    # CD deploys the real Next.js image and runtime API URL. Terraform owns the
    # stable service shape and warm instance setting.
    ignore_changes = [
      client,
      client_version,
      template[0].containers[0].image,
      template[0].containers[0].env,
      template[0].containers[0].ports,
      template[0].containers[0].startup_probe,
    ]
  }

  scaling {
    min_instance_count = 1
  }

  template {
    service_account = google_service_account.app.email

    scaling {
      # Keep one warm frontend instance to avoid first-visit Cloud Run cold starts.
      min_instance_count = 1
      max_instance_count = 12
    }

    containers {
      # Bootstrap image only. CD replaces this with the real Next.js image.
      image = local.frontend_image

      # The placeholder listens on 8080. CD deploys the real frontend on 3000.
      # Port drift is ignored above so Terraform does not undo CD's runtime port.
      ports {
        container_port = 8080
      }

      resources {
        cpu_idle          = true
        startup_cpu_boost = true

        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.frontend.name
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
  deletion_protection = false # Allow terraform destroy to work cleanly

  # Same IAM propagation wait as the API service
  depends_on = [null_resource.iam_propagation_delay]

  lifecycle {
    # GitHub Actions CD deploys the real job image and attaches secret env vars.
    ignore_changes = [
      client,
      client_version,
      template[0].template[0].containers[0].image,
      template[0].template[0].containers[0].env,
    ]
  }

  template {
    template {
      service_account = google_service_account.app.email

      containers {
        # Bootstrap image only. CD replaces this with the real ingestion image.
        image = local.job_image

        # Mount the Cloud SQL Auth Proxy socket volume so DB_HOST=/cloudsql/...
        # resolves inside the ingestion container.
        volume_mounts {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }

        # Secret env vars are intentionally NOT attached by Terraform.
        # The CD pipeline attaches populated Secret Manager versions when it
        # updates this job to the real ingestion image.

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
            memory = "1Gi" # More memory than API — ingestion processes large datasets
          }
        }
      }

      volumes {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [var.db_connection]
        }
      }

      max_retries = 2       # Retry up to 2 times on transient failures
      timeout     = "3600s" # 1 hour max — ingestion should never take this long
    }
  }
}

output "api_url" {
  value       = google_cloud_run_v2_service.api.uri
  description = "Cloud Run service URL — use as ALLOWED_HOSTS in terraform.tfvars after first apply"
}

output "frontend_url" {
  value       = google_cloud_run_v2_service.frontend.uri
  description = "Cloud Run frontend service URL"
}

output "api_service_name" {
  value       = google_cloud_run_v2_service.api.name
  description = "Cloud Run API service name — used by the load balancer serverless NEG"
}

output "frontend_service_name" {
  value       = google_cloud_run_v2_service.frontend.name
  description = "Cloud Run frontend service name — used by the load balancer serverless NEG"
}

output "ingestion_job_name" {
  value       = google_cloud_run_v2_job.ingest.name
  description = "Cloud Run Job name — passed to the scheduler module"
}

output "service_account_email" {
  value       = google_service_account.app.email
  description = "Service account email — used in WIF binding and GitHub Actions secrets"
}
