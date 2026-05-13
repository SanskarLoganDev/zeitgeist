variable "project_id"         { type = string }
variable "region"             { type = string }
variable "api_image"          { type = string }
variable "job_image"          { type = string }
variable "db_connection"      { type = string }
variable "service_account"    { type = string }
variable "allowed_hosts"      {
  type    = string
  default = "localhost"
}
variable "cors_allowed_origins" {
  type    = string
  default = "http://localhost:3000"
}
