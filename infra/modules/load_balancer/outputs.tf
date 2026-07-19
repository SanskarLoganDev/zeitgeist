output "ip_address" {
  value       = google_compute_global_address.main.address
  description = "Global static IP address for dailyzeitgeist.xyz DNS A record"
}

output "domain" {
  value       = var.domain
  description = "Primary custom domain served by the load balancer"
}

output "managed_ssl_certificate_name" {
  value       = google_compute_managed_ssl_certificate.main.name
  description = "Google-managed SSL certificate resource name"
}

output "https_url_map_name" {
  value       = google_compute_url_map.https.name
  description = "HTTPS URL map routing /api/* to the API and everything else to frontend"
}
