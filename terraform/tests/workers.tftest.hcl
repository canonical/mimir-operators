mock_provider "juju" {}

variables {
  model_uuid  = "00000000-0000-0000-0000-000000000000"
  channel     = "dev/edge"
}

# --- default: three workers (backend, read, write) ---

run "default_workers" {
  command = plan

  assert {
    condition     = length(module.mimir_worker) == 3
    error_message = "Expected 3 worker modules with default workers config"
  }

  assert {
    condition     = length(juju_integration.coordinator_to_worker) == 3
    error_message = "Expected 3 coordinator-to-worker integrations"
  }
}

# --- monolithic mode: single worker with role-all ---

run "monolithic_mode" {
  command = plan

  variables {
    workers = {
      all = {}
    }
  }

  assert {
    condition     = length(module.mimir_worker) == 1
    error_message = "Expected 1 worker module in monolithic mode"
  }

  assert {
    condition     = length(juju_integration.coordinator_to_worker) == 1
    error_message = "Expected 1 coordinator-to-worker integration in monolithic mode"
  }
}

# --- custom units per worker ---

run "custom_units" {
  command = plan

  variables {
    workers = {
      backend = { units = 3 }
      read    = { units = 2 }
      write   = { units = 5 }
    }
  }

  assert {
    condition     = module.mimir_worker["backend"].app_name == "mimir-backend"
    error_message = "Expected backend worker app_name to be mimir-backend"
  }

  assert {
    condition     = module.mimir_worker["read"].app_name == "mimir-read"
    error_message = "Expected read worker app_name to be mimir-read"
  }

  assert {
    condition     = module.mimir_worker["write"].app_name == "mimir-write"
    error_message = "Expected write worker app_name to be mimir-write"
  }
}

# --- custom app_name override ---

run "custom_app_name" {
  command = plan

  variables {
    workers = {
      backend = { app_name = "my-backend" }
      read    = {}
      write   = {}
    }
  }

  assert {
    condition     = module.mimir_worker["backend"].app_name == "my-backend"
    error_message = "Expected custom app_name to be used"
  }

  assert {
    condition     = module.mimir_worker["read"].app_name == "mimir-read"
    error_message = "Expected default app_name mimir-read"
  }
}

# --- subset of workers (only read and write) ---

run "subset_workers" {
  command = plan

  variables {
    workers = {
      read  = { units = 2 }
      write = { units = 2 }
    }
  }

  assert {
    condition     = length(module.mimir_worker) == 2
    error_message = "Expected 2 worker modules"
  }

  assert {
    condition     = length(juju_integration.coordinator_to_worker) == 2
    error_message = "Expected 2 coordinator-to-worker integrations"
  }
}
