output "app_name" {
  value = juju_application.mimir_worker.name
}

output "endpoints" {
  value = {
    # Requires
    mimir_cluster = "mimir-cluster"
    # Provides
  }
}
