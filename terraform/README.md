# Terraform module for Mimir solution

This is a Terraform module facilitating the deployment of Mimir solution, using the [Terraform juju provider](https://github.com/juju/terraform-provider-juju/). For more information, refer to the provider [documentation](https://registry.terraform.io/providers/juju/juju/latest/docs). This Terraform module deploys Mimir in its [microservices mode](https://grafana.com/docs/mimir/latest/references/architecture/deployment-modes/#microservices-mode), which runs each one of the required roles in distinct processes.

> [!NOTE]
> `s3-integrator` itself doesn't act as an S3 object storage system. For the HA solution to be functional, `s3-integrator` needs to point to an S3-like storage. See [this guide](https://discourse.charmhub.io/t/cos-lite-docs-set-up-minio/15211) to learn how to connect to an S3-like storage for traces.

<!-- BEGIN_TF_DOCS -->
## Providers

| Name | Version |
|------|---------|
| <a name="provider_juju"></a> [juju](#provider\_juju) | >= 1.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_mimir_coordinator"></a> [mimir\_coordinator](#module\_mimir\_coordinator) | ../coordinator/terraform | n/a |
| <a name="module_mimir_worker"></a> [mimir\_worker](#module\_mimir\_worker) | ../worker/terraform | n/a |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_anti_affinity"></a> [anti\_affinity](#input\_anti\_affinity) | Enable anti-affinity constraints. | `bool` | `true` | no |
| <a name="input_channel"></a> [channel](#input\_channel) | Channel that the applications are deployed from | `string` | n/a | yes |
| <a name="input_coordinator_config"></a> [coordinator\_config](#input\_coordinator\_config) | Map of the coordinator configuration options | `map(string)` | `{}` | no |
| <a name="input_coordinator_constraints"></a> [coordinator\_constraints](#input\_coordinator\_constraints) | String listing constraints for the coordinator application | `string` | `"arch=amd64"` | no |
| <a name="input_coordinator_resources"></a> [coordinator\_resources](#input\_coordinator\_resources) | The coordinator application's resources i.e., a resource revision number from CharmHub or a custom OCI image resource | `map(string)` | `{}` | no |
| <a name="input_coordinator_revision"></a> [coordinator\_revision](#input\_coordinator\_revision) | Revision number of the coordinator application | `number` | `null` | no |
| <a name="input_coordinator_storage_directives"></a> [coordinator\_storage\_directives](#input\_coordinator\_storage\_directives) | Map of storage used by the coordinator application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_coordinator_units"></a> [coordinator\_units](#input\_coordinator\_units) | Number of Mimir coordinator units | `number` | `1` | no |
| <a name="input_model_uuid"></a> [model\_uuid](#input\_model\_uuid) | Reference to an existing model resource or data source for the model to deploy to | `string` | n/a | yes |
| <a name="input_s3_access_key"></a> [s3\_access\_key](#input\_s3\_access\_key) | S3 access-key credential. Set to null (along with s3\_endpoint and s3\_secret\_key) to skip deploying the S3 integrator. | `string` | `null` | no |
| <a name="input_s3_bucket"></a> [s3\_bucket](#input\_s3\_bucket) | Bucket name | `string` | `"mimir"` | no |
| <a name="input_s3_endpoint"></a> [s3\_endpoint](#input\_s3\_endpoint) | S3 endpoint. When null, the S3 integrator is not deployed and the caller must handle storage integration externally. | `string` | `null` | no |
| <a name="input_s3_integrator_channel"></a> [s3\_integrator\_channel](#input\_s3\_integrator\_channel) | Channel that the s3-integrator application is deployed from | `string` | `"2/stable"` | no |
| <a name="input_s3_integrator_config"></a> [s3\_integrator\_config](#input\_s3\_integrator\_config) | Map of the s3-integrator configuration options | `map(string)` | `{}` | no |
| <a name="input_s3_integrator_constraints"></a> [s3\_integrator\_constraints](#input\_s3\_integrator\_constraints) | String listing constraints for the s3-integrator application | `string` | `"arch=amd64"` | no |
| <a name="input_s3_integrator_name"></a> [s3\_integrator\_name](#input\_s3\_integrator\_name) | Name of the s3-integrator app | `string` | `"mimir-s3-integrator"` | no |
| <a name="input_s3_integrator_revision"></a> [s3\_integrator\_revision](#input\_s3\_integrator\_revision) | Revision number of the s3-integrator application | `number` | `null` | no |
| <a name="input_s3_integrator_storage_directives"></a> [s3\_integrator\_storage\_directives](#input\_s3\_integrator\_storage\_directives) | Map of storage used by the s3-integrator application, which defaults to 1 GB, allocated by Juju | `map(string)` | `{}` | no |
| <a name="input_s3_integrator_units"></a> [s3\_integrator\_units](#input\_s3\_integrator\_units) | Number of S3 integrator units | `number` | `1` | no |
| <a name="input_s3_secret_key"></a> [s3\_secret\_key](#input\_s3\_secret\_key) | S3 secret-key credential. Set to null (along with s3\_endpoint and s3\_access\_key) to skip deploying the S3 integrator. | `string` | `null` | no |
| <a name="input_worker_resources"></a> [worker\_resources](#input\_worker\_resources) | The worker application's resources i.e., a resource revision number from CharmHub or a custom OCI image resource | `map(string)` | `{}` | no |
| <a name="input_worker_revision"></a> [worker\_revision](#input\_worker\_revision) | Revision number of the worker application | `number` | `null` | no |
| <a name="input_workers"></a> [workers](#input\_workers) | Map of worker roles to deploy. Keys must be one of: all, backend, read, write. When 'all' is used, a single worker with role-all is created. | <pre>map(object({<br/>    units              = optional(number, 1)<br/>    config             = optional(map(string), {})<br/>    constraints        = optional(string, "arch=amd64")<br/>    storage_directives = optional(map(string), {})<br/>    app_name           = optional(string)<br/>  }))</pre> | <pre>{<br/>  "backend": {},<br/>  "read": {},<br/>  "write": {}<br/>}</pre> | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_app_names"></a> [app\_names](#output\_app\_names) | All application names which make up this product module |
| <a name="output_provides"></a> [provides](#output\_provides) | All Juju integration endpoints where the charm is the provider |
| <a name="output_requires"></a> [requires](#output\_requires) | All Juju integration endpoints where the charm is the requirer |
<!-- END_TF_DOCS -->

## Usage

### Microservices deployment (default)

By default, this module deploys three separate workers — `backend`, `read`, and `write` — each with 1 unit:

```hcl
module "mimir" {
  source     = "git::https://github.com/canonical/mimir-operators//terraform"
  model_uuid = juju_model.cos.uuid
  channel    = "dev/edge"

  s3_endpoint   = "https://s3.example.com"
  s3_access_key = "my-access-key"
  s3_secret_key = "my-secret-key"
}
```

To scale individual roles:

```hcl
module "mimir" {
  source     = "git::https://github.com/canonical/mimir-operators//terraform"
  model_uuid = juju_model.cos.uuid
  channel    = "dev/edge"

  workers = {
    backend = { units = 3, storage_directives = { "data" = "50G" } }
    read    = { units = 2 }
    write   = { units = 2 }
  }

  s3_endpoint   = "https://s3.example.com"
  s3_access_key = "my-access-key"
  s3_secret_key = "my-secret-key"
}
```

See [Mimir worker roles](https://discourse.charmhub.io/t/mimir-worker-roles/15484) for the recommended scale for each role.

### Monolithic deployment

To deploy a single worker with all roles combined:

```hcl
module "mimir" {
  source     = "git::https://github.com/canonical/mimir-operators//terraform"
  model_uuid = juju_model.cos.uuid
  channel    = "dev/edge"

  workers = {
    all = { units = 3 }
  }

  s3_endpoint   = "https://s3.example.com"
  s3_access_key = "my-access-key"
  s3_secret_key = "my-secret-key"
}
```

> [!NOTE]
> When using `all`, no other worker roles may be specified.

### External storage backend (no S3 integrator)

When using an external storage backend (e.g. SeaweedFS), omit the `s3_*` variables. The module will not deploy the S3 integrator, and you are responsible for integrating your storage with the coordinator's `s3` endpoint:

```hcl
module "mimir" {
  source     = "git::https://github.com/canonical/mimir-operators//terraform"
  model_uuid = juju_model.cos.uuid
  channel    = "dev/edge"

  workers = {
    backend = { units = 2 }
    read    = { units = 2 }
    write   = { units = 2 }
  }
}

# Wire external storage to the coordinator
resource "juju_integration" "seaweedfs_mimir" {
  model_uuid = juju_model.cos.uuid

  application {
    name     = module.seaweedfs.app_name
    endpoint = module.seaweedfs.provides.s3
  }

  application {
    name     = module.mimir.app_names.mimir_coordinator
    endpoint = module.mimir.requires.s3
  }
}
```
