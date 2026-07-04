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
    "django-secret-key"    = "Django SECRET_KEY"
    "db-password"          = "Cloud SQL postgres user password"
    "google-client-id"     = "Google OAuth client ID (user login)"
    "google-client-secret" = "Google OAuth client secret (user login)"

    # ── Phase 2 ──────────────────────────────────────────────────────────────
    "youtube-api-key" = "YouTube Data API v3 key"
    "tmdb-api-key"    = "TMDB API key"
    "nasa-api-key"    = "NASA Open APIs key"
    "pubmed-api-key"  = "NCBI E-utilities API key"

    # ── Phase 3 ──────────────────────────────────────────────────────────────
    "sendgrid-api-key" = "SendGrid email delivery API key"
  }
}

resource "google_secret_manager_secret" "secrets" {
  for_each            = local.secrets
  project             = var.project_id
  secret_id           = each.key
  deletion_protection = false    # Allow terraform destroy even after values are set

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
