output "pool_id" {
  description = "Workload Identity Pool ID."
  value       = google_iam_workload_identity_pool.github.workload_identity_pool_id
}

output "pool_name" {
  description = "Full Workload Identity Pool resource name."
  value       = google_iam_workload_identity_pool.github.name
}

output "provider_name" {
  description = "Full Workload Identity Provider resource name for GitHub Actions."
  value       = google_iam_workload_identity_pool_provider.github.name
}
