# ── Secret Manager ────────────────────────────────────────────────────────────
# Creates secret resources only — NOT secret versions (values).
# Secret values are set manually via gcloud after infra is provisioned.
# This prevents secrets from ever appearing in Terraform state.
#
# To set a secret value after apply:
#   echo -n "your-value" | gcloud secrets versions add <secret-name> --data-file=- --project PROJECT_ID
#
# deletion_protection = false allows terraform destroy to delete these secrets
# even after values have been added via gcloud.

locals {
  secrets = {
    # ── Phase 1 ──────────────────────────────────────────────────────────────
    "django-secret-key" = "Django SECRET_KEY"
    "db-password"       = "Cloud SQL postgres user password"

    # ── Verified source API keys ────────────────────────────────────────────
    "nytimes-api-key"       = "New York Times Most Popular API key"
    "rawg-api-key"          = "RAWG video games API key"
    "football-data-api-key" = "Football-Data API token"

    # ── SMTP email delivery ─────────────────────────────────────────────────
    "smtp-host"          = "SMTP server hostname for verification emails"
    "smtp-host-user"     = "SMTP account username for verification emails"
    "smtp-host-password" = "SMTP account password or app password for verification emails"
  }
}

resource "google_secret_manager_secret" "secrets" {
  for_each            = local.secrets
  project             = var.project_id
  secret_id           = each.key
  deletion_protection = false # Allow terraform destroy even after values are set

  replication {
    auto {}
  }

  labels = {
    managed-by = "terraform"
    app        = "zeitgeist"
  }
}

output "secret_ids" {
  value       = { for k, v in google_secret_manager_secret.secrets : k => v.id }
  description = "Map of secret name → full Secret Manager resource ID"
}
