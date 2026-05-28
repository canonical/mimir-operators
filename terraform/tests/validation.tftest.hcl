mock_provider "juju" {}

variables {
  model_uuid  = "00000000-0000-0000-0000-000000000000"
  channel     = "dev/edge"
}

# --- invalid worker key ---

run "invalid_worker_key" {
  command         = plan
  expect_failures = [var.workers]

  variables {
    workers = {
      invalid_role = {}
    }
  }
}

# --- role-all with other roles ---

run "all_with_other_roles" {
  command         = plan
  expect_failures = [var.workers]

  variables {
    workers = {
      all     = {}
      backend = {}
    }
  }
}

# --- zero units ---

run "zero_units" {
  command         = plan
  expect_failures = [var.workers]

  variables {
    workers = {
      backend = { units = 0 }
    }
  }
}

# --- partial S3 config: endpoint without credentials ---

run "s3_endpoint_without_credentials" {
  command         = plan
  expect_failures = [var.s3_endpoint]

  variables {
    s3_endpoint = "https://s3.example.com"
  }
}

# --- partial S3 config: credentials without endpoint ---

run "s3_credentials_without_endpoint" {
  command         = plan
  expect_failures = [var.s3_endpoint]

  variables {
    s3_access_key = "access-key"
    s3_secret_key = "secret-key"
  }
}

# --- invalid channel track ---

run "invalid_channel" {
  command         = plan
  expect_failures = [var.channel]

  variables {
    channel = "stable"
  }
}

# --- anti-affinity with custom coordinator constraints ---

run "anti_affinity_with_custom_coordinator_constraints" {
  command         = plan
  expect_failures = [var.coordinator_constraints]

  variables {
    anti_affinity            = true
    coordinator_constraints  = "arch=arm64"
  }
}
