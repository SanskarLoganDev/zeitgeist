# ── Cloud SQL (Postgres) ──────────────────────────────────────────────────────
# db-f1-micro during development — cheapest tier (~$7/month).
# Single instance, no HA. Upgrade to db-g1-small before public launch.

resource "google_sql_database_instance" "main" {
  project          = var.project_id
  name             = "zeitgeist-pg"
  database_version = "POSTGRES_16"
  region           = var.region

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"    # Switch to REGIONAL before public launch

    backup_configuration {
      enabled    = true
      start_time = "04:00"         # Daily backup at 4am UTC (after ingestion)
    }

    ip_configuration {
      ipv4_enabled = false         # No public IP — accessed via Cloud SQL Auth Proxy
      private_network = var.vpc_network
    }

    deletion_protection = false    # Set true before public launch (terraform.tfvars)
  }

  # Prevent accidental destruction in production
  lifecycle {
    prevent_destroy = false        # Flip to true after first real data
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
  # Password is stored in Secret Manager, not here.
  # Set via: gcloud sql users set-password zeitgeist --instance=zeitgeist-pg --prompt-for-password
  password = var.db_password
}

output "connection_name" {
  value       = google_sql_database_instance.main.connection_name
  description = "Used by Cloud Run SQL Auth Proxy sidecar"
}

output "instance_name" {
  value = google_sql_database_instance.main.name
}
