module "mimir_coordinator" {
  source             = "../coordinator/terraform"
  app_name           = "mimir"
  channel            = var.channel
  config             = var.coordinator_config
  constraints        = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=mimir,anti-pod.topology-key=kubernetes.io/hostname" : var.coordinator_constraints
  model_uuid         = var.model_uuid
  resources          = var.coordinator_resources
  revision           = var.coordinator_revision
  storage_directives = var.coordinator_storage_directives
  units              = var.coordinator_units
}

locals {
  workers = { for k, v in var.workers : k => merge(v, {
    app_name = coalesce(v.app_name, "mimir-${k}")
  }) }
}

module "mimir_worker" {
  for_each = local.workers
  source   = "../worker/terraform"

  app_name           = each.value.app_name
  channel            = var.channel
  config             = merge({ "role-${each.key}" = "true" }, each.value.config)
  constraints        = var.anti_affinity ? "arch=amd64 tags=anti-pod.app.kubernetes.io/name=${each.value.app_name},anti-pod.topology-key=kubernetes.io/hostname" : each.value.constraints
  model_uuid         = var.model_uuid
  resources          = var.worker_resources
  revision           = var.worker_revision
  storage_directives = each.value.storage_directives
  units              = each.value.units
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

resource "juju_integration" "coordinator_to_worker" {
  for_each   = local.workers
  model_uuid = var.model_uuid

  application {
    name     = module.mimir_coordinator.app_name
    endpoint = module.mimir_coordinator.provides.mimir_cluster
  }

  application {
    name     = module.mimir_worker[each.key].app_name
    endpoint = module.mimir_worker[each.key].requires.mimir_cluster
  }
}
