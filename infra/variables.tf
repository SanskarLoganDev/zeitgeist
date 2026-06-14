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
