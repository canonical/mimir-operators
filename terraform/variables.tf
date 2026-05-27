variable "model_uuid" {
  description = "Reference to an existing model resource or data source for the model to deploy to"
  type        = string
}

variable "channel" {
  description = "Channel that the applications are deployed from"
  type        = string

  validation {
    condition     = startswith(var.channel, "dev/")
    error_message = "The track of the channel must be 'dev/'. e.g. 'dev/edge'."
  }
}

variable "anti_affinity" {
  description = "Enable anti-affinity constraints."
  type        = bool
  default     = true
}

# -------------- # S3 object storage --------------

variable "s3_integrator_channel" {
  description = "Channel that the s3-integrator application is deployed from"
  type        = string
  default     = "2/stable"
}

variable "s3_bucket" {
  description = "Bucket name"
  type        = string
  default     = "mimir"
}

variable "s3_access_key" {
  description = "S3 access-key credential. Set to null (along with s3_endpoint and s3_secret_key) to skip deploying the S3 integrator."
  type        = string
  default     = null
}

variable "s3_secret_key" {
  description = "S3 secret-key credential. Set to null (along with s3_endpoint and s3_access_key) to skip deploying the S3 integrator."
  type        = string
  sensitive   = true
  default     = null
}

variable "s3_endpoint" {
  description = "S3 endpoint. When null, the S3 integrator is not deployed and the caller must handle storage integration externally."
  type        = string
  default     = null

  validation {
    condition = (
      (var.s3_endpoint == null && var.s3_access_key == null && var.s3_secret_key == null) ||
      (var.s3_endpoint != null && var.s3_access_key != null && var.s3_secret_key != null)
    )
    error_message = "s3_endpoint, s3_access_key, and s3_secret_key must all be set or all be null."
  }
}

# -------------- # Workers --------------

variable "workers" {
  description = "Map of worker roles to deploy. Keys must be one of: all, backend, read, write. When 'all' is used, a single worker with role-all is created."
  type = map(object({
    units              = optional(number, 1)
    config             = optional(map(string), {})
    constraints        = optional(string, "arch=amd64")
    storage_directives = optional(map(string), {})
    app_name           = optional(string)
  }))
  default = {
    backend = {}
    read    = {}
    write   = {}
  }

  validation {
    condition     = alltrue([for k in keys(var.workers) : contains(["all", "backend", "read", "write"], k)])
    error_message = "Worker keys must be one of: all, backend, read, write."
  }

  validation {
    condition     = !(contains(keys(var.workers), "all") && length(var.workers) > 1)
    error_message = "When using role 'all', no other worker roles may be specified."
  }

  validation {
    condition     = alltrue([for k, v in var.workers : v.units >= 1])
    error_message = "The number of units for each worker must be greater than or equal to 1."
  }
}

variable "s3_integrator_name" {
  description = "Name of the s3-integrator app"
  type        = string
  default     = "mimir-s3-integrator"
}

# -------------- # Configs --------------

variable "coordinator_config" {
  description = "Map of the coordinator configuration options"
  type        = map(string)
  default     = {}
}

variable "s3_integrator_config" {
  description = "Map of the s3-integrator configuration options"
  type        = map(string)
  default     = {}
}

# -------------- # Constraints --------------

# We use constraints to set AntiAffinity in K8s
# https://discourse.charmhub.io/t/pod-priority-and-affinity-in-juju-charms/4091/13?u=jose

# FIXME: Passing an empty constraints value to the Juju Terraform provider currently
# causes the operation to fail due to https://github.com/juju/terraform-provider-juju/issues/344
# Therefore, we set a default value of "arch=amd64" for all applications.

variable "coordinator_constraints" {
  description = "String listing constraints for the coordinator application"
  type        = string
  default     = "arch=amd64"

  validation {
    condition     = !(var.anti_affinity && var.coordinator_constraints != "arch=amd64")
    error_message = "Setting both custom charm constraints and anti-affinity to true is not allowed."
  }
}

variable "s3_integrator_constraints" {
  description = "String listing constraints for the s3-integrator application"
  type        = string
  default     = "arch=amd64"

  validation {
    condition     = !(var.anti_affinity && var.s3_integrator_constraints != "arch=amd64")
    error_message = "Setting both custom charm constraints and anti-affinity to true is not allowed."
  }
}

# -------------- # Resources --------------

variable "coordinator_resources" {
  description = "The coordinator application's resources i.e., a resource revision number from CharmHub or a custom OCI image resource"
  type        = map(string)
  default     = {}
}

variable "worker_resources" {
  description = "The worker application's resources i.e., a resource revision number from CharmHub or a custom OCI image resource"
  type        = map(string)
  default     = {}
}

# -------------- # Revisions --------------

variable "coordinator_revision" {
  description = "Revision number of the coordinator application"
  type        = number
  default     = null
}

variable "worker_revision" {
  description = "Revision number of the worker application"
  type        = number
  default     = null
}

variable "s3_integrator_revision" {
  description = "Revision number of the s3-integrator application"
  type        = number
  default     = null
}

# -------------- # Storage directives --------------

variable "coordinator_storage_directives" {
  description = "Map of storage used by the coordinator application, which defaults to 1 GB, allocated by Juju"
  type        = map(string)
  default     = {}
}

variable "s3_integrator_storage_directives" {
  description = "Map of storage used by the s3-integrator application, which defaults to 1 GB, allocated by Juju"
  type        = map(string)
  default     = {}
}

# -------------- # Units Per App --------------

variable "coordinator_units" {
  description = "Number of Mimir coordinator units"
  type        = number
  default     = 1
  validation {
    condition     = var.coordinator_units >= 1
    error_message = "The number of units must be greater than or equal to 1."
  }
}

variable "s3_integrator_units" {
  description = "Number of S3 integrator units"
  type        = number
  default     = 1
  validation {
    condition     = var.s3_integrator_units >= 1
    error_message = "The number of units must be greater than or equal to 1."
  }
}
