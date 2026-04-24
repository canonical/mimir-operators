output "app_names" {
  value = merge(
    {
      mimir_s3_integrator = juju_application.s3_integrator.name,
      mimir_coordinator   = module.mimir_coordinator.app_name,
      mimir_read          = var.monolithic ? null : module.mimir_read[0].app_name,
      mimir_write         = var.monolithic ? null : module.mimir_write[0].app_name,
      mimir_backend       = var.monolithic ? null : module.mimir_backend[0].app_name,
      mimir_all           = var.monolithic ? module.mimir_all[0].app_name : null,
    }
  )
  description = "All application names which make up this product module"
}

output "provides" {
  value = {
    grafana_dashboards_provider = "grafana-dashboards-provider",
    grafana_source              = "grafana-source",
    mimir_cluster               = module.mimir_coordinator.provides.mimir_cluster,
    receive_remote_write        = "receive-remote-write",
    self_metrics_endpoint       = "self-metrics-endpoint",
    send_datasource             = "send-datasource",
  }
  description = "All Juju integration endpoints where the charm is the provider"
}

output "requires" {
  value = {
    alertmanager     = "alertmanager",
    certificates     = "certificates",
    ingress          = "ingress",
    logging_consumer = "logging-consumer",
    s3               = "s3",
    charm_tracing    = "charm-tracing",
    catalogue        = "catalogue",
  }
  description = "All Juju integration endpoints where the charm is the requirer"
}
