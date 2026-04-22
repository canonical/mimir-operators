output "app_name" {
  value = juju_application.mimir_coordinator.name
}

output "provides" {
  value = {
    mimir_cluster = "mimir-cluster"
  }
  description = "All Juju integration endpoints where the charm is the provider"
}

output "requires" {
  value       = {}
  description = "All Juju integration endpoints where the charm is the requirer"
}
