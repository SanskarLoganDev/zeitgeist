output "api_url" {
  description = "Cloud Run API service URL — set this as ALLOWED_HOSTS in production"
  value       = module.cloud_run.api_url
}

output "artifact_registry_url" {
  description = "Docker registry URL — used in GitHub Actions push step"
  value       = module.artifact_registry.registry_url
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL connection name — used by Cloud Run SQL proxy"
  value       = module.cloud_sql.connection_name
}
