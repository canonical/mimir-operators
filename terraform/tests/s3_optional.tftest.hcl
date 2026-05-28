mock_provider "juju" {}

variables {
  model_uuid  = "00000000-0000-0000-0000-000000000000"
  channel     = "dev/edge"
}

# --- default: S3 disabled (no integrator deployed) ---

run "s3_disabled_by_default" {
  command = plan

  assert {
    condition     = length(juju_application.s3_integrator) == 0
    error_message = "Expected no s3-integrator when s3_endpoint is null"
  }

  assert {
    condition     = length(juju_secret.mimir_s3_credentials_secret) == 0
    error_message = "Expected no s3 credentials secret when s3_endpoint is null"
  }

  assert {
    condition     = length(juju_access_secret.mimir_s3_secret_access) == 0
    error_message = "Expected no s3 access secret when s3_endpoint is null"
  }

  assert {
    condition     = length(juju_integration.coordinator_to_s3_integrator) == 0
    error_message = "Expected no s3 integration when s3_endpoint is null"
  }
}

# --- S3 enabled: all resources created ---

run "s3_enabled" {
  command = plan

  variables {
    s3_endpoint   = "https://s3.example.com"
    s3_access_key = "access-key"
    s3_secret_key = "secret-key"
  }

  assert {
    condition     = length(juju_application.s3_integrator) == 1
    error_message = "Expected s3-integrator when s3_endpoint is set"
  }

  assert {
    condition     = length(juju_secret.mimir_s3_credentials_secret) == 1
    error_message = "Expected s3 credentials secret when s3_endpoint is set"
  }

  assert {
    condition     = length(juju_access_secret.mimir_s3_secret_access) == 1
    error_message = "Expected s3 access secret when s3_endpoint is set"
  }

  assert {
    condition     = length(juju_integration.coordinator_to_s3_integrator) == 1
    error_message = "Expected s3 integration when s3_endpoint is set"
  }
}
