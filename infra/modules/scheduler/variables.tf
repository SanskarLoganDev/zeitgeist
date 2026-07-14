variable "project_id" { type = string }
variable "region" { type = string }
variable "job_name" { type = string }
variable "service_account" { type = string }
variable "api_url" {
  type    = string
  default = "" # Required only when weekly digest scheduler is enabled (Phase 3)
}
