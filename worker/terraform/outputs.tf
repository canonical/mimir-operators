output "app_name" {
  value = juju_application.mimir_worker.name
}

output "provides" {
  value       = {}
  description = "All Juju integration endpoints where the charm is the provider"
}

output "requires" {
  value = {
    mimir_cluster = "mimir-cluster"
  }
  description = "All Juju integration endpoints where the charm is the requirer"
}
