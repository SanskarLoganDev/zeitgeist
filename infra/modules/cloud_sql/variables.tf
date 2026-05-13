variable "project_id"   { type = string }
variable "region"       { type = string }
variable "db_name"      { type = string }
variable "db_user"      { type = string }
variable "db_password"  {
  type      = string
  sensitive = true
  default   = ""   # Set via TF_VAR_db_password env var in CI — never in tfvars
}
variable "vpc_network"  {
  type    = string
  default = "projects/${var.project_id}/global/networks/default"
}
