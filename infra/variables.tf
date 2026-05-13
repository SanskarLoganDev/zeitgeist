variable "gcp_project_id" {
  description = "GCP project ID — e.g. zeitgeist-prod-123456"
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
