resource "google_artifact_registry_repository" "zeitgeist" {
  project       = var.project_id
  location      = var.region
  repository_id = "zeitgeist"
  description   = "Docker images for Zeitgeist API and ingestion job"
  format        = "DOCKER"
  # No special destroy settings needed — Artifact Registry deletes cleanly
  # even with images present when terraform destroy is run.
}

output "registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/zeitgeist"
}
