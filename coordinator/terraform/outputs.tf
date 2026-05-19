output "app_name" {
  value = juju_application.mimir_coordinator.name
}

output "provides" {
  value = {
    mimir_cluster    = "mimir-cluster",
    provide_cmr_mesh = "provide-cmr-mesh",
  }
  description = "All Juju integration endpoints where the charm is the provider"
}

output "requires" {
  value = {
    require_cmr_mesh = "require-cmr-mesh",
    service_mesh     = "service-mesh",
  }
  description = "All Juju integration endpoints where the charm is the requirer"
}
