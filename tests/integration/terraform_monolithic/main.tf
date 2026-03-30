# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

# Integration test Terraform configuration for monolithic Mimir deployment.
# This reuses the shipped product Terraform module (../../../terraform) to
# validate the real Terraform interface that consumers use.
#
# SeaweedFS is deployed as an S3-compatible backing store, mirroring
# real-world usage where S3 is provisioned independently.

terraform {
  required_version = ">= 1.5"
  required_providers {
    juju = {
      source  = "juju/juju"
      version = "~> 1.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

resource "random_id" "model_name" {
  byte_length = 4
  prefix      = "test-terraform-monolithic-"
}

locals {
  s3_bucket = "mimir"
  # SeaweedFS's predictable in-cluster endpoint, derived from the Juju model
  # name and the app name. SeaweedFS listens on port 8333 for S3 traffic.
  s3_endpoint = "seaweedfs-0.seaweedfs-endpoints.${juju_model.test_model.name}.svc.cluster.local:8333"
}

resource "juju_model" "test_model" {
  name   = random_id.model_name.id
  config = { logging-config = "<root>=WARNING; unit=DEBUG" }
}

# ──────────────────────────────────────────────────────────
# SeaweedFS — S3-compatible storage stand-in
# We're not going to integrate it, because mimir tf module
# already deploys s3-integrator. Seaweedfs in this test is
# just a ceph stand-in.
# ──────────────────────────────────────────────────────────

module "s3-standin" {
  source = "git::https://github.com/sed-i/seaweedfs-k8s-operator//terraform"

  app_name   = "seaweedfs"
  model_uuid = juju_model.test_model.uuid
  channel    = "latest/edge"
  config     = { bucket = local.s3_bucket }
}

# ──────────────────────────────────────────────────────────
# Mimir product module (coordinator + workers + s3-integrator)
# ──────────────────────────────────────────────────────────

module "mimir" {
  source = "../../../terraform"

  model_uuid    = juju_model.test_model.uuid
  channel       = "dev/edge"
  anti_affinity = false

  # S3 configuration — points at the SeaweedFS deployed above.
  s3_endpoint   = local.s3_endpoint
  s3_access_key = "placeholder"
  s3_secret_key = "placeholder"
  s3_bucket     = local.s3_bucket

  depends_on = [module.s3-standin]
}

# ──────────────────────────────────────────────────────────
# Outputs
# ──────────────────────────────────────────────────────────

output "app_names" {
  value       = module.mimir.app_names
  description = "All application names deployed by the Mimir module"
}

output "endpoints" {
  value       = module.mimir.endpoints
  description = "All Juju integration endpoints exposed by the Mimir module"
}

output "model_name" {
  value       = juju_model.test_model.name
  description = "The randomly generated Juju model name"
}
