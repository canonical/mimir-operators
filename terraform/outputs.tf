output "app_names" {
  value = merge(
    {
      mimir_coordinator = module.mimir_coordinator.app_name,
    },
    local.deploy_s3 ? { mimir_s3_integrator = juju_application.s3_integrator[0].name } : {},
    { for k, v in module.mimir_worker : "mimir_${k}" => v.app_name }
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
    provide_cmr_mesh            = module.mimir_coordinator.provides.provide_cmr_mesh,
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
    require_cmr_mesh = module.mimir_coordinator.requires.require_cmr_mesh,
    service_mesh     = module.mimir_coordinator.requires.service_mesh,
  }
  description = "All Juju integration endpoints where the charm is the requirer"
}
