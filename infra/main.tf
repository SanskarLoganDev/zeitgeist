terraform {
  required_version = ">= 1.8"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

module "artifact_registry" {
  source     = "./modules/artifact_registry"
  project_id = var.gcp_project_id
  region     = var.gcp_region
}

module "secrets" {
  source     = "./modules/secrets"
  project_id = var.gcp_project_id
}

module "cloud_sql" {
  source      = "./modules/cloud_sql"
  project_id  = var.gcp_project_id
  region      = var.gcp_region
  db_name     = var.db_name
  db_user     = var.db_user
  db_password = var.db_password
}

module "cloud_run" {
  source                = "./modules/cloud_run"
  project_id            = var.gcp_project_id
  region                = var.gcp_region
  api_image             = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/zeitgeist/api:latest"
  frontend_image        = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/zeitgeist/frontend:latest"
  job_image             = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/zeitgeist/job:latest"
  db_connection         = module.cloud_sql.connection_name
  use_placeholder_image = var.use_placeholder_image
  allowed_hosts         = var.allowed_hosts
  cors_allowed_origins  = var.cors_allowed_origins
  github_repository     = var.github_repository
  wif_pool_id           = var.workload_identity_pool_id
  depends_on            = [module.cloud_sql, module.artifact_registry]
}

module "scheduler" {
  source          = "./modules/scheduler"
  project_id      = var.gcp_project_id
  region          = var.gcp_region
  job_name        = module.cloud_run.ingestion_job_name
  service_account = module.cloud_run.service_account_email
  depends_on      = [module.cloud_run]
}
