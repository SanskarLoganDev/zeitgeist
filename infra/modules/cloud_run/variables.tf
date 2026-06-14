variable "project_id"         { type = string }
variable "region"             { type = string }
variable "api_image"          { type = string }
variable "job_image"          { type = string }
variable "db_connection"      { type = string }
variable "service_account"    { type = string }
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
# the service. Set use_placeholder_image = true for the initial apply,
# then set it to false after the first successful CD pipeline run.
# Google's hello-world image is a tiny public image that starts instantly.
variable "use_placeholder_image" {
  type        = bool
  default     = true
  description = "Use placeholder image for initial apply before real images are built"
}
