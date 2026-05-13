resource "google_artifact_registry_repository" "zeitgeist" {
  project       = var.project_id
  location      = var.region
  repository_id = "zeitgeist"
  description   = "Docker images for Zeitgeist API and ingestion job"
  format        = "DOCKER"
}

output "registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/zeitgeist"
}
