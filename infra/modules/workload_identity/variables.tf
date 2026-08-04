variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "pool_id" {
  description = "Workload Identity Pool ID used by GitHub Actions."
  type        = string
}

variable "provider_id" {
  description = "Workload Identity Provider ID used by GitHub Actions."
  type        = string
}

variable "repository" {
  description = "GitHub repository allowed to authenticate, in owner/repo format."
  type        = string
}
