variable "project_id" { type = string }
variable "region" { type = string }
variable "api_image" { type = string }
variable "frontend_image" { type = string }
variable "job_image" { type = string }
variable "db_connection" { type = string }
variable "github_repository" {
  type    = string
  default = "SanskarLoganDev/zeitgeist"
}
variable "wif_pool_id" {
  type    = string
  default = "github-pool"
}
variable "allowed_hosts" {
  type    = string
  default = "localhost"
}
variable "cors_allowed_origins" {
  type    = string
  default = "http://localhost:3000"
}

# ── Placeholder image ─────────────────────────────────────────────────────────
# On first terraform apply the real Docker images don't exist yet —
# the CD pipeline hasn't run. Cloud Run requires a valid image to create
# the service. Keep this true for bootstrap; after CD deploys the real images,
# lifecycle.ignore_changes in main.tf prevents Terraform from rolling the live
# service/job back to placeholders.
variable "use_placeholder_image" {
  type        = bool
  default     = true
  description = "Use placeholder image for initial apply before real images are built"
}
