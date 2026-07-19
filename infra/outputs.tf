output "api_url" {
  description = "Cloud Run API service URL — set this as ALLOWED_HOSTS in production"
  value       = module.cloud_run.api_url
}

output "frontend_url" {
  description = "Cloud Run frontend service URL"
  value       = module.cloud_run.frontend_url
}

output "artifact_registry_url" {
  description = "Docker registry URL — used in GitHub Actions push step"
  value       = module.artifact_registry.registry_url
}

output "cloud_sql_connection_name" {
  description = "Cloud SQL connection name — used by Cloud Run SQL proxy"
  value       = module.cloud_sql.connection_name
}

output "load_balancer_ip" {
  description = "Global static IP for the dailyzeitgeist.xyz DNS A record"
  value       = module.load_balancer.ip_address
}

output "load_balancer_domain" {
  description = "Primary production domain served by the load balancer"
  value       = module.load_balancer.domain
}

output "managed_ssl_certificate_name" {
  description = "Google-managed SSL certificate resource name"
  value       = module.load_balancer.managed_ssl_certificate_name
}
