# ── Cloud SQL (Postgres) ──────────────────────────────────────────────────────
# db-f1-micro + ENTERPRISE edition — cheapest available tier (~$7/month).
# GCP now defaults new instances to ENTERPRISE_PLUS which requires different
# tier names (db-perf-optimized-N-*) and costs ~$100+/month.
# Explicitly setting edition = "ENTERPRISE" keeps db-f1-micro available.
# Upgrade to ENTERPRISE edition with a larger tier before public launch.

resource "google_sql_database_instance" "main" {
  project             = var.project_id
  name                = "zeitgeist-pg"
  database_version    = "POSTGRES_16"
  region              = var.region
  deletion_protection = false    # Set true before public launch

  settings {
    tier              = "db-f1-micro"
    edition           = "ENTERPRISE"   # Must be set explicitly — GCP defaults to ENTERPRISE_PLUS
    availability_type = "ZONAL"        # Switch to REGIONAL before public launch

    backup_configuration {
      enabled    = true
      start_time = "04:00"             # Daily backup at 4am UTC (after ingestion)
    }

    ip_configuration {
      ipv4_enabled = true              # Public IP — accessed securely via Cloud SQL Auth Proxy
    }
  }

  # Cloud SQL takes 5-10 minutes to provision on a new project.
  # These timeouts prevent Terraform from giving up too early and causing
  # the "instance already exists" error on the next apply.
  timeouts {
    create = "20m"
    update = "20m"
    delete = "20m"
  }
}

resource "google_sql_database" "zeitgeist" {
  project  = var.project_id
  name     = var.db_name
  instance = google_sql_database_instance.main.name
}

resource "google_sql_user" "app" {
  project  = var.project_id
  name     = var.db_user
  instance = google_sql_database_instance.main.name
  password = var.db_password
}

output "connection_name" {
  value       = google_sql_database_instance.main.connection_name
  description = "Used by Cloud Run SQL Auth Proxy — format: project:region:instance"
}

output "instance_name" {
  value = google_sql_database_instance.main.name
}
