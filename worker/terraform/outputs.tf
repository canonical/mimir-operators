output "app_name" {
  value = juju_application.mimir_worker.name
}

output "requires" {
  value = {
    mimir_cluster = "mimir-cluster"
  }
}
