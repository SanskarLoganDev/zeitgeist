# ── Production Entry Point ────────────────────────────────────────────────────
# Public HTTPS load balancer for dailyzeitgeist.xyz.
# Cloud Run direct run.app access intentionally stays open during this phase.

locals {
  name_prefix = "zeitgeist"
}

resource "google_compute_global_address" "main" {
  project = var.project_id
  name    = "${local.name_prefix}-lb-ip"
}

resource "google_compute_managed_ssl_certificate" "main" {
  project = var.project_id
  name    = "${local.name_prefix}-managed-cert"

  managed {
    domains = [var.domain]
  }
}

resource "google_compute_region_network_endpoint_group" "api" {
  project               = var.project_id
  name                  = "${local.name_prefix}-api-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = var.api_service_name
  }
}

resource "google_compute_region_network_endpoint_group" "frontend" {
  project               = var.project_id
  name                  = "${local.name_prefix}-frontend-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = var.frontend_service_name
  }
}

resource "google_compute_security_policy" "api" {
  project     = var.project_id
  name        = "${local.name_prefix}-api-armor"
  description = "Edge protection for Zeitgeist API auth endpoints"

  rule {
    action      = "throttle"
    priority    = 1000
    description = "Throttle auth endpoint bursts by client IP"

    match {
      expr {
        expression = "request.path.lower().urlDecode().startsWith('/api/v1/auth/')"
      }
    }

    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"

      rate_limit_threshold {
        count        = 30
        interval_sec = 60
      }
    }
  }

  rule {
    action      = "allow"
    priority    = 2147483647
    description = "Default allow"

    match {
      versioned_expr = "SRC_IPS_V1"

      config {
        src_ip_ranges = ["*"]
      }
    }
  }
}

resource "google_compute_backend_service" "api" {
  project               = var.project_id
  name                  = "${local.name_prefix}-api-backend"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTP"
  security_policy       = google_compute_security_policy.api.id

  backend {
    group = google_compute_region_network_endpoint_group.api.id
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

resource "google_compute_backend_service" "frontend" {
  project               = var.project_id
  name                  = "${local.name_prefix}-frontend-backend"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTP"

  backend {
    group = google_compute_region_network_endpoint_group.frontend.id
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

resource "google_compute_url_map" "https" {
  project = var.project_id
  name    = "${local.name_prefix}-https-url-map"

  default_service = google_compute_backend_service.frontend.id

  host_rule {
    hosts        = ["*"]
    path_matcher = "main"
  }

  path_matcher {
    name            = "main"
    default_service = google_compute_backend_service.frontend.id

    path_rule {
      paths   = ["/api", "/api/*"]
      service = google_compute_backend_service.api.id
    }
  }
}

resource "google_compute_url_map" "http_redirect" {
  project = var.project_id
  name    = "${local.name_prefix}-http-redirect"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_https_proxy" "main" {
  project          = var.project_id
  name             = "${local.name_prefix}-https-proxy"
  url_map          = google_compute_url_map.https.id
  ssl_certificates = [google_compute_managed_ssl_certificate.main.id]
}

resource "google_compute_target_http_proxy" "redirect" {
  project = var.project_id
  name    = "${local.name_prefix}-http-redirect-proxy"
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_global_forwarding_rule" "https" {
  project               = var.project_id
  name                  = "${local.name_prefix}-https-forwarding-rule"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.main.id
  port_range            = "443"
  target                = google_compute_target_https_proxy.main.id
}

resource "google_compute_global_forwarding_rule" "http" {
  project               = var.project_id
  name                  = "${local.name_prefix}-http-forwarding-rule"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.main.id
  port_range            = "80"
  target                = google_compute_target_http_proxy.redirect.id
}
