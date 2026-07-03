variable "gcp_project_id" {
  description = "GCP project ID — e.g. zeitgeist-499322"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for all resources"
  type        = string
  default     = "us-central1"
}

variable "db_name" {
  description = "Postgres database name"
  type        = string
  default     = "zeitgeist"
}

variable "db_user" {
  description = "Postgres database user"
  type        = string
  default     = "zeitgeist"
}

variable "db_password" {
  description = "Postgres database password — set in terraform.tfvars, never hardcode"
  type        = string
  sensitive   = true
}

variable "use_placeholder_image" {
  description = "Use placeholder image for initial apply before real images are built by CD pipeline"
  type        = bool
  default     = true
}

variable "allowed_hosts" {
  description = "Comma-separated list of allowed hosts for Django ALLOWED_HOSTS setting. Unknown before first apply — update terraform.tfvars after first apply with the Cloud Run URL."
  type        = string
  default     = "localhost"
}

variable "cors_allowed_origins" {
  description = "Comma-separated list of allowed CORS origins. localhost:3000 during Phase 1-2, production frontend domain in Phase 3."
  type        = string
  default     = "http://localhost:3000"
}

variable "github_repository" {
  description = "GitHub repository allowed to impersonate the deploy service account via Workload Identity Federation."
  type        = string
  default     = "SanskarLoganDev/zeitgeist"
}

variable "workload_identity_pool_id" {
  description = "Workload Identity Pool ID used by GitHub Actions."
  type        = string
  default     = "github-pool"
}
