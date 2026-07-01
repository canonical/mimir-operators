module "mimir_coordinator" {
  source             = "../coordinator/terraform"
  app_name           = "mimir"
  base               = var.base
  channel            = var.channel
  config             = var.coordinator_config
  constraints        = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=mimir,anti-pod.topology-key=kubernetes.io/hostname" : var.coordinator_constraints
  model_uuid         = var.model_uuid
  resources          = var.coordinator_resources
  revision           = var.coordinator_revision
  storage_directives = var.coordinator_storage_directives
  units              = var.coordinator_units
}

module "mimir_backend" {
  source     = "../worker/terraform"
  depends_on = [module.mimir_coordinator]

  app_name    = var.backend_name
  base        = var.base
  channel     = var.channel
  constraints = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.backend_name},anti-pod.topology-key=kubernetes.io/hostname" : var.worker_constraints
  config = merge({
    role-backend = true
  }, var.backend_config)
  model_uuid         = var.model_uuid
  resources          = var.worker_resources
  revision           = var.worker_revision
  storage_directives = var.backend_worker_storage_directives
  units              = var.backend_units
}

module "mimir_read" {
  source     = "../worker/terraform"
  depends_on = [module.mimir_coordinator]

  app_name = var.read_name
  base     = var.base
  channel  = var.channel
  config = merge({
    role-read = true
  }, var.read_config)
  constraints        = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.read_name},anti-pod.topology-key=kubernetes.io/hostname" : var.worker_constraints
  model_uuid         = var.model_uuid
  resources          = var.worker_resources
  revision           = var.worker_revision
  storage_directives = var.read_worker_storage_directives
  units              = var.read_units
}

module "mimir_write" {
  source     = "../worker/terraform"
  depends_on = [module.mimir_coordinator]

  app_name = var.write_name
  base     = var.base
  channel  = var.channel
  config = merge({
    role-write = true
  }, var.write_config)
  constraints        = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${var.write_name},anti-pod.topology-key=kubernetes.io/hostname" : var.worker_constraints
  model_uuid         = var.model_uuid
  resources          = var.worker_resources
  revision           = var.worker_revision
  storage_directives = var.write_worker_storage_directives
  units              = var.write_units
}

# -------------- # S3-integrator --------------

resource "juju_secret" "mimir_s3_credentials_secret" {
  model_uuid = var.model_uuid
  name       = "mimir_s3_credentials"
  value = {
    access-key = var.s3_access_key
    secret-key = var.s3_secret_key
  }
  info = "Credentials for the S3 endpoint"
}

resource "juju_access_secret" "mimir_s3_secret_access" {
  model_uuid = var.model_uuid
  applications = [
    juju_application.s3_integrator.name
  ]
  secret_id = juju_secret.mimir_s3_credentials_secret.secret_id
}

resource "juju_application" "s3_integrator" {
  config = merge({
    endpoint    = var.s3_endpoint
    bucket      = var.s3_bucket
    credentials = "secret:${juju_secret.mimir_s3_credentials_secret.secret_id}"
  }, var.s3_integrator_config)
  constraints        = var.s3_integrator_constraints
  model_uuid         = var.model_uuid
  name               = var.s3_integrator_name
  storage_directives = var.s3_integrator_storage_directives
  trust              = true
  units              = var.s3_integrator_units

  charm {
    name     = "s3-integrator"
    channel  = var.s3_integrator_channel
    revision = var.s3_integrator_revision
  }
}

# -------------- # Integrations --------------

resource "juju_integration" "coordinator_to_s3_integrator" {
  model_uuid = var.model_uuid
  application {
    name     = juju_application.s3_integrator.name
    endpoint = "s3-credentials"
  }

  application {
    name     = module.mimir_coordinator.app_name
    endpoint = "s3"
  }
}

resource "juju_integration" "coordinator_to_read" {
  model_uuid = var.model_uuid

  application {
    name     = module.mimir_coordinator.app_name
    endpoint = module.mimir_coordinator.provides.mimir_cluster
  }

  application {
    name     = module.mimir_read.app_name
    endpoint = module.mimir_read.requires.mimir_cluster
  }
}

resource "juju_integration" "coordinator_to_write" {
  model_uuid = var.model_uuid

  application {
    name     = module.mimir_coordinator.app_name
    endpoint = module.mimir_coordinator.provides.mimir_cluster
  }

  application {
    name     = module.mimir_write.app_name
    endpoint = module.mimir_write.requires.mimir_cluster
  }
}

resource "juju_integration" "coordinator_to_backend" {
  model_uuid = var.model_uuid

  application {
    name     = module.mimir_coordinator.app_name
    endpoint = module.mimir_coordinator.provides.mimir_cluster
  }

  application {
    name     = module.mimir_backend.app_name
    endpoint = module.mimir_backend.requires.mimir_cluster
  }
}
