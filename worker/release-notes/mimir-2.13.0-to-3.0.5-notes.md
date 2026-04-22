# 2.13.0

Tag: mimir-2.13.0
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.13.0

This release contains 490 PRs from 67 authors, including new contributors Anthony Keydel, Armand Grillet, AvivGuiser, Daniel R. Dagfinrud, David Collier-Brown, David Grant, Dimitris Alo, Enrique Garbi, Erik Sommer, Ian Halliday, InventiveCoder, Kevin Mingtarja, Lasse Hels, Pangidoan Butar, Quentin Bisson, Rens Groothuijsen, René Gärtner, Ross Brunson, Santiago, Seiya, Spyros Panagiotopoulos, Yuri Nikolic, Zied ABID, kahirokunn, lasermoth. Thank you!

# Grafana Mimir version 2.13.0 release notes

<!-- vale Grafana.GoogleWill = NO -->
<!-- vale Grafana.Timeless = NO -->
<!-- Release notes are often future focused -->

Grafana Labs is excited to announce version 2.13 of Grafana Mimir.

The highlights that follow include the top features, enhancements, and bug fixes in this release.
For the complete list of changes, refer to the [CHANGELOG](https://github.com/grafana/mimir/blob/main/CHANGELOG.md).

## Features and enhancements

- **Improved CPU performance in processing queries with regular expressions** that contain many alternations (for example `foo|bar|baz|...`).

- **Improved OTLP ingestion performance** by using native translation, which reduces memory usage in the distributor by up to 30% and CPU usage by up to 8%.

- Configurable S3 bucket lookup type improves interoperability with **S3-compatible providers, such as Tencent and Alibaba**. Configure lookup type via `-<prefix>.s3.bucket-lookup-type` or `-common.storage.s3-bucket-lookup-type`.

- **Configuration of TLS for S3 buckets** is now possible via `-<prefix>.s3.http.*` and `-common.storage.s3.http.*` configuration options.

- **Mimirtool can now verify the validity of a Mimir runtime configuration** file with the `mimirtool runtime-config verify` command.

- **Active series are now updated along with owned series.** This means the number of active series for a tenant is more accurate after scaling out ingesters. As a result, ingesters now more precisely enforce tenants' series limits. This feature is only enabled when `-ingester.track-ingester-owned-series` or `-ingester.use-ingester-owned-series-for-limits` are enabled.

- **Store-gateway can be configured to explicitly disable or enable tenants**. This is useful in cases where compaction slows down for a tenant to temporarily exclude another tenant while compaction catches up without affecting other tenants.

- **Remote read (`/prometheus/api/v1/read`) is becoming a first-class endpoint in Mimir** with support in `query stats` logs and query blocking in the query-frontend. More coming in future releases.

Additionally, the following previously experimental features are now considered stable:

- Rules tenant federation via the `source_tenants` field in rule groups.
- Enabling recording, and alerting rules evaluation on a per-tenant basis.
- Limiting the number of tenants a federated query can query.

## Important changes

In Grafana Mimir 2.13 the following behavior has changed:

- The default Docker image `grafana/mimir` is now based on the distroless image `gcr.io/distroless/static-debian12`.
  See [Debugging distroless container images](https://grafana.com/docs/mimir/latest/manage/mimir-runbooks/#debugging-distroless-container-images-in-kubernetes) for more details on how to
  work with distroless images.

- Error logs in the ingester are now sampled at 10% by default. Sampled log lines contain `(sampled 1/10)`. The `cortex_discarded_samples_total` metric still tracks all discarded samples.

- Anonymous usage statistics now include actual CPU usage instead of available CPU cores.

- Continuous-test is no longer a standalone binary and is now part of Mimir as its own target. The published Docker image has been updated to use the new packaging.

The following deprecated configuration options are removed in Grafana Mimir 2.13:

- The configuration option `-log.buffered`, which was deprecated in 2.11 and is now enabled by default.

## Experimental features

Grafana Mimir 2.13 includes new features that are considered experimental and disabled by default.
Use them with caution and report any issues you encounter:

- Experimental support for server-side circuit breakers in ingesters on read and write requests. This can be enabled using `-ingester.push-circuit-breaker.enabled` and `-ingester.read-circuit-breaker.enabled` options and further configured via the `-ingester.push-circuit-breaker.*` and `-ingester.read-circuit-breaker.*` options.

The following configuration options are deprecated and will be removed in a future Grafana Mimir release:

- `evaluation_delay` field in the rule group configuration has been deprecated. Please use `query_offset` instead.

## Bug fixes

- OTLP ingestion: translate all HTTP 5xx errors into one of 502, 503, or 504, so that the otel-collector retries the failed requests.
- OTLP ingestion: return properly formatted protobuf error messages when ingestion fails.
- OTLP ingestion: generate `target_info` metric only when there are metrics in the request and there is at least one configured identifying label.
- OTLP ingestion: don't discard timeseries paired with invalid exemplars. Instead, try to ingest the timeseries and discard only the invalid exemplars.
- Subqueries: `@ end()` and `@ start()` now work correctly with queries split by time.
- Native histograms: order exemplars before ingestion to improve success rate when ingesting multiple exemplars.
- Native histograms: return HTTP 400 on invalid native histogram samples instead of HTTP 500. The metric `cortex_discarded_samples_total{reason="invalid-native-histogram"}` is now incremented on invalid histogram samples.

### Helm chart improvements

The Grafana Mimir and Grafana Enterprise Metrics Helm charts are released independently.
Refer to the [Grafana Mimir Helm chart documentation](https://grafana.com/docs/helm-charts/mimir-distributed/latest/).


# Changelog

## 2.13.0

### Grafana Mimir

* [CHANGE] Build: `grafana/mimir` docker image is now based on `gcr.io/distroless/static-debian12` image. Alpine-based docker image is still available as `grafana/mimir-alpine`, until Mimir 2.15. #8204 #8235
* [CHANGE] Ingester: `/ingester/flush` endpoint is now only allowed to execute only while the ingester is in `Running` state. The 503 status code is returned if the endpoint is called while the ingester is not in `Running` state. #7486
* [CHANGE] Distributor: Include label name in `err-mimir-label-value-too-long` error message: #7740
* [CHANGE] Ingester: enabled 1 out 10 errors log sampling by default. All the discarded samples will still be tracked by the `cortex_discarded_samples_total` metric. The feature can be configured via `-ingester.error-sample-rate` (0 to log all errors). #7807
* [CHANGE] Query-frontend: Query results caching and experimental query blocking now utilize the PromQL string-formatted query format rather than the unvalidated query as submitted to the frontend. #7742
  * Query results caching should be more stable as all equivalent queries receive the same cache key, but there may be cache churn on first deploy with the updated format
  * Query blocking can no longer be circumvented with an equivalent query in a different format; see [Configure queries to block](https://grafana.com/docs/mimir/latest/configure/configure-blocked-queries/)
* [CHANGE] Query-frontend: stop using `-validation.create-grace-period` to clamp how far into the future a query can span. #8075
* [CHANGE] Clamp [`GOMAXPROCS`](https://pkg.go.dev/runtime#GOMAXPROCS) to [`runtime.NumCPU`](https://pkg.go.dev/runtime#NumCPU). #8201
* [CHANGE] Anonymous usage statistics tracking: add CPU usage percentage tracking. #8282
* [CHANGE] Added new metric `cortex_compactor_disk_out_of_space_errors_total` which counts how many times a compaction failed due to the compactor being out of disk. #8237
* [CHANGE] Anonymous usage statistics tracking: report active series in addition to in-memory series. #8279
* [CHANGE] Ruler: `evaluation_delay` field in the rule group configuration has been deprecated. Please use `query_offset` instead (it has the same exact meaning and behaviour). #8295
* [CHANGE] General: remove `-log.buffered`. The configuration option has been enabled by default and deprecated since Mimir 2.11. #8395
* [CHANGE] Ruler: promote tenant federation from experimental to stable. #8400
* [CHANGE] Ruler: promote `-ruler.recording-rules-evaluation-enabled` and `-ruler.alerting-rules-evaluation-enabled` from experimental to stable. #8400
* [CHANGE] General: promote `-tenant-federation.max-tenants` from experimental to stable. #8400
* [FEATURE] Continuous-test: now runable as a module with `mimir -target=continuous-test`. #7747
* [FEATURE] Store-gateway: Allow specific tenants to be enabled or disabled via `-store-gateway.enabled-tenants` or `-store-gateway.disabled-tenants` CLI flags or their corresponding YAML settings. #7653
* [FEATURE] New `-<prefix>.s3.bucket-lookup-type` flag configures lookup style type, used to access bucket in s3 compatible providers. #7684
* [FEATURE] Querier: add experimental streaming PromQL engine, enabled with `-querier.promql-engine=mimir`. #7693 #7898 #7899 #8023 #8058 #8096 #8121 #8197 #8230 #8247 #8270 #8276 #8277 #8291 #8303 #8340 #8256 #8348
* [FEATURE] New `/ingester/unregister-on-shutdown` HTTP endpoint allows dynamic access to ingesters' `-ingester.ring.unregister-on-shutdown` configuration. #7739
* [FEATURE] Server: added experimental [PROXY protocol support](https://www.haproxy.org/download/2.3/doc/proxy-protocol.txt). The PROXY protocol support can be enabled via `-server.proxy-protocol-enabled=true`. When enabled, the support is added both to HTTP and gRPC listening ports. #7698
* [FEATURE] Query-frontend, querier: new experimental `/cardinality/active_native_histogram_metrics` API to get active native histogram metric names with statistics about active native histogram buckets. #7982 #7986 #8008
* [FEATURE] Alertmanager: Added `-alertmanager.max-silences-count` and `-alertmanager.max-silence-size-bytes` to set limits on per tenant silences. Disabled by default. #8241 #8249
* [FEATURE] Ingester: add experimental support for the server-side circuit breakers when writing to and reading from ingesters. This can be enabled using `-ingester.push-circuit-breaker.enabled` and `-ingester.read-circuit-breaker.enabled` options. Further `-ingester.push-circuit-breaker.*` and `-ingester.read-circuit-breaker.*` options for configuring circuit-breaker are available. Added metrics `cortex_ingester_circuit_breaker_results_total`,  `cortex_ingester_circuit_breaker_transitions_total`, `cortex_ingester_circuit_breaker_current_state` and `cortex_ingester_circuit_breaker_request_timeouts_total`. #8180 #8285 #8315 #8446
* [FEATURE] Distributor, ingester: add new setting `-validation.past-grace-period` to limit how old (based on the wall clock minus OOO window) the ingested samples can be. The default 0 value disables this limit. #8262
* [ENHANCEMENT] Distributor: add metrics `cortex_distributor_samples_per_request` and `cortex_distributor_exemplars_per_request` to track samples/exemplars per request. #8265
* [ENHANCEMENT] Reduced memory allocations in functions used to propagate contextual information between gRPC calls. #7529
* [ENHANCEMENT] Distributor: add experimental limit for exemplars per series per request, enabled with `-distributor.max-exemplars-per-series-per-request`, the number of discarded exemplars are tracked with `cortex_discarded_exemplars_total{reason="too_many_exemplars_per_series_per_request"}` #7989 #8010
* [ENHANCEMENT] Store-gateway: merge series from different blocks concurrently. #7456
* [ENHANCEMENT] Store-gateway: Add `stage="wait_max_concurrent"` to `cortex_bucket_store_series_request_stage_duration_seconds` which records how long the query had to wait for its turn for `-blocks-storage.bucket-store.max-concurrent`. #7609
* [ENHANCEMENT] Querier: add `cortex_querier_federation_upstream_query_wait_duration_seconds` to observe time from when a querier picks up a cross-tenant query to when work begins on its single-tenant counterparts. #7209
* [ENHANCEMENT] Compactor: Add `cortex_compactor_block_compaction_delay_seconds` metric to track how long it takes to compact blocks. #7635
* [ENHANCEMENT] Store-gateway: add `outcome` label to `cortex_bucket_stores_gate_duration_seconds` histogram metric. Possible values for the `outcome` label are: `rejected_canceled`, `rejected_deadline_exceeded`, `rejected_other`, and `permitted`. #7784
* [ENHANCEMENT] Query-frontend: use zero-allocation experimental decoder for active series queries via `-query-frontend.use-active-series-decoder`. #7665
* [ENHANCEMENT] Go: updated to 1.22.2. #7802
* [ENHANCEMENT] Query-frontend: support `limit` parameter on `/prometheus/api/v1/label/{name}/values` and `/prometheus/api/v1/labels` endpoints. #7722
* [ENHANCEMENT] Expose TLS configuration for the S3 backend client. #7959
* [ENHANCEMENT] Rules: Support expansion of native histogram values when using rule templates #7974
* [ENHANCEMENT] Rules: Add metric `cortex_prometheus_rule_group_last_restore_duration_seconds` which measures how long it takes to restore rule groups using the `ALERTS_FOR_STATE` series #7974
* [ENHANCEMENT] OTLP: Improve remote write format translation performance by using label set hashes for metric identifiers instead of string based ones. #8012
* [ENHANCEMENT] Querying: Remove OpEmptyMatch from regex concatenations. #8012
* [ENHANCEMENT] Store-gateway: add `-blocks-storage.bucket-store.max-concurrent-queue-timeout`. When set, queries at the store-gateway's query gate will not wait longer than that to execute. If a query reaches the wait timeout, then the querier will retry the blocks on a different store-gateway. If all store-gateways are unavailable, then the query will fail with `err-mimir-store-consistency-check-failed`. #7777 #8149
* [ENHANCEMENT] Store-gateway: add `-blocks-storage.bucket-store.index-header.lazy-loading-concurrency-queue-timeout`. When set, loads of index-headers at the store-gateway's index-header lazy load gate will not wait longer than that to execute. If a load reaches the wait timeout, then the querier will retry the blocks on a different store-gateway. If all store-gateways are unavailable, then the query will fail with `err-mimir-store-consistency-check-failed`. #8138
* [ENHANCEMENT] Ingester: Optimize querying with regexp matchers. #8106
* [ENHANCEMENT] Distributor: Introduce `-distributor.max-request-pool-buffer-size` to allow configuring the maximum size of the request pool buffers. #8082
* [ENHANCEMENT] Store-gateway: improve performance when streaming chunks to queriers is enabled (`-querier.prefer-streaming-chunks-from-store-gateways=true`) and the query selects fewer than `-blocks-storage.bucket-store.batch-series-size` series (defaults to 5000 series). #8039
* [ENHANCEMENT] Ingester: active series are now updated along with owned series. They decrease when series change ownership between ingesters. This helps provide a more accurate total of active series when ingesters are added. This is only enabled when `-ingester.track-ingester-owned-series` or `-ingester.use-ingester-owned-series-for-limits` are enabled. #8084
* [ENHANCEMENT] Query-frontend: include route name in query stats log lines. #8191
* [ENHANCEMENT] OTLP: Speed up conversion from OTel to Mimir format by about 8% and reduce memory consumption by about 30%. Can be disabled via `-distributor.direct-otlp-translation-enabled=false` #7957
* [ENHANCEMENT] Ingester/Querier: Optimise regexps with long lists of alternates. #8221, #8234
* [ENHANCEMENT] Ingester: Include more detail in tracing of queries. #8242
* [ENHANCEMENT] Distributor: add `insight=true` to remote-write and OTLP write handlers when the HTTP response status code is 4xx. #8294
* [ENHANCEMENT] Ingester: reduce locked time while matching postings for a label, improving the write latency and compaction speed. #8327
* [ENHANCEMENT] Ingester: reduce the amount of locks taken during the Head compaction's garbage-collection process, improving the write latency and compaction speed. #8327
* [ENHANCEMENT] Query-frontend: log the start, end time and matchers for remote read requests to the query stats logs. #8326 #8370 #8373
* [BUGFIX] Distributor: prometheus retry on 5xx and 429 errors, while otlp collector only retry on 429, 502, 503 and 504, mapping other 5xx errors to the retryable ones in otlp endpoint. #8324 #8339
* [BUGFIX] Distributor: make OTLP endpoint return marshalled proto bytes as response body for 4xx/5xx errors. #8227
* [BUGFIX] Rules: improve error handling when querier is local to the ruler. #7567
* [BUGFIX] Querier, store-gateway: Protect against panics raised during snappy encoding. #7520
* [BUGFIX] Ingester: Prevent timely compaction of empty blocks. #7624
* [BUGFIX] Querier: Don't cache context.Canceled errors for bucket index. #7620
* [BUGFIX] Store-gateway: account for `"other"` time in LabelValues and LabelNames requests. #7622
* [BUGFIX] Query-frontend: Don't panic when using the `-query-frontend.downstream-url` flag. #7651
* [BUGFIX] Ingester: when receiving multiple exemplars for a native histogram via remote write, sort them and only report an error if all are older than the latest exemplar as this could be a partial update. #7640 #7948 #8014
* [BUGFIX] Ingester: don't retain blocks if they finish exactly on the boundary of the retention window. #7656
* [BUGFIX] Bug-fixes and improvements to experimental native histograms. #7744 #7813
* [BUGFIX] Querier: return an error when a query uses `label_join` with an invalid destination label name. #7744
* [BUGFIX] Compactor: correct outstanding job estimation in metrics and `compaction-planner` tool when block labels differ. #7745
* [BUGFIX] Ingester: turn native histogram validation errors in TSDB into soft ingester errors that result in returning 4xx to the end-user instead of 5xx. In the case of TSDB validation errors, the counter `cortex_discarded_samples_total` will be increased with the `reason` label set to `"invalid-native-histogram"`. #7736 #7773
* [BUGFIX] Do not wrap error message with `sampled 1/<frequency>` if it's not actually sampled. #7784
* [BUGFIX] Store-gateway: do not track cortex_querier_blocks_consistency_checks_failed_total metric if query has been canceled or interrued due to any error not related to blocks consistency check failed. #7752
* [BUGFIX] Ingester: ignore instances with no tokens when calculating local limits to prevent discards during ingester scale-up #7881
* [BUGFIX] Ingester: do not reuse exemplars slice in the write request if there are more than 10 exemplars per series. This should help to reduce the in-use memory in case of few requests with a very large number of exemplars. #7936
* [BUGFIX] Distributor: fix down scaling of native histograms in the distributor when timeseries unmarshal cache is in use. #7947
* [BUGFIX] Distributor: fix cardinality API to return more accurate number of in-memory series when number of zones is larger than replication factor. #7984
* [BUGFIX] All: fix config validation for non-ingester modules, when ingester's ring is configured with spread-minimizing token generation strategy. #7990
* [BUGFIX] Ingester: copy LabelValues strings out of mapped memory to avoid a segmentation fault if the region becomes unmapped before the result is marshaled. #8003
* [BUGFIX] OTLP: Don't generate target_info unless at least one identifying label is defined. #8012
* [BUGFIX] OTLP: Don't generate target_info unless there are metrics. #8012
* [BUGFIX] Query-frontend: Experimental query queue splitting: fix issue where offset and range selector duration were not considered when predicting query component. #7742
* [BUGFIX] Querying: Empty matrix results were incorrectly returning `null` instead of `[]`. #8029
* [BUGFIX] All: don't increment `thanos_objstore_bucket_operation_failures_total` metric for cancelled requests. #8072
* [BUGFIX] Query-frontend: fix empty metric name matcher not being applied under certain conditions. #8076
* [BUGFIX] Querying: Fix regex matching of multibyte runes with dot operator. #8089
* [BUGFIX] Querying: matrix results returned from instant queries were not sorted by series. #8113
* [BUGFIX] Query scheduler: Fix a crash in result marshaling. #8140
* [BUGFIX] Store-gateway: Allow long-running index scans to be interrupted. #8154
* [BUGFIX] Query-frontend: fix splitting of queries using `@ start()` and `@end()` modifiers on a subquery. Previously the `start()` and `end()` would be evaluated using the start end end of the split query instead of the original query. #8162
* [BUGFIX] Distributor: Don't discard time series with invalid exemplars, just drop affected exemplars. #8224
* [BUGFIX] Ingester: fixed in-memory series count when replaying a corrupted WAL. #8295
* [BUGFIX] Ingester: fix context cancellation handling when a query is busy looking up series in the TSDB index and `-blocks-storage.tsdb.head-postings-for-matchers-cache*` or `-blocks-storage.tsdb.block-postings-for-matchers-cache*` are in use. #8337
* [BUGFIX] Querier: fix edge case where bucket indexes are sometimes cached forever instead of with the expected TTL. #8343
* [BUGFIX] OTLP handler: fix errors returned by OTLP handler when used via httpgrpc tunneling. #8363
* [BUGFIX] Update `github.com/hashicorp/go-retryablehttp` to address [CVE-2024-6104](https://github.com/advisories/GHSA-v6v8-xj6m-xwqh). #8539
* [BUGFIX] Alertmanager: Fixes a number of bugs in silences which could cause an existing silence to be deleted/expired when updating the silence failed. This could happen when the replacing silence was invalid or exceeded limits. #8525
* [BUGFIX] Alertmanager: Fix per-tenant silence limits not reloaded during runtime. #8456
* [BUGFIX] Alertmanager: Fix help message for utf-8-strict-mode. #8572
* [BUGFIX] Upgrade golang to 1.22.5 to address [CVE-2024-24791](https://nvd.nist.gov/vuln/detail/CVE-2024-24791). #8600

### Mixin

* [CHANGE] Alerts: Removed obsolete `MimirQueriesIncorrect` alert that used test-exporter metrics. Test-exporter support was however removed in Mimir 2.0 release. #7774
* [CHANGE] Alerts: Change threshold for `MimirBucketIndexNotUpdated` alert to fire before queries begin to fail due to bucket index age. #7879
* [FEATURE] Dashboards: added 'Remote ruler reads networking' dashboard. #7751
* [FEATURE] Alerts: Add `MimirIngesterStuckProcessingRecordsFromKafka` alert. #8147
* [ENHANCEMENT] Alerts: allow configuring alerts range interval via `_config.base_alerts_range_interval_minutes`. #7591
* [ENHANCEMENT] Dashboards: Add panels for monitoring distributor and ingester when using ingest-storage. These panels are disabled by default, but can be enabled using `show_ingest_storage_panels: true` config option. Similarly existing panels used when distributors and ingesters use gRPC for forwarding requests can be disabled by setting `show_grpc_ingestion_panels: false`. #7670 #7699
* [ENHANCEMENT] Alerts: add the following alerts when using ingest-storage: #7699 #7702
  * `MimirIngesterLastConsumedOffsetCommitFailed`
  * `MimirIngesterFailedToReadRecordsFromKafka`
  * `MimirIngesterKafkaFetchErrorsRateTooHigh`
  * `MimirStartingIngesterKafkaReceiveDelayIncreasing`
  * `MimirRunningIngesterReceiveDelayTooHigh`
  * `MimirIngesterFailsToProcessRecordsFromKafka`
  * `MimirIngesterFailsEnforceStrongConsistencyOnReadPath`
* [ENHANCEMENT] Dashboards: add in-flight queries scaling metric panel for ruler-querier. #7749
* [ENHANCEMENT] Dashboards: renamed rows in the "Remote ruler reads" and "Remote ruler reads resources" dashboards to match the actual component names. #7750
* [ENHANCEMENT] Dashboards: allow switching between using classic of native histograms in dashboards. #7627
  * Overview dashboard, Status panel, `cortex_request_duration_seconds` metric.
* [ENHANCEMENT] Alerts: exclude `529` and `598` status codes from failure codes in `MimirRequestsError`. #7889
* [ENHANCEMENT] Dashboards: renamed "TCP Connections" panel to "Ingress TCP Connections" in the networking dashboards. #8092
* [ENHANCEMENT] Dashboards: update the use of deprecated "table (old)" panels to "table". #8181
* [ENHANCEMENT] Dashboards: added a `component` variable to "Slow queries" dashboard to allow checking the slow queries of the remote ruler evaluation query path. #8309
* [BUGFIX] Dashboards: fix regular expression for matching read-path gRPC ingester methods to include querying of exemplars, label-related queries, or active series queries. #7676
* [BUGFIX] Dashboards: fix user id abbreviations and column heads for Top Tenants dashboard. #7724
* [BUGFIX] Dashboards: fix incorrect query used for "queue length" panel on "Ruler" dashboard. #8006
* [BUGFIX] Dashboards: fix disk space utilization panels when running with a recent version of kube-state-metrics. #8212

### Jsonnet

* [CHANGE] Memcached: Change default read timeout for chunks and index caches to `750ms` from `450ms`. #7778
* [CHANGE] Fine-tuned `terminationGracePeriodSeconds` for the following components: #7364
  * Querier: changed from `30` to `180`
  * Query-scheduler: changed from `30` to `180`
* [CHANGE] Change TCP port exposed by `mimir-continuous-test` deployment to match with updated defaults of its container image (see changes below). #7958
* [FEATURE] Add support to deploy Mimir with experimental ingest storage enabled. #8028 #8222
* [ENHANCEMENT] Compactor: add `$._config.cortex_compactor_concurrent_rollout_enabled` option (disabled by default) that makes use of rollout-operator to speed up the rollout of compactors. #7783 #7878
* [ENHANCEMENT] Shuffle-sharding: add `$._config.shuffle_sharding.ingest_storage_partitions_enabled` and `$._config.shuffle_sharding.ingester_partitions_shard_size` options, that allow configuring partitions shard size in ingest-storage mode. #7804
* [ENHANCEMENT] Update rollout-operator to `v0.17.0`. #8399
* [ENHANCEMENT] Add `_config.autoscaling_querier_predictive_scaling_enabled` to scale querier based on inflight queries 7 days ago. #7775
* [ENHANCEMENT] Add support to autoscale ruler-querier replicas based on in-flight queries too (in addition to CPU and memory based scaling). #8060 #8188
* [ENHANCEMENT] Distributor: improved distributor HPA scaling metric to only take in account ready pods. This requires the metric `kube_pod_status_ready` to be available in the data source used by KEDA to query scaling metrics (configured via `_config.autoscaling_prometheus_url`). #8251
* [BUGFIX] Guard against missing samples in KEDA queries. #7691

### Mimirtool

* [CHANGE] Deprecated `--rule-files` flag in favor of CLI arguments. #7756
* [FEATURE] mimirtool: Add `runtime-config verify` sub-command, for verifying Mimir runtime config files. #8123
* [ENHANCEMENT] `mimirtool promql format`: Format PromQL query with Prometheus' string or pretty-print formatter. #7742
* [ENHANCEMENT] Add `mimir-http-prefix` configuration to set the Mimir URL prefix when using legacy routes. #8069
* [ENHANCEMENT] Add option `--output-dir` to `mimirtool rules get` and `mimirtool rules print` to allow persisting rule groups to a file for edit and re-upload. #8142
* [BUGFIX] Fix panic in `loadgen` subcommand. #7629
* [BUGFIX] `mimirtool rules prepare`: do not add aggregation label to `on()` clause if already present in `group_left()` or `group_right()`. #7839
* [BUGFIX] Analyze Grafana: fix parsing queries with variables. #8062
* [BUGFIX] `mimirtool rules sync`: detect a change when the `query_offset` or the deprecated `evaluation_delay` configuration changes. #8297

### Mimir Continuous Test

* [CHANGE] `mimir-continuous-test` has been deprecated and replaced by a Mimir module that can be run as a target from the `mimir` binary using `mimir -target=continuous-test`. #7753
* [CHANGE] `-server.metrics-port` flag is no longer available for use in the module run of mimir-continuous-test, including the grafana/mimir-continuous-test Docker image which uses the new module. Configuring this port is still possible in the binary, which is deprecated. #7747
* [CHANGE] Allowed authenticatication to Mimir using both Tenant ID and basic/bearer auth #7619.
* [BUGFIX] Set `User-Agent` header for all requests sent from the testing client. #7607

### Query-tee

* [ENHANCEMENT] Log queries that take longer than `proxy.log-slow-query-response-threshold` when compared to other backends. #7346
* [ENHANCEMENT] Add two new metrics for measuring the relative duration between backends: #7782 #8013 #8330
  * `cortex_querytee_backend_response_relative_duration_seconds`
  * `cortex_querytee_backend_response_relative_duration_proportional`

### Documentation

* [ENHANCEMENT] Clarify Compactor and its storage volume when configured under Kubernetes. #7675
* [ENHANCEMENT] Add OTLP route to _Mimir routes by path_ runbooks section. #8074
* [ENHANCEMENT] Document option server.log-source-ips-full. #8268

### Tools

* [ENHANCEMENT] ulidtime: add option to show random part of ULID, timestamp in milliseconds and header. #7615
* [ENHANCEMENT] copyblocks: add a flag to configure part-size for multipart uploads in s3 client-side copying. #8292
* [ENHANCEMENT] copyblocks: enable pprof HTTP endpoints. #8292


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.12.0...mimir-2.13.0


================================================================================

# 2.13.1

Tag: mimir-2.13.1
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.13.1

This release contains 9 PRs from 4 authors. Thank you!

# Changelog

## 2.13.1

### Grafana Mimir

* [BUGFIX] Upgrade Go to 1.22.9 to address [CVE-2024-34156](https://nvd.nist.gov/vuln/detail/CVE-2024-34156). #10097
* [BUGFIX] Update module google.golang.org/grpc to v1.64.1 to address [GHSA-xr7q-jx4m-x55m](https://github.com/advisories/GHSA-xr7q-jx4m-x55m). #8717
* [BUGFIX] Upgrade github.com/rs/cors to v1.11.0 address [GHSA-mh55-gqvf-xfwm](https://github.com/advisories/GHSA-mh55-gqvf-xfwm). #8611


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.13.0...mimir-2.13.1


================================================================================

# 2.14.0

Tag: mimir-2.14.0
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.14.0

This release contains 599 PRs from 66 authors, including new contributors Adrian Berger, Albert Kerr, Alexander Davis, Alyssa Wada, Aofei Sheng, Bailhache Pierre, Bradley, David Stevens, Davin Kevin, Dennis Haney, Felipe Ferreira, Jeongseup, Nicholas Kress, Paul Farver, Pooya, Rajguru, Sephia Laureencia, Sviat Loginov, Taehyun Kim, Taylor C, Tito Lins, Willem Gillis, William Travis Holton, William Wernert, Yuri Tseretyan. Thank you!

# Grafana Mimir version 2.14.0 release notes

Grafana Labs is excited to announce version 2.14 of Grafana Mimir.

The highlights that follow include the top features, enhancements, and bug fixes in this release. For the complete list of changes, refer to the [CHANGELOG](https://github.com/grafana/mimir/blob/main/CHANGELOG.md).

## Features and enhancements

The streaming of chunks from store-gateways to queriers is now enabled by default. This reduces the memory usage in queriers. This was an experimental feature since Mimir 2.10, and is now considered stable.

Compactor adds a new `cortex_compactor_disk_out_of_space_errors_total` counter metric that tracks how many times a compaction fails due to the compactor being out of disk.

The distributor now replies with the `Retry-After` header on retriable errors by default. This protects Mimir from clients, including Prometheus, that default to retrying very quickly, making recovering from an outage easier. The feature was originally added as experimental in Mimir 2.11.

Incoming OTLP requests were previously size-limited with the distributor's `-distributor.max-recv-msg-size` configuration.
The distributor has a new `-distributor.max-otlp-request-size` configuration for limiting OTLP requests. The default value is 100 MiB.

Ingesters can be marked as read-only as part of their downscaling procedure. The new `prepare-instance-ring-downscale` endpoint updates the read-only status of an ingester in the ring.

## Important changes

In Grafana Mimir 2.14, the following behavior has changed:

When running a remote read request, the querier honors the time range specified in the read hints.

The default inactivity timeout of active series in ingesters, controlled by the `-ingester.active-series-metrics-idle-timeout` configuration, is increased from `10m` to `20m`.

The following features of store-gateway are changed: `-blocks-storage.bucket-store.max-concurrent-queue-timeout` is set to five seconds; `-blocks-storage.bucket-store.index-header.lazy-loading-concurrency-queue-timeout` is set to five seconds; `-blocks-storage.bucket-store.max-concurrent` is set to 200;

The experimental support for Redis caching is now deprecated and set to be removed in the next major release. Users are encouraged
to switch to use Memcached.

The following deprecated configuration options were removed in this release:

- The `-ingester.return-only-grpc-errors` option in the ingester
- The `-ingester.client.circuit-breaker.*` options in the ingester
- The `-ingester.limit-inflight-requests-using-grpc-method-limiter` option in the ingester
- The `-ingester.client.report-grpc-codes-in-instrumentation-label-enabled` option in the distributor and ruler
- The `-distributor.limit-inflight-requests-using-grpc-method-limiter` option in the distributor
- The `-distributor.enable-otlp-metadata-storage` option in the distributor
- The `-ruler.drain-notification-queue-on-shutdown` option in the ruler
- The `-querier.max-query-into-future` option in the querier
- The `-querier.prefer-streaming-chunks-from-store-gateways` option in the querier and the store-gateway
- The `-query-scheduler.use-multi-algorithm-query-queue` option in the querier-scheduler
- The YAML configuration `frontend.align_queries_with_step` in the query-frontend

## Experimental features

Grafana Mimir 2.14 includes some features that are experimental and disabled by default. Use these features with caution and report any issues that you encounter:

The ingester added an experimental `-ingester.ignore-ooo-exemplars` configuration. When set, out-of-order exemplars are no longer reported to the remote write client.

The querier supports the experimental `limitk()` and `limit_ratio()` PromQL functions. This feature is disabled by default, but you can enable it with the `-querier.promql-experimental-functions-enabled=true` setting in the query-frontend and the querier.

## Bug fixes

- Alertmanager: fix configuration validation gap around unreferenced templates.
- Alertmanager: fix goroutine leak when stored configuration fails to apply and there is no existing tenant alertmanager.
- Alertmanager: fix receiver firewall to detect `0.0.0.0` and IPv6 interface-local multicast address as local addresses.
- Alertmanager: fix per-tenant silence limits not reloaded during runtime.
- Alertmanager: fix bugs in silences that could cause an existing silence to expire/be deleted when updating the silence fails. This could happen when the updated silence was invalid or exceeded limits.
- Alertmanager: fix help message for utf-8-strict-mode.
- Compactor: fix a race condition between different compactor replicas that may cause a deleted block to be referenced as non-deleted in the bucket index.
- Configuration: multi-line environment variables are flattened during injection to be compatible with YAML syntax.
- HA Tracker: store correct timestamp for the last-received request from the elected replica.
- Ingester: fix the sporadic `not found` error causing an internal server error if label names are queried with matchers during head compaction.
- Ingester, store-gateway: fix case insensitive regular expressions not correctly matching some Unicode characters.
- Ingester: fixed timestamp reported in the "the sample has been rejected because its timestamp is too old" error when the write request contains only histograms.
- Query-frontend: fix `-querier.max-query-lookback` and `-compactor.blocks-retention-period` enforcement in query-frontend when one of the two is not set.
- Query-frontend: "query stats" log includes the actual `status_code` when the request fails due to an error occurring in the query-frontend itself.
- Query-frontend: ensure that internal errors result in an HTTP 500 response code instead of a 422 response code.
- Query-frontend: return annotations generated during evaluation of sharded queries.
- Query-scheduler: fix a panic in request queueing.
- Querier: fix the issue where "context canceled" is logged for trace spans for requests to store-gateways that return no series when chunks streaming is enabled.
- Querier: fix issue where queries can return incorrect results if a single store-gateway returns overlapping chunks for a series.
- Querier: do not return `grpc: the client connection is closing` errors as HTTP `499`.
- Querier: fix issue where some native histogram-related warnings were not emitted when `rate()` was used over native histograms.
- Querier: fix invalid query results when multiple chunks are merged.
- Querier: support optional start and end times on `/prometheus/api/v1/labels`, `/prometheus/api/v1/label/<label>/values`, and `/prometheus/api/v1/series` when `max_query_into_future: 0`.
- Querier: fix issue where both recently compacted blocks and their source blocks can be skipped during querying if store-gateways are restarting.
- Ruler: add support for draining any outstanding alert notifications before shutting down. Enable this setting with the `-ruler.drain-notification-queue-on-shutdown=true` CLI flag.
- Store-gateway: fixed a case where, on a quick subsequent restart, the previous lazy-loaded index header snapshot was overwritten by a partially loaded one.
- Store-gateway: store sparse index headers atomically to disk.
- Ruler: map invalid org-id errors to the 400 status code.

### Helm chart improvements

The Grafana Mimir and Grafana Enterprise Metrics Helm charts are released independently. Refer to the [Grafana Mimir Helm chart documentation](/docs/helm-charts/mimir-distributed/latest/).

# Changelog

## 2.14.0

### Grafana Mimir

* [CHANGE] Update minimal supported version of Go to 1.22. #9134
* [CHANGE] Store-gateway / querier: enable streaming chunks from store-gateways to queriers by default. #6646
* [CHANGE] Querier: honor the start/end time range specified in the read hints when executing a remote read request. #8431
* [CHANGE] Querier: return only samples within the queried start/end time range when executing a remote read request using "SAMPLES" mode. Previously, samples outside of the range could have been returned. Samples outside of the queried time range may still be returned when executing a remote read request using "STREAMED_XOR_CHUNKS" mode. #8463
* [CHANGE] Querier: Set minimum for `-querier.max-concurrent` to four to prevent queue starvation with querier-worker queue prioritization algorithm; values below the minimum four are ignored and set to the minimum. #9054
* [CHANGE] Store-gateway: enabled `-blocks-storage.bucket-store.max-concurrent-queue-timeout` by default with a timeout of 5 seconds. #8496
* [CHANGE] Store-gateway: enabled `-blocks-storage.bucket-store.index-header.lazy-loading-concurrency-queue-timeout` by default with a timeout of 5 seconds . #8667
* [CHANGE] Distributor: Incoming OTLP requests were previously size-limited by using limit from `-distributor.max-recv-msg-size` option. We have added option `-distributor.max-otlp-request-size` for limiting OTLP requests, with default value of 100 MiB. #8574
* [CHANGE] Distributor: remove metric `cortex_distributor_sample_delay_seconds`. #8698
* [CHANGE] Query-frontend: Remove deprecated `frontend.align_queries_with_step` YAML configuration. The configuration option has been moved to per-tenant and default `limits` since Mimir 2.12. #8733 #8735
* [CHANGE] Store-gateway: Change default of `-blocks-storage.bucket-store.max-concurrent` to 200. #8768
* [CHANGE] Added new metric `cortex_compactor_disk_out_of_space_errors_total` which counts how many times a compaction failed due to the compactor being out of disk, alert if there is a single increase. #8237 #8278
* [CHANGE] Store-gateway: Remove experimental parameter `-blocks-storage.bucket-store.series-selection-strategy`. The default strategy is now `worst-case`. #8702
* [CHANGE] Store-gateway: Rename `-blocks-storage.bucket-store.series-selection-strategies.worst-case-series-preference` to `-blocks-storage.bucket-store.series-fetch-preference` and promote to stable. #8702
* [CHANGE] Querier, store-gateway: remove deprecated `-querier.prefer-streaming-chunks-from-store-gateways=true`. Streaming from store-gateways is now always enabled. #8696
* [CHANGE] Ingester: remove deprecated `-ingester.return-only-grpc-errors`. #8699 #8828
* [CHANGE] Distributor, ruler: remove deprecated `-ingester.client.report-grpc-codes-in-instrumentation-label-enabled`. #8700
* [CHANGE] Ingester client: experimental support for client-side circuit breakers, their configuration options (`-ingester.client.circuit-breaker.*`) and metrics (`cortex_ingester_client_circuit_breaker_results_total`, `cortex_ingester_client_circuit_breaker_transitions_total`) were removed. #8802
* [CHANGE] Ingester: circuit breakers do not open in case of per-instance limit errors anymore. Opening can be triggered only in case of push and pull requests exceeding the configured duration. #8854
* [CHANGE] Query-frontend: Return `413 Request Entity Too Large` if a response shard for an `/active_series` request is too large. #8861
* [CHANGE] Distributor: Promote replying with `Retry-After` header on retryable errors to stable and set `-distributor.retry-after-header.enabled=true` by default. #8694
* [CHANGE] Distributor: Replace `-distributor.retry-after-header.max-backoff-exponent` and `-distributor.retry-after-header.base-seconds` with `-distributor.retry-after-header.min-backoff` and `-distributor.retry-after-header.max-backoff` for easier configuration. #8694
* [CHANGE] Ingester: increase the default inactivity timeout of active series (`-ingester.active-series-metrics-idle-timeout`) from `10m` to `20m`. #8975
* [CHANGE] Distributor: Remove `-distributor.enable-otlp-metadata-storage` flag, which was deprecated in version 2.12. #9069
* [CHANGE] Ruler: Removed `-ruler.drain-notification-queue-on-shutdown` option, which is now enabled by default. #9115
* [CHANGE] Querier: allow wrapping errors with context errors only when the former actually correspond to `context.Canceled` and `context.DeadlineExceeded`. #9175
* [CHANGE] Query-scheduler: Remove the experimental `-query-scheduler.use-multi-algorithm-query-queue` flag. The new multi-algorithm tree queue is always used for the scheduler. #9210
* [CHANGE] Distributor: reject incoming requests until the distributor service has started. #9317
* [CHANGE] Ingester, Distributor: Remove deprecated `-ingester.limit-inflight-requests-using-grpc-method-limiter` and `-distributor.limit-inflight-requests-using-grpc-method-limiter`. The feature was deprecated and enabled by default in Mimir 2.12. #9407
* [CHANGE] Querier: Remove deprecated `-querier.max-query-into-future`. The feature was deprecated in Mimir 2.12. #9407
* [CHANGE] Cache: Deprecate experimental support for Redis as a cache backend. The support is set to be removed in the next major release. #9453
* [FEATURE] Alertmanager: Added `-alertmanager.log-parsing-label-matchers` to control logging when parsing label matchers. This flag is intended to be used with `-alertmanager.utf8-strict-mode-enabled` to validate UTF-8 strict mode is working as intended. The default value is `false`. #9173
* [FEATURE] Alertmanager: Added `-alertmanager.utf8-migration-logging-enabled` to enable logging of tenant configurations that are incompatible with UTF-8 strict mode. The default value is `false`. #9174
* [FEATURE] Querier: add experimental streaming PromQL engine, enabled with `-querier.query-engine=mimir`. #8422 #8430 #8454 #8455 #8360 #8490 #8508 #8577 #8660 #8671 #8677 #8747 #8850 #8872 #8838 #8911 #8909 #8923 #8924 #8925 #8932 #8933 #8934 #8962 #8986 #8993 #8995 #9008 #9017 #9018 #9019 #9120 #9121 #9136 #9139 #9140 #9145 #9191 #9192 #9194 #9196 #9201 #9212 #9225 #9260 #9272 #9277 #9278 #9280 #9281 #9342 #9343 #9371
* [FEATURE] Experimental Kafka-based ingest storage. #6888 #6894 #6929 #6940 #6951 #6974 #6982 #7029 #7030 #7091 #7142 #7147 #7148 #7153 #7160 #7193 #7349 #7376 #7388 #7391 #7393 #7394 #7402 #7404 #7423 #7424 #7437 #7486 #7503 #7508 #7540 #7621 #7682 #7685 #7694 #7695 #7696 #7697 #7701 #7733 #7734 #7741 #7752 #7838 #7851 #7871 #7877 #7880 #7882 #7887 #7891 #7925 #7955 #7967 #8031 #8063 #8077 #8088 #8135 #8176 #8184 #8194 #8216 #8217 #8222 #8233 #8503 #8542 #8579 #8657 #8686 #8688 #8703 #8706 #8708 #8738 #8750 #8778 #8808 #8809 #8841 #8842 #8845 #8853 #8886 #8988
  * What it is:
    * When the new ingest storage architecture is enabled, distributors write incoming write requests to a Kafka-compatible backend, and the ingesters asynchronously replay ingested data from Kafka. In this architecture, the write and read path are de-coupled through a Kafka-compatible backend. The write path and Kafka load is a function of the incoming write traffic, the read path load is a function of received queries. Whatever the load on the read path, it doesn't affect the write path.
  * New configuration options:
    * `-ingest-storage.enabled`
    * `-ingest-storage.kafka.*`: configures Kafka-compatible backend and how clients interact with it.
    * `-ingest-storage.ingestion-partition-tenant-shard-size`: configures the per-tenant shuffle-sharding shard size used by partitions ring.
    * `-ingest-storage.read-consistency`: configures the default read consistency.
    * `-ingest-storage.migration.distributor-send-to-ingesters-enabled`: enabled tee-ing writes to classic ingesters and Kafka, used during a live migration to the new ingest storage architecture.
    * `-ingester.partition-ring.*`: configures partitions ring backend.
* [FEATURE] Querier: added support for `limitk()` and `limit_ratio()` experimental PromQL functions. Experimental functions are disabled by default, but can be enabled setting `-querier.promql-experimental-functions-enabled=true` in the query-frontend and querier. #8632
* [FEATURE] Querier: experimental support for `X-Mimir-Chunk-Info-Logger` header that triggers logging information about TSDB chunks loaded from ingesters and store-gateways in the querier. The header should contain the comma separated list of labels for which their value will be included in the logs. #8599
* [FEATURE] Query frontend: added new query pruning middleware to enable pruning dead code (eg. expressions that cannot produce any results) and simplifying expressions (eg. expressions that can be evaluated immediately) in queries. #9086
* [FEATURE] Ruler: added experimental configuration, `-ruler.rule-evaluation-write-enabled`, to disable writing the result of rule evaluation to ingesters. This feature can be used for testing purposes. #9060
* [FEATURE] Ingester: added experimental configuration `ingester.ignore-ooo-exemplars`. When set to `true` out of order exemplars are no longer reported to the remote write client. #9151
* [ENHANCEMENT] Compactor: Add `cortex_compactor_compaction_job_duration_seconds` and `cortex_compactor_compaction_job_blocks` histogram metrics to track duration of individual compaction jobs and number of blocks per job. #8371
* [ENHANCEMENT] Rules: Added per namespace max rules per rule group limit. The maximum number of rules per rule groups for all namespaces continues to be configured by `-ruler.max-rules-per-rule-group`, but now, this can be superseded by the new `-ruler.max-rules-per-rule-group-by-namespace` option on a per namespace basis. This new limit can be overridden using the overrides mechanism to be applied per-tenant. #8378
* [ENHANCEMENT] Rules: Added per namespace max rule groups per tenant limit. The maximum number of rule groups per rule tenant for all namespaces continues to be configured by `-ruler.max-rule-groups-per-tenant`, but now, this can be superseded by the new `-ruler.max-rule-groups-per-tenant-by-namespace` option on a per namespace basis. This new limit can be overridden using the overrides mechanism to be applied per-tenant. #8425
* [ENHANCEMENT] Ruler: Added support to protect rules namespaces from modification. The `-ruler.protected-namespaces` flag can be used to specify namespaces that are protected from rule modifications. The header `X-Mimir-Ruler-Override-Namespace-Protection` can be used to override the protection. #8444
* [ENHANCEMENT] Query-frontend: be able to block remote read queries via the per tenant runtime override `blocked_queries`. #8372 #8415
* [ENHANCEMENT] Query-frontend: added `remote_read` to `op` supported label values for the `cortex_query_frontend_queries_total` metric. #8412
* [ENHANCEMENT] Query-frontend: log the overall length and start, end time offset from current time for remote read requests. The start and end times are calculated as the miminum and maximum times of the individual queries in the remote read request. #8404
* [ENHANCEMENT] Storage Provider: Added option `-<prefix>.s3.dualstack-enabled` that allows disabling S3 client from resolving AWS S3 endpoint into dual-stack IPv4/IPv6 endpoint. Defaults to true. #8405
* [ENHANCEMENT] HA Tracker: Added reporting of most recent elected replica change via `cortex_ha_tracker_last_election_timestamp_seconds` gauge, logging, and a new column in the HA Tracker status page. #8507
* [ENHANCEMENT] Use sd_notify to send events to systemd at start and stop of mimir services. Default systemd mimir.service config now wait for those events with a configurable timeout `TimeoutStartSec` default is 3 min to handle long start time (ex. store-gateway). #8220 #8555 #8658
* [ENHANCEMENT] Alertmanager: Reloading config and templates no longer needs to hit the disk. #4967
* [ENHANCEMENT] Compactor: Added experimental `-compactor.in-memory-tenant-meta-cache-size` option to set size of in-memory cache (in number of items) for parsed meta.json files. This can help when a tenant has many meta.json files and their parsing before each compaction cycle is using a lot of CPU time. #8544
* [ENHANCEMENT] Distributor: Interrupt OTLP write request translation when context is canceled or has timed out. #8524
* [ENHANCEMENT] Ingester, store-gateway: optimised regular expression matching for patterns like `1.*|2.*|3.*|...|1000.*`. #8632
* [ENHANCEMENT] Query-frontend: Add `header_cache_control` to query stats. #8590
* [ENHANCEMENT] Query-scheduler: Introduce `query-scheduler.use-multi-algorithm-query-queue`, which allows use of an experimental queue structure, with no change in external queue behavior. #7873
* [ENHANCEMENT] Query-scheduler: Improve CPU/memory performance of experimental query-scheduler. #8871
* [ENHANCEMENT] Expose a new `s3.trace.enabled` configuration option to enable detailed logging of operations against S3-compatible object stores. #8690
* [ENHANCEMENT] memberlist: locally-generated messages (e.g. ring updates) are sent to gossip network before forwarded messages. Introduced `-memberlist.broadcast-timeout-for-local-updates-on-shutdown` option to modify how long to wait until queue with locally-generated messages is empty when shutting down. Previously this was hard-coded to 10s, and wait included all messages (locally-generated and forwarded). Now it defaults to 10s, 0 means no timeout. Increasing this value may help to avoid problem when ring updates on shutdown are not propagated to other nodes, and ring entry is left in a wrong state. #8761
* [ENHANCEMENT] Querier: allow using both raw numbers of seconds and duration literals in queries where previously only one or the other was permitted. For example, `predict_linear` now accepts a duration literal (eg. `predict_linear(..., 4h)`), and range vector selectors now accept a number of seconds (eg. `rate(metric[2])`). #8780
* [ENHANCEMENT] Ruler: Add `ruler.max-independent-rule-evaluation-concurrency` to allow independent rules of a tenant to be run concurrently. You can control the amount of concurrency per tenant is controlled via the `-ruler.max-independent-rule-evaluation-concurrency-per-tenan` as a limit. Use a `-ruler.max-independent-rule-evaluation-concurrency` value of `0` can be used to disable the feature for all tenants. By default, this feature is disabled. A rule is eligible for concurrency as long as it doesn't depend on any other rules, doesn't have any other rules that depend on it, and has a total rule group runtime that exceeds 50% of its interval by default. The threshold can can be adjusted with `-ruler.independent-rule-evaluation-concurrency-min-duration-percentage`. #8146 #8858 #8880 #8884
  * This work introduces the following metrics:
    * `cortex_ruler_independent_rule_evaluation_concurrency_slots_in_use`
    * `cortex_ruler_independent_rule_evaluation_concurrency_attempts_started_total`
    * `cortex_ruler_independent_rule_evaluation_concurrency_attempts_incomplete_total`
    * `cortex_ruler_independent_rule_evaluation_concurrency_attempts_completed_total`
* [ENHANCEMENT] Expose a new `s3.session-token` configuration option to enable using temporary security credentials. #8952
* [ENHANCEMENT] Add HA deduplication features to the `mimir-microservices-mode` development environment. #9012
* [ENHANCEMENT] Remove experimental `-query-frontend.additional-query-queue-dimensions-enabled` and `-query-scheduler.additional-query-queue-dimensions-enabled`. Mimir now always includes "query components" as a queue dimension. #8984 #9135
* [ENHANCEMENT] Add a new ingester endpoint to prepare instances to downscale. #8956
* [ENHANCEMENT] Query-scheduler: Add `query-scheduler.prioritize-query-components` which, when enabled, will primarily prioritize dequeuing fairly across queue components, and secondarily prioritize dequeuing fairly across tenants. When disabled, tenant fairness is primarily prioritized. `query-scheduler.use-multi-algorithm-query-queue` must be enabled in order to use this flag. #9016 #9071
* [ENHANCEMENT] Update runtime configuration to read gzip-compressed files with `.gz` extension. #9074
* [ENHANCEMENT] Ingester: add `cortex_lifecycler_read_only` metric which is set to 1 when ingester's lifecycler is set to read-only mode. #9095
* [ENHANCEMENT] Add a new field, `encode_time_seconds` to query stats log messages, to record the amount of time it takes the query-frontend to encode a response. This does not include any serialization time for downstream components. #9062
* [ENHANCEMENT] OTLP: If the flag `-distributor.otel-created-timestamp-zero-ingestion-enabled` is true, OTel start timestamps are converted to Prometheus zero samples to mark series start. #9131
* [ENHANCEMENT] Querier: attach logs emitted during query consistency check to trace span for query. #9213
* [ENHANCEMENT] Query-scheduler: Experimental `-query-scheduler.prioritize-query-components` flag enables the querier-worker queue priority algorithm to take precedence over tenant rotation when dequeuing requests. #9220
* [ENHANCEMENT] Add application credential arguments for Openstack Swift storage backend. #9181
* [BUGFIX] Ruler: add support for draining any outstanding alert notifications before shutting down. This can be enabled with the `-ruler.drain-notification-queue-on-shutdown=true` CLI flag. #8346
* [BUGFIX] Query-frontend: fix `-querier.max-query-lookback` enforcement when `-compactor.blocks-retention-period` is not set, and viceversa. #8388
* [BUGFIX] Ingester: fix sporadic `not found` error causing an internal server error if label names are queried with matchers during head compaction. #8391
* [BUGFIX] Ingester, store-gateway: fix case insensitive regular expressions not matching correctly some Unicode characters. #8391
* [BUGFIX] Query-frontend: "query stats" log now includes the actual `status_code` when the request fails due to an error occurring in the query-frontend itself. #8407
* [BUGFIX] Store-gateway: fixed a case where, on a quick subsequent restart, the previous lazy-loaded index header snapshot was overwritten by a partially loaded one. #8281
* [BUGFIX] Ingester: fixed timestamp reported in the "the sample has been rejected because its timestamp is too old" error when the write request contains only histograms. #8462
* [BUGFIX] Store-gateway: store sparse index headers atomically to disk. #8485
* [BUGFIX] Query scheduler: fix a panic in request queueing. #8451
* [BUGFIX] Querier: fix issue where "context canceled" is logged for trace spans for requests to store-gateways that return no series when chunks streaming is enabled. #8510
* [BUGFIX] Alertmanager: Fix per-tenant silence limits not reloaded during runtime. #8456
* [BUGFIX] Alertmanager: Fixes a number of bugs in silences which could cause an existing silence to be deleted/expired when updating the silence failed. This could happen when the replacing silence was invalid or exceeded limits. #8525
* [BUGFIX] Alertmanager: Fix help message for utf-8-strict-mode. #8572
* [BUGFIX] Query-frontend: Ensure that internal errors result in an HTTP 500 response code instead of 422. #8595 #8666
* [BUGFIX] Configuration: Multi line envs variables are flatten during injection to be compatible with YAML syntax
* [BUGFIX] Querier: fix issue where queries can return incorrect results if a single store-gateway returns overlapping chunks for a series. #8827
* [BUGFIX] HA Tracker: store correct timestamp for last received request from elected replica. #8821
* [BUGFIX] Querier: do not return `grpc: the client connection is closing` errors as HTTP `499`. #8865 #8888
* [BUGFIX] Compactor: fix a race condition between different compactor replicas that may cause a deleted block to be still referenced as non-deleted in the bucket index. #8905
* [BUGFIX] Querier: fix issue where some native histogram-related warnings were not emitted when `rate()` was used over native histograms. #8918
* [BUGFIX] Ruler: map invalid org-id errors to 400 status code. #8935
* [BUGFIX] Querier: Fix invalid query results when multiple chunks are being merged. #8992
* [BUGFIX] Query-frontend: return annotations generated during evaluation of sharded queries. #9138
* [BUGFIX] Querier: Support optional start and end times on `/prometheus/api/v1/labels`, `/prometheus/api/v1/label/<label>/values`, and `/prometheus/api/v1/series` when `max_query_into_future: 0`. #9129
* [BUGFIX] Alertmanager: Fix config validation gap around unreferenced templates. #9207
* [BUGFIX] Alertmanager: Fix goroutine leak when stored config fails to apply and there is no existing tenant alertmanager #9211
* [BUGFIX] Querier: fix issue where both recently compacted blocks and their source blocks can be skipped during querying if store-gateways are restarting. #9224
* [BUGFIX] Alertmanager: fix receiver firewall to detect `0.0.0.0` and IPv6 interface-local multicast address as local addresses. #9308

### Mixin

* [CHANGE] Dashboards: set default auto-refresh rate to 5m. #8758
* [ENHANCEMENT] Dashboards: allow switching between using classic or native histograms in dashboards.
  * Overview dashboard: status, read/write latency and queries/ingestion per sec panels, `cortex_request_duration_seconds` metric. #7674 #8502 #8791
  * Writes dashboard: `cortex_request_duration_seconds` metric. #8757 #8791
  * Reads dashboard: `cortex_request_duration_seconds` metric. #8752
  * Rollout progress dashboard: `cortex_request_duration_seconds` metric. #8779
  * Alertmanager dashboard: `cortex_request_duration_seconds` metric. #8792
  * Ruler dashboard: `cortex_request_duration_seconds` metric. #8795
  * Queries dashboard: `cortex_request_duration_seconds` metric. #8800
  * Remote ruler reads dashboard: `cortex_request_duration_seconds` metric. #8801
* [ENHANCEMENT] Alerts: `MimirRunningIngesterReceiveDelayTooHigh` alert has been tuned to be more reactive to high receive delay. #8538
* [ENHANCEMENT] Dashboards: improve end-to-end latency and strong read consistency panels when experimental ingest storage is enabled. #8543 #8830
* [ENHANCEMENT] Dashboards: Add panels for monitoring ingester autoscaling when not using ingest-storage. These panels are disabled by default, but can be enabled using the `autoscaling.ingester.enabled: true` config option. #8484
* [ENHANCEMENT] Dashboards: Add panels for monitoring store-gateway autoscaling. These panels are disabled by default, but can be enabled using the `autoscaling.store_gateway.enabled: true` config option. #8824
* [ENHANCEMENT] Dashboards: add panels to show writes to experimental ingest storage backend in the "Mimir / Ruler" dashboard, when `_config.show_ingest_storage_panels` is enabled. #8732
* [ENHANCEMENT] Dashboards: show all series in tooltips on time series dashboard panels. #8748
* [ENHANCEMENT] Dashboards: add compactor autoscaling panels to "Mimir / Compactor" dashboard. The panels are disabled by default, but can be enabled setting `_config.autoscaling.compactor.enabled` to `true`. #8777
* [ENHANCEMENT] Alerts: added `MimirKafkaClientBufferedProduceBytesTooHigh` alert. #8763
* [ENHANCEMENT] Dashboards: added "Kafka produced records / sec" panel to "Mimir / Writes" dashboard. #8763
* [ENHANCEMENT] Alerts: added `MimirStrongConsistencyOffsetNotPropagatedToIngesters` alert, and rename `MimirIngesterFailsEnforceStrongConsistencyOnReadPath` alert to `MimirStrongConsistencyEnforcementFailed`. #8831
* [ENHANCEMENT] Dashboards: remove "All" option for namespace dropdown in dashboards. #8829
* [ENHANCEMENT] Dashboards: add Kafka end-to-end latency outliers panel in the "Mimir / Writes" dashboard. #8948
* [ENHANCEMENT] Dashboards: add "Out-of-order samples appended" panel to "Mimir / Tenants" dashboard. #8939
* [ENHANCEMENT] Alerts: `RequestErrors` and `RulerRemoteEvaluationFailing` have been enriched with a native histogram version. #9004
* [ENHANCEMENT] Dashboards: add 'Read path' selector to 'Mimir / Queries' dashboard. #8878
* [ENHANCEMENT] Dashboards: add annotation indicating active series are being reloaded to 'Mimir / Tenants' dashboard. #9257
* [ENHANCEMENT] Dashboards: limit results on the 'Failed evaluations rate' panel of the 'Mimir / Tenants' dashboard to 50 to avoid crashing the page when there are many failing groups. #9262
* [FEATURE] Alerts: add `MimirGossipMembersEndpointsOutOfSync` alert. #9347
* [BUGFIX] Dashboards: fix "current replicas" in autoscaling panels when HPA is not active. #8566
* [BUGFIX] Alerts: do not fire `MimirRingMembersMismatch` during the migration to experimental ingest storage. #8727
* [BUGFIX] Dashboards: avoid over-counting of ingesters metrics when migrating to experimental ingest storage. #9170
* [BUGFIX] Dashboards: fix `job_prefix` not utilized in `jobSelector`. #9155

### Jsonnet

* [CHANGE] Changed the following config options when the experimental ingest storage is enabled: #8874
  * `ingest_storage_ingester_autoscaling_min_replicas` changed to `ingest_storage_ingester_autoscaling_min_replicas_per_zone`
  * `ingest_storage_ingester_autoscaling_max_replicas` changed to `ingest_storage_ingester_autoscaling_max_replicas_per_zone`
* [CHANGE] Changed the overrides configmap generation to remove any field with `null` value. #9116
* [CHANGE] `$.replicaTemplate` function now takes replicas and labelSelector parameter. #9248
* [CHANGE] Renamed `ingest_storage_ingester_autoscaling_replica_template_custom_resource_definition_enabled` to `replica_template_custom_resource_definition_enabled`. #9248
* [FEATURE] Add support for automatically deleting compactor, store-gateway, ingester and read-write mode backend PVCs when the corresponding StatefulSet is scaled down. #8382 #8736
* [FEATURE] Automatically set GOMAXPROCS on ingesters. #9273
* [ENHANCEMENT] Added the following config options to set the number of partition ingester replicas when migrating to experimental ingest storage. #8517
  * `ingest_storage_migration_partition_ingester_zone_a_replicas`
  * `ingest_storage_migration_partition_ingester_zone_b_replicas`
  * `ingest_storage_migration_partition_ingester_zone_c_replicas`
* [ENHANCEMENT] Distributor: increase `-distributor.remote-timeout` when the experimental ingest storage is enabled. #8518
* [ENHANCEMENT] Memcached: Update to Memcached 1.6.28 and memcached-exporter 0.14.4. #8557
* [ENHANCEMENT] Rollout-operator: Allow the rollout-operator to be used as Kubernetes statefulset webhook to enable `no-downscale` and `prepare-downscale` annotations to be used on ingesters or store-gateways. #8743
* [ENHANCEMENT] Do not deploy ingester-zone-c when experimental ingest storage is enabled and `ingest_storage_ingester_zones` is configured to `2`. #8776
* [ENHANCEMENT] Added the config option `ingest_storage_migration_classic_ingesters_no_scale_down_delay` to disable the downscale delay on classic ingesters when migrating to experimental ingest storage. #8775 #8873
* [ENHANCEMENT] Configure experimental ingest storage on query-frontend too when enabled. #8843
* [ENHANCEMENT] Allow to override Kafka client ID on a per-component basis. #9026
* [ENHANCEMENT] Rollout-operator's access to ReplicaTemplate is now configured via config option `rollout_operator_replica_template_access_enabled`. #9252
* [ENHANCEMENT] Added support for new way of downscaling ingesters, using rollout-operator's resource-mirroring feature and read-only mode of ingesters. This can be enabled by using `ingester_automated_downscale_v2_enabled` config option. This is mutually exclusive with both `ingester_automated_downscale_enabled` (previous downscale mode) and `ingest_storage_ingester_autoscaling_enabled` (autoscaling for ingest-storage).
* [ENHANCEMENT] Update rollout-operator to `v0.19.1`. #9388
* [BUGFIX] Added missing node affinity matchers to write component. #8910

### Mimirtool

* [CHANGE] Analyze Rules: Count recording rules used in rules group as used. #6133
* [CHANGE] Remove deprecated `--rule-files` flag in favor of CLI arguments for the following commands: #8701
  * `mimirtool rules load`
  * `mimirtool rules sync`
  * `mimirtool rules diff`
  * `mimirtool rules check`
  * `mimirtool rules prepare`
* [ENHANCEMENT] Remote read and backfill now supports the experimental native histograms. #9156

### Mimir Continuous Test

* [CHANGE] Use test metrics that do not pass through 0 to make identifying incorrect results easier. #8630
* [CHANGE] Allowed authentication to Mimir using both Tenant ID and basic/bearer auth. #9038
* [FEATURE] Experimental support for the `-tests.send-chunks-debugging-header` boolean flag to send the `X-Mimir-Chunk-Info-Logger: series_id` header with queries. #8599
* [ENHANCEMENT] Include human-friendly timestamps in diffs logged when a test fails. #8630
* [ENHANCEMENT] Add histograms to measure latency of read and write requests. #8583
* [ENHANCEMENT] Log successful test runs in addition to failed test runs. #8817
* [ENHANCEMENT] Series emitted by continuous-test now distribute more uniformly across ingesters. #9218 #9243
* [ENHANCEMENT] Configure `User-Agent` header for the Mimir client via `-tests.client.user-agent`. #9338
* [BUGFIX] Initialize test result metrics to 0 at startup so that alerts can correctly identify the first failure after startup. #8630

### Query-tee

* [CHANGE] If a preferred backend is configured, then query-tee always returns its response, regardless of the response status code. Previously, query-tee would only return the response from the preferred backend if it did not have a 5xx status code. #8634
* [ENHANCEMENT] Emit trace spans from query-tee. #8419
* [ENHANCEMENT] Log trace ID (if present) with all log messages written while processing a request. #8419
* [ENHANCEMENT] Log user agent when processing a request. #8419
* [ENHANCEMENT] Add `time` parameter to proxied instant queries if it is not included in the incoming request. This is optional but enabled by default, and can be disabled with `-proxy.add-missing-time-parameter-to-instant-queries=false`. #8419
* [ENHANCEMENT] Add support for sending only a proportion of requests to all backends, with the remainder only sent to the preferred backend. The default behaviour is to send all requests to all backends. This can be configured with `-proxy.secondary-backends-request-proportion`. #8532
* [ENHANCEMENT] Check annotations emitted by both backends are the same when comparing responses from two backends. #8660
* [ENHANCEMENT] Compare native histograms in query results when comparing results between two backends. #8724
* [ENHANCEMENT] Don't consider responses to be different during response comparison if both backends' responses contain different series, but all samples are within the recent sample window. #8749 #8894
* [ENHANCEMENT] When the expected and actual response for a matrix series is different, the full set of samples for that series from both backends will now be logged. #8947
* [ENHANCEMENT] Wait up to `-server.graceful-shutdown-timeout` for inflight requests to finish when shutting down, rather than immediately terminating inflight requests on shutdown. #8985
* [ENHANCEMENT] Optionally consider equivalent error messages the same when comparing responses. Enabled by default, disable with `-proxy.require-exact-error-match=true`. #9143 #9350 #9366
* [BUGFIX] Ensure any errors encountered while forwarding a request to a backend (eg. DNS resolution failures) are logged. #8419
* [BUGFIX] The comparison of the results should not fail when either side contains extra samples from within SkipRecentSamples duration. #8920
* [BUGFIX] When `-proxy.compare-skip-recent-samples` is enabled, compare sample timestamps with the time the query requests were made, rather than the time at which the comparison is occurring. #9416

### Documentation

* [ENHANCEMENT] Specify in which component the configuration flags `-compactor.blocks-retention-period`, `-querier.max-query-lookback`, `-query-frontend.max-total-query-length`, `-query-frontend.max-query-expression-size-bytes` are applied and that they are applied to remote read as well. #8433
* [ENHANCEMENT] Provide more detailed recommendations on how to migrate from classic to native histograms. #8864
* [ENHANCEMENT] Clarify that `{namespace}` and `{groupName}` path segments in the ruler config API should be URL-escaped. #8969
* [ENHANCEMENT] Include stalled compactor network drive information in runbooks. #9297
* [ENHANCEMENT] Document `/ingester/prepare-partition-downscale` and `/ingester/prepare-instance-ring-downscale` endpoints. #9132
* [ENHANCEMENT] Describe read-only mode of ingesters in component documentation. #9132

### Tools

* [CHANGE] `wal-reader`: Renamed `-series-entries` to `-print-series`. Renamed `-print-series-with-samples` to `-print-samples`. #8568
* [FEATURE] `query-bucket-index`: add new tool to query a bucket index file and print the blocks that would be used for a given query time range. #8818
* [FEATURE] `kafkatool`: add new CLI tool to operate Kafka. Supported commands: #9000
  * `brokers list-leaders-by-partition`
  * `consumer-group commit-offset`
  * `consumer-group copy-offset`
  * `consumer-group list-offsets`
  * `create-partitions`
* [ENHANCEMENT] `wal-reader`: References to unknown series from Samples, Exemplars, histogram or tombstones records are now always logged. #8568
* [ENHANCEMENT] `tsdb-series`: added `-stats` option to print min/max time of chunks, total number of samples and DPM for each series. #8420
* [ENHANCEMENT] `tsdb-print-chunk`: print counter reset information for native histograms. #8812
* [ENHANCEMENT] `grpcurl-query-ingesters`: print counter reset information for native histograms. #8820
* [ENHANCEMENT] `grpcurl-query-ingesters`: concurrently query ingesters. #9102
* [ENHANCEMENT] `grpcurl-query-ingesters`: sort series and chunks in output. #9180
* [ENHANCEMENT] `grpcurl-query-ingesters`: print full chunk timestamps, not just time component. #9180
* [ENHANCEMENT] `tsdb-series`: Added `-json` option to generate JSON output for easier post-processing. #8844
* [ENHANCEMENT] `tsdb-series`: Added `-min-time` and `-max-time` options to filter samples that are used for computing data-points per minute. #8844
* [ENHANCEMENT] `mimir-rules-action`: Added new input to support matching target namespaces by regex. #9244
* [ENHANCEMENT] `mimir-rules-action`: Added new inputs to support ignoring namespaces and ignoring namespaces by regex. #9258 #9324


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.13.0...mimir-2.14.0


================================================================================

# 2.14.1

Tag: mimir-2.14.1
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.14.1

This release contains 2 PRs from 2 authors. Thank you!

# Changelog

## 2.14.1

### Grafana Mimir

* [BUGFIX] Update objstore library to resolve issues observed for some S3-compatible object stores, which respond to `StatObject` with `Range` incorrectly. #9625


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.14.0...mimir-2.14.1


================================================================================

# 2.14.2

Tag: mimir-2.14.2
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.14.2

This release contains 3 PRs from 2 authors. Thank you!

# Changelog

## 2.14.2

### Grafana Mimir

* [BUGFIX] Query-frontend: Do not break scheduler connection on malformed queries. #9833


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.14.1...mimir-2.14.2


================================================================================

# 2.14.3

Tag: mimir-2.14.3
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.14.3

This release contains 4 PRs from 3 authors. Thank you!

# Changelog

## 2.14.3

### Grafana Mimir

* [BUGFIX] Update `golang.org/x/crypto` to address [CVE-2024-45337](https://github.com/advisories/GHSA-v778-237x-gjrc). #10251
* [BUGFIX] Update `golang.org/x/net` to address [CVE-2024-45338](https://github.com/advisories/GHSA-w32m-9786-jp63). #10298


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.14.2...mimir-2.14.3


================================================================================

# 2.15.0

Tag: mimir-2.15.0
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.15.0

This release contains 487 PRs from 61 authors, including new contributors Alexander Akhmetov, Daan Schipper, Daniel Kovacs, I. Elisa Pasaoglu, Jay Clifford, Jorge Alberto Díaz Orozco (Akiel), Martin Valiente Ainz, Mia, Michael Tweten, Nikos Angelopoulos, Santi Leira, cui fliter, elsoa-invitech, madhu-reddy-peram. Thank you!

# Grafana Mimir version 2.15.0 release notes

Grafana Labs is excited to announce version 2.15 of Grafana Mimir.

The highlights that follow include the top features, enhancements, and bug fixes in this release.
For the complete list of changes, refer to the [CHANGELOG](https://github.com/grafana/mimir/blob/main/CHANGELOG.md).

## Features and enhancements

S2 compression for gRPC is now supported using the following flags:

- `-alertmanager.alertmanager-client.grpc-compression=s2`
- `-ingester.client.grpc-compression=s2`
- `-querier.frontend-client.grpc-compression=s2`
- `-querier.scheduler-client.grpc-compression=s2`
- `-query-frontend.grpc-client-config.grpc-compression=s2`
- `-query-scheduler.grpc-client-config.grpc-compression=s2`
- `-ruler.client.grpc-compression=s2`
- `-ruler.query-frontend.grpc-client-config.grpc-compression=s2`

Distributors now support `lz4` OTLP compression, and you can deploy them in multiple availability zones.

The ruler's `<prometheus-http-prefix>/api/v1/rules` endpoint now supports the `exclude_alerts`, `group_limit`, and `group_next_token` parameters.

mimirtool's `analyze ruler` and `analyze prometheus` commands now support bearer tokens.

You can now tune HTTP client settings for GCS and Azure backends via an `http` block or corresponding CLI flags.

The compactor now refreshes deletion marks concurrently when updating the bucket index.

You can now set the number of Memcached replicas for each type of cache using configuration settings when using jsonnet.

## Important changes

In Grafana Mimir 2.15, the following behavior has changed:

The following alertmanager metrics are not exported for a `user` label when the metric value is zero:

- `cortex_alertmanager_alerts_received_total`
- `cortex_alertmanager_alerts_invalid_total`
- `cortex_alertmanager_partial_state_merges_total`
- `cortex_alertmanager_partial_state_merges_failed_total`
- `cortex_alertmanager_state_replication_total`
- `cortex_alertmanager_state_replication_failed_total`
- `cortex_alertmanager_alerts`
- `cortex_alertmanager_silences`

PromQL compatibility has been upgraded from Prometheus 2.0 to 3.0. For more details, refer to the [Prometheus documentation](https://prometheus.io/docs/prometheus/3.0/migration/#promql). The following changes are of note:

- The `.` pattern in regular expressions in PromQL now matches newline characters.
- Lookback and range selectors are left-open and right-closed. They were previously left-closed and right-closed.
- Native histograms now use exponential interpolation.

Backwards compatibility in dashboards and alerts for `thanos_memcached_`-prefixed metrics has been removed. These metrics were removed in 2.12 in favor of `thanos_cache_`-prefixed metrics.

Experimental support for Redis as a cache backend has been removed from jsonnet.

The following deprecated configuration options were removed in this release:

- `-distributor.direct-otlp-translation-enabled`, which has been enabled by default since 2.13 and is now considered stable.
- `-query-scheduler.prioritize-query-components`, which is now always enabled.
- `-api.get-request-for-ingester-shutdown-enabled`, a deprecated experimental flag which has been marked for removal in 2.15.

## Experimental features

Grafana Mimir 2.15 includes some features that are experimental and disabled by default.
Use these features with caution and report any issues that you encounter:

You can now enable Mimir's experimental PromQL engine with `-querier.query-engine=mimir`. This new engine provides improved performance and reduced querier resource consumption. However, it only supports a subset of all PromQL features. It falls back to the regular Prometheus engine for queries containing unsupported features.

You can now use the query-frontend to cache non-transient errors using the experimental flags `-query-frontend.cache-errors` and `-query-frontend.results-cache-ttl-for-errors`.

The query-frontend and querier both support an experimental PromQL function, `double_exponential_smoothing`, which you can enable by setting `-querier.promql-experimental-functions-enabled=true` and `-query-frontend.promql-experimental-functions-enabled=true`.

The ingester now supports out-of-order native histogram ingestion via the flag `-ingester.ooo-native-histograms-ingestion-enabled`.

The ingester can now build 24h blocks for out-of-order data which is more than 24 hours old, using the setting `-blocks-storage.tsdb.bigger-out-of-order-blocks-for-old-samples`.

The ruler now supports caching the contents of rule groups via the setting `-ruler-storage.cache.rule-group-enabled`.

The distributor now supports promotion of OTel resource attributes to labels via the setting `-distributor.promote-otel-resource-attributes`.

## Bug fixes

- Alerts: Fix autoscaling metrics joins in `MimirAutoscalerNotActive` when series churn.
- Alerts: Exclude failed cache "add" operations from alerting since failures are expected in normal operation.
- Alerts: Exclude read-only replicas from `IngesterInstanceHasNoTenants` alert.
- Alerts: Use resident set memory for the `EtcdAllocatingTooMuchMemory` alert so that ephemeral file cache memory doesn't cause the alert to misfire.
- Dashboards: Fix autoscaling metrics joins when series churn.
- Distributor: Fix pooling buffer reuse logic when `-distributor.max-request-pool-buffer-size` is set.
- Ingester: Fix issue where active series requests error when encountering a stale posting.
- Ingester: Fix race condition in per-tenant TSDB creation.
- Ingester: Fix race condition in exemplar adding.
- Ingester: Fix race condition in native histogram appending.
- Ingester: Fix bug in concurrent fetching where a failure to list topics on startup would cause an invalid topic ID (0x00000000000000000000000000000000).
- Ingester: Fix data loss bug in the experimental ingest storage when a Kafka Fetch is split into multiple requests and some of them return an error.
- Ingester: Fix bug where chunks could have one unnecessary zero byte at the end.
- OTLP: Support integer exemplar value type.
- OTLP receiver: Preserve colons and combine multiple consecutive underscores into one when generating metric names in suffix adding mode (`-distributor.otel-metric-suffixes-enabled`).
- Prometheus: Fix issue where negation of native histograms (e.g. `-some_native_histogram_series`) did nothing.
- Prometheus: Always return unknown hint for first sample in non-gauge native histograms chunk to avoid incorrect counter reset hints when merging chunks from different sources.
- Prometheus: Ensure native histograms counter reset hints are corrected when merging results from different sources.
- PromQL: Fix issue where functions such as `rate()` over native histograms could return incorrect values if a float stale marker was present in the selected range.
- PromQL: `round` now removes the metric name again.
- PromQL: Fix issue where `metric might not be a counter, name does not end in _total/_sum/_count/_bucket` annotation would be emitted even if `rate` or `increase` did not have enough samples to compute a result.
- Querier: Fix the behavior of binary operators between native histograms and floats.
- Querier: Fix stddev+stdvar aggregations to always ignore native histograms, and to treat infinity consistently.
- Query-frontend: Fix issue where sharded queries could return annotations with incorrect or confusing position information.
- Query-frontend: Fix issue where downstream consumers may not generate correct cache keys for experimental error caching.
- Query-frontend: Support `X-Read-Consistency-Offsets` on labels queries too.
- Ruler: Fix issue when using the experimental `-ruler.max-independent-rule-evaluation-concurrency` feature, where the ruler could panic as it updates a running ruleset or shutdowns.

### Helm chart improvements

The Grafana Mimir and Grafana Enterprise Metrics Helm charts are released independently.
Refer to the [Grafana Mimir Helm chart documentation](/docs/helm-charts/mimir-distributed/latest/).


# Changelog

## 2.15.0

### Grafana Mimir

* [CHANGE] Alertmanager: the following metrics are not exported for a given `user` when the metric value is zero: #9359
  * `cortex_alertmanager_alerts_received_total`
  * `cortex_alertmanager_alerts_invalid_total`
  * `cortex_alertmanager_partial_state_merges_total`
  * `cortex_alertmanager_partial_state_merges_failed_total`
  * `cortex_alertmanager_state_replication_total`
  * `cortex_alertmanager_state_replication_failed_total`
  * `cortex_alertmanager_alerts`
  * `cortex_alertmanager_silences`
* [CHANGE] Distributor: Drop experimental `-distributor.direct-otlp-translation-enabled` flag, since direct OTLP translation is well tested at this point. #9647
* [CHANGE] Ingester: Change `-initial-delay` for circuit breakers to begin when the first request is received, rather than at breaker activation. #9842
* [CHANGE] Query-frontend: apply query pruning before query sharding instead of after. #9913
* [CHANGE] Ingester: remove experimental flags `-ingest-storage.kafka.ongoing-records-per-fetch` and `-ingest-storage.kafka.startup-records-per-fetch`. They are removed in favour of `-ingest-storage.kafka.max-buffered-bytes`. #9906
* [CHANGE] Ingester: Replace `cortex_discarded_samples_total` label from `sample-out-of-bounds` to `sample-timestamp-too-old`. #9885
* [CHANGE] Ruler: the `/prometheus/config/v1/rules` does not return an error anymore if a rule group is missing in the object storage after been successfully returned by listing the storage, because it could have been deleted in the meanwhile. #9936
* [CHANGE] Querier: The `.` pattern in regular expressions in PromQL matches newline characters. With this change regular expressions like `.*` match strings that include `\n`. To maintain the old behaviour, you will have to change regular expressions by replacing all `.` patterns with `[^\n]`, e.g. `foo[^\n]*`. This upgrades PromQL compatibility from Prometheus 2.0 to 3.0. #9844
* [CHANGE] Querier: Lookback and range selectors are left open and right closed (previously left closed and right closed). This change affects queries when the evaluation time perfectly aligns with the sample timestamps. For example assume querying a timeseries with evenly spaced samples exactly 1 minute apart. Previously, a range query with `5m` would usually return 5 samples, or 6 samples if the query evaluation aligns perfectly with a scrape. Now, queries like this will always return 5 samples. This upgrades PromQL compatibility from Prometheus 2.0 to 3.0. #9844
* [CHANGE] Querier: promql(native histograms): Introduce exponential interpolation. #9844
* [CHANGE] Remove deprecated `api.get-request-for-ingester-shutdown-enabled` setting, which scheduled for removal in 2.15. #10197
* [FEATURE] Querier: add experimental streaming PromQL engine, enabled with `-querier.query-engine=mimir`. #10067
* [FEATURE] Distributor: Add support for `lz4` OTLP compression. #9763
* [FEATURE] Query-frontend: added experimental configuration options `query-frontend.cache-errors` and `query-frontend.results-cache-ttl-for-errors` to allow non-transient responses to be cached. When set to `true` error responses from hitting limits or bad data are cached for a short TTL. #9028
* [FEATURE] Query-frontend: add middleware to control access to specific PromQL experimental functions on a per-tenant basis. #9798
* [FEATURE] gRPC: Support S2 compression. #9322
  * `-alertmanager.alertmanager-client.grpc-compression=s2`
  * `-ingester.client.grpc-compression=s2`
  * `-querier.frontend-client.grpc-compression=s2`
  * `-querier.scheduler-client.grpc-compression=s2`
  * `-query-frontend.grpc-client-config.grpc-compression=s2`
  * `-query-scheduler.grpc-client-config.grpc-compression=s2`
  * `-ruler.client.grpc-compression=s2`
  * `-ruler.query-frontend.grpc-client-config.grpc-compression=s2`
* [FEATURE] Alertmanager: limit added for maximum size of the Grafana state (`-alertmanager.max-grafana-state-size-bytes`). #9475
* [FEATURE] Alertmanager: limit added for maximum size of the Grafana configuration (`-alertmanager.max-config-size-bytes`). #9402
* [FEATURE] Ingester: Experimental support for ingesting out-of-order native histograms. This is disabled by default and can be enabled by setting `-ingester.ooo-native-histograms-ingestion-enabled` to `true`. #7175
* [FEATURE] Distributor: Added `-api.skip-label-count-validation-header-enabled` option to allow skipping label count validation on the HTTP write path based on `X-Mimir-SkipLabelCountValidation` header being `true` or not. #9576
* [FEATURE] Ruler: Add experimental support for caching the contents of rule groups. This is disabled by default and can be enabled by setting `-ruler-storage.cache.rule-group-enabled`. #9595 #10024
* [FEATURE] PromQL: Add experimental `info` function. Experimental functions are disabled by default, but can be enabled setting `-querier.promql-experimental-functions-enabled=true` in the query-frontend and querier. #9879
* [FEATURE] Distributor: Support promotion of OTel resource attributes to labels. #8271
* [FEATURE] Querier: Add experimental `double_exponential_smoothing` PromQL function. Experimental functions are disabled by default, but can be enabled by setting `-querier.promql-experimental-functions-enabled=true` in the query-frontend and querier. #9844
* [ENHANCEMENT] Query Frontend: Return server-side `bytes_processed` statistics following Server-Timing format. #9645 #9985
* [ENHANCEMENT] mimirtool: Adds bearer token support for mimirtool's analyze ruler/prometheus commands. #9587
* [ENHANCEMENT] Ruler: Support `exclude_alerts` parameter in `<prometheus-http-prefix>/api/v1/rules` endpoint. #9300
* [ENHANCEMENT] Distributor: add a metric to track tenants who are sending newlines in their label values called `cortex_distributor_label_values_with_newlines_total`. #9400
* [ENHANCEMENT] Ingester: improve performance of reading the WAL. #9508
* [ENHANCEMENT] Query-scheduler: improve the errors and traces emitted by query-schedulers when communicating with queriers. #9519
* [ENHANCEMENT] Compactor: uploaded blocks cannot be bigger than max configured compactor time range, and cannot cross the boundary for given time range. #9524
* [ENHANCEMENT] The distributor now validates that received label values only contain allowed characters. #9185
* [ENHANCEMENT] Add SASL plain authentication support to Kafka client used by the experimental ingest storage. Configure SASL credentials via the following settings: #9584
  * `-ingest-storage.kafka.sasl-password`
  * `-ingest-storage.kafka.sasl-username`
* [ENHANCEMENT] memberlist: TCP transport write path is now non-blocking, and is configurable by new flags: #9594
  * `-memberlist.max-concurrent-writes`
  * `-memberlist.acquire-writer-timeout`
* [ENHANCEMENT] memberlist: Notifications can now be processed once per interval specified by `-memberlist.notify-interval` to reduce notify storm CPU activity in large clusters. #9594
* [ENHANCEMENT] Query-scheduler: Remove the experimental `query-scheduler.prioritize-query-components` flag. Request queues always prioritize query component dequeuing above tenant fairness. #9703
* [ENHANCEMENT] Ingester: Emit traces for block syncing, to join up block-upload traces. #9656
* [ENHANCEMENT] Querier: Enable the optional querying of additional storage queryables. #9712
* [ENHANCEMENT] Ingester: Disable the push circuit breaker when ingester is in read-only mode. #9760
* [ENHANCEMENT] Ingester: Reduced lock contention in the `PostingsForMatchers` cache. #9773
* [ENHANCEMENT] Storage: Allow HTTP client settings to be tuned for GCS and Azure backends via an `http` block or corresponding CLI flags. This was already supported by the S3 backend. #9778
* [ENHANCEMENT] Ruler: Support `group_limit` and `group_next_token` parameters in the `<prometheus-http-prefix>/api/v1/rules` endpoint. #9563
* [ENHANCEMENT] Ingester: improved lock contention affecting read and write latencies during TSDB head compaction. #9822
* [ENHANCEMENT] Distributor: when a label value fails validation due to invalid UTF-8 characters, don't include the invalid characters in the returned error. #9828
* [ENHANCEMENT] Ingester: when experimental ingest storage is enabled, do not buffer records in the Kafka client when fetch concurrency is in use. #9838 #9850
* [ENHANCEMENT] Compactor: refresh deletion marks when updating the bucket index concurrently. This speeds up updating the bucket index by up to 16 times when there is a lot of blocks churn (thousands of blocks churning every cleanup cycle). #9881
* [ENHANCEMENT] PromQL: make `sort_by_label` stable. #9879
* [ENHANCEMENT] Distributor: Initialize ha_tracker cache before ha_tracker and distributor reach running state and begin serving writes. #9826 #9976
* [ENHANCEMENT] Ingester: `-ingest-storage.kafka.max-buffered-bytes` to limit the memory for buffered records when using concurrent fetching. #9892
* [ENHANCEMENT] Querier: improve performance and memory consumption of queries that select many series. #9914
* [ENHANCEMENT] Ruler: Support OAuth2 and proxies in Alertmanager client #9945 #10030
* [ENHANCEMENT] Ingester: Add `-blocks-storage.tsdb.bigger-out-of-order-blocks-for-old-samples` to build 24h blocks for out-of-order data belonging to the previous days instead of building smaller 2h blocks. This reduces pressure on compactors and ingesters when the out-of-order samples span multiple days in the past. #9844 #10033 #10035
* [ENHANCEMENT] Distributor: allow a different limit for info series (series ending in `_info`) label count, via `-validation.max-label-names-per-info-series`. #10028
* [ENHANCEMENT] Ingester: do not reuse labels, samples and histograms slices in the write request if there are more entries than 10x the pre-allocated size. This should help to reduce the in-use memory in case of few requests with a very large number of labels, samples or histograms. #10040
* [ENHANCEMENT] Query-Frontend: prune `<subquery> and on() (vector(x)==y)` style queries and stop pruning `<subquery> < -Inf`. Triggered by https://github.com/prometheus/prometheus/pull/15245. #10026
* [ENHANCEMENT] Query-Frontend: perform request format validation before processing the request. #10093
* [BUGFIX] Fix issue where functions such as `rate()` over native histograms could return incorrect values if a float stale marker was present in the selected range. #9508
* [BUGFIX] Fix issue where negation of native histograms (eg. `-some_native_histogram_series`) did nothing. #9508
* [BUGFIX] Fix issue where `metric might not be a counter, name does not end in _total/_sum/_count/_bucket` annotation would be emitted even if `rate` or `increase` did not have enough samples to compute a result. #9508
* [BUGFIX] Fix issue where sharded queries could return annotations with incorrect or confusing position information. #9536
* [BUGFIX] Fix issue where downstream consumers may not generate correct cache keys for experimental error caching. #9644
* [BUGFIX] Fix issue where active series requests error when encountering a stale posting. #9580
* [BUGFIX] Fix pooling buffer reuse logic when `-distributor.max-request-pool-buffer-size` is set. #9666
* [BUGFIX] Fix issue when using the experimental `-ruler.max-independent-rule-evaluation-concurrency` feature, where the ruler could panic as it updates a running ruleset or shutdowns. #9726
* [BUGFIX] Always return unknown hint for first sample in non-gauge native histograms chunk to avoid incorrect counter reset hints when merging chunks from different sources. #10033
* [BUGFIX] Ensure native histograms counter reset hints are corrected when merging results from different sources. #9909
* [BUGFIX] Ingester: Fix race condition in per-tenant TSDB creation. #9708
* [BUGFIX] Ingester: Fix race condition in exemplar adding. #9765
* [BUGFIX] Ingester: Fix race condition in native histogram appending. #9765
* [BUGFIX] Ingester: Fix bug in concurrent fetching where a failure to list topics on startup would cause to use an invalid topic ID (0x00000000000000000000000000000000). #9883
* [BUGFIX] Ingester: Fix data loss bug in the experimental ingest storage when a Kafka Fetch is split into multiple requests and some of them return an error. #9963 #9964
* [BUGFIX] PromQL: `round` now removes the metric name again. #9879
* [BUGFIX] Query-Frontend: fix `QueryFrontendCodec` module initialization to set lookback delta from `-querier.lookback-delta`. #9984
* [BUGFIX] OTLP: Support integer exemplar value type. #9844
* [BUGFIX] Querier: Correct the behaviour of binary operators between native histograms and floats. #9844
* [BUGFIX] Querier: Fix stddev+stdvar aggregations to always ignore native histograms. #9844
* [BUGFIX] Querier: Fix stddev+stdvar aggregations to treat Infinity consistently. #9844
* [BUGFIX] Ingester: Chunks could have one unnecessary zero byte at the end. #9844
* [BUGFIX] OTLP receiver: Preserve colons and combine multiple consecutive underscores into one when generating metric names in suffix adding mode (`-distributor.otel-metric-suffixes-enabled`). #10075

### Mixin

* [CHANGE] Remove backwards compatibility for `thanos_memcached_` prefixed metrics in dashboards and alerts removed in 2.12. #9674 #9758
* [CHANGE] Reworked the alert `MimirIngesterStuckProcessingRecordsFromKafka` to also work when concurrent fetching is enabled. #9855
* [ENHANCEMENT] Unify ingester autoscaling panels on 'Mimir / Writes' dashboard to work for both ingest-storage and non-ingest-storage autoscaling. #9617
* [ENHANCEMENT] Alerts: Enable configuring job prefix for alerts to prevent clashes with metrics from Loki/Tempo. #9659
* [ENHANCEMENT] Dashboards: visualize the age of source blocks in the "Mimir / Compactor" dashboard. #9697
* [ENHANCEMENT] Dashboards: Include block compaction level on queried blocks in 'Mimir / Queries' dashboard. #9706
* [ENHANCEMENT] Alerts: add `MimirIngesterMissedRecordsFromKafka` to detect gaps in consumed records in the ingester when using the experimental Kafka-based storage. #9921 #9972
* [ENHANCEMENT] Dashboards: Add more panels to 'Mimir / Writes' for concurrent ingestion and fetching when using ingest storage. #10021
* [BUGFIX] Dashboards: Fix autoscaling metrics joins when series churn. #9412 #9450 #9432
* [BUGFIX] Alerts: Fix autoscaling metrics joins in `MimirAutoscalerNotActive` when series churn. #9412
* [BUGFIX] Alerts: Exclude failed cache "add" operations from alerting since failures are expected in normal operation. #9658
* [BUGFIX] Alerts: Exclude read-only replicas from `IngesterInstanceHasNoTenants` alert. #9843
* [BUGFIX] Alerts: Use resident set memory for the `EtcdAllocatingTooMuchMemory` alert so that ephemeral file cache memory doesn't cause the alert to misfire. #9997
* [BUGFIX] Query-frontend: support `X-Read-Consistency-Offsets` on labels queries too.

### Jsonnet

* [CHANGE] Remove support to set Redis as a cache backend from jsonnet. #9677
* [CHANGE] Rollout-operator now defaults to storing scaling operation metadata in a Kubernetes ConfigMap. This avoids recursively invoking the admission webhook in some Kubernetes environments. #9699
* [CHANGE] Update rollout-operator version to 0.20.0. #9995
* [CHANGE] Remove the `track_sizes` feature for Memcached pods since it is unused. #10032
* [CHANGE] The configuration options `autoscaling_distributor_min_replicas` and `autoscaling_distributor_max_replicas` has been renamed to `autoscaling_distributor_min_replicas_per_zone` and `autoscaling_distributor_max_replicas_per_zone` respectively. #10019
* [FEATURE] Add support to deploy distributors in multi availability zones. #9548
* [FEATURE] Add configuration settings to set the number of Memcached replicas for each type of cache (`memcached_frontend_replicas`, `memcached_index_queries_replicas`, `memcached_chunks_replicas`, `memcached_metadata_replicas`). #9679
* [ENHANCEMENT] Add `ingest_storage_ingester_autoscaling_triggers` option to specify multiple triggers in ScaledObject created for ingest-store ingester autoscaling. #9422
* [ENHANCEMENT] Add `ingest_storage_ingester_autoscaling_scale_up_stabilization_window_seconds` and `ingest_storage_ingester_autoscaling_scale_down_stabilization_window_seconds` config options to make stabilization window for ingester autoscaling when using ingest-storage configurable. #9445
* [ENHANCEMENT] Make label-selector in ReplicaTemplate/ingester-zone-a object configurable when using ingest-storage. #9480
* [ENHANCEMENT] Add `querier_only_args` option to specify CLI flags that apply only to queriers but not ruler-queriers. #9503
* [ENHANCEMENT] Validate the Kafka client ID configured when ingest storage is enabled. #9573
* [ENHANCEMENT] Configure pod anti-affinity and tolerations to run etcd pods multi-AZ when `_config.multi_zone_etcd_enabled` is set to `true`. #9725

### Mimirtool

### Mimir Continuous Test

### Query-tee

* [FEATURE] Added `-proxy.compare-skip-samples-before` to skip samples before the given time when comparing responses. The time can be in RFC3339 format (or) RFC3339 without the timezone and seconds (or) date only. #9515
* [FEATURE] Add `-backend.config-file` for a YAML configuration file for per-backend options. Currently, it only supports additional HTTP request headers. #10081
* [ENHANCEMENT] Added human-readable timestamps to comparison failure messages. #9665

### Documentation

* [BUGFIX] Send native histograms: update the migration guide with the corrected dashboard query for switching between classic and native histograms queries. #10052

### Tools

* [FEATURE] `splitblocks`: add new tool to split blocks larger than a specified duration into multiple blocks. #9517, #9779
* [ENHANCEMENT] `copyblocks`: add `--skip-no-compact-block-duration-check`, which defaults to `false`, to simplify targeting blocks that are not awaiting compaction. #9439
* [ENHANCEMENT] `copyblocks`: add `--user-mapping` to support copying blocks between users. #10110
* [ENHANCEMENT] `kafkatool`: add SASL plain authentication support. The following new CLI flags have been added: #9584
  * `--kafka-sasl-username`
  * `--kafka-sasl-password`
* [ENHANCEMENT] `kafkatool`: add `dump print` command to print the content of write requests from a dump. #9942
* [ENHANCEMENT] Updated `KubePersistentVolumeFillingUp` runbook, including a sample command to debug the distroless image. #9802


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.14.2...mimir-2.15.0


================================================================================

# 2.15.1

Tag: mimir-2.15.1
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.15.1

This release contains 8 PRs from 3 authors. Thank you!

# Changelog

## 2.15.1

### Grafana Mimir

* [BUGFIX] Update module github.com/golang/glog to v1.2.4 to address [CVE-2024-45339](https://nvd.nist.gov/vuln/detail/CVE-2024-45339). #10541
* [BUGFIX] Update module github.com/go-jose/go-jose/v4 to v4.0.5 to address [CVE-2025-27144](https://nvd.nist.gov/vuln/detail/CVE-2025-27144). #10783
* [BUGFIX] Update module golang.org/x/oauth2 to v0.27.0 to address [CVE-2025-22868](https://nvd.nist.gov/vuln/detail/CVE-2025-22868). #10803
* [BUGFIX] Update module golang.org/x/crypto to v0.35.0 to address [CVE-2025-22869](https://nvd.nist.gov/vuln/detail/CVE-2025-22869). #10804
* [BUGFIX] Upgrade Go to 1.23.7 to address [CVE-2024-45336](https://nvd.nist.gov/vuln/detail/CVE-2024-45336), [CVE-2024-45341](https://nvd.nist.gov/vuln/detail/CVE-2024-45341), and [CVE-2025-22866](https://nvd.nist.gov/vuln/detail/CVE-2025-22866). #10862



**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.15.0...mimir-2.15.1


================================================================================

# 2.15.2

Tag: mimir-2.15.2
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.15.2

This release contains 4 PRs from 3 authors. Thank you!

# Changelog

## 2.15.2

### Grafana Mimir

* [BUGFIX] Update module golang.org/x/net to v0.36.0 to address [CVE-2025-22870](https://nvd.nist.gov/vuln/detail/CVE-2025-22870). #10875
* [BUGFIX] Update module github.com/golang-jwt/jwt/v5 to v5.2.2 to address [CVE-2025-30204](https://nvd.nist.gov/vuln/detail/CVE-2025-30204). #11045



**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.15.1...mimir-2.15.2


================================================================================

# 2.15.3

Tag: mimir-2.15.3
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.15.3

This release contains 10 PRs from 5 authors, including new contributors mimir-github-bot[bot]. Thank you!

# Changelog

## 2.15.3

### Grafana Mimir

* [BUGFIX] Update to Go v1.23.9 to address [CVE-2025-22871](https://nvd.nist.gov/vuln/detail/CVE-2025-22871). #11537

### Mimirtool

* [BUGFIX] Upgrade Alpine Linux to 3.20.6, fixes CVE-2025-26519. #11530

### Mimir Continuous Test

* [BUGFIX] Upgrade Alpine Linux to 3.20.6, fixes CVE-2025-26519. #11530


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.15.2...mimir-2.15.3


================================================================================

# 2.16.0

Tag: mimir-2.16.0
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.16.0

This release contains 463 PRs from 69 authors, including new contributors Alessandro Verzicco, Alex Greenbank, André Pires, Bjorn Stout, Bruno FERNANDO, Casie Chen, Dustin Wilson, Edwin Tye, Kenny Trytek, Leszek Błażewski, Markus Opolka, Matthew Jacobson, Matt Veitas, mimir-github-bot[bot], Moustafa Baiou, Ryan Brady, TheRealNoob. Thank you!

# Grafana Mimir version 2.16.0 release notes

## Features and enhancements

In rulers, when rule concurrency is enabled for a rule group, its rules will now be reordered and run in batches based on their dependencies. This increases the number of rules that can potentially run concurrently. Note that the global and tenant-specific limits around the number of rule groups and rules per group still apply.

Using `mimirtool` to analyze Grafana dashboards now supports bar chart, pie chart, state timeline, status history, histogram, candlestick, canvas, flame graph, geomap, node graph, trend, and XY chart panels.

## Important changes

In Grafana Mimir 2.16, the following behavior has changed:

Grafana Mimir only provides container images based on [distroless](https://github.com/GoogleContainerTools/distroless) images. Alpine Linux-based container images were deprecated in the 2.12 release and are no longer built.

How experimental PromQL functions are enabled has changed.

- The experimental CLI flags `-querier.promql-experimental-functions-enabled` and `-query-frontend.block-promql-experimental-functions` and respective YAML configuration have been removed from query-frontends and queriers.
- Experimental PromQL functions are disabled by default but can be enabled using only the per-tenant setting `enabled_promql_experimental_functions`.

Support for native histograms and out-of-order native histograms is enabled by default in ingesters.

Distributors discard float and histogram samples with duplicated timestamps from each timeseries in a request before the request is forwarded to ingesters. Discarded samples are tracked by `cortex_discarded_samples_total` metrics with the reason `sample_duplicate_timestamp`.

## Experimental features

Grafana Mimir 2.16 includes some features that are experimental and disabled by default. Use these features with caution and report any issues that you encounter:

Distributors now include experimental support for the Influx [line protocol](https://docs.influxdata.com/influxdb/cloud/reference/syntax/line-protocol/).

Query-frontends now include experimental support to "spin off" subqueries as actual range queries, so that they benefit from query acceleration techniques such as sharding, splitting, and caching.

## Bug fixes

- Distributor: Use a boolean to track changes while merging the ReplicaDesc components, rather than comparing the objects directly. #10185
- Querier: Fix timeout responding to the query-frontend when the response size is within a few hundred bytes of `-querier.frontend-client.grpc-max-send-msg-size`. #10154
- Query-frontend and querier: Show warning and info annotations in some cases where they were missing (if a lazy querier was used). #10277
- Query-frontend: Fix an issue where transient errors are inadvertently cached. #10537 #10631
- Ruler: Fix indeterminate rules always, instead of never, running concurrently when `-ruler.max-independent-rule-evaluation-concurrency` is set. https://github.com/prometheus/prometheus/pull/15560 #10258
- PromQL: Fix various UTF-8 bugs related to quoting. https://github.com/prometheus/prometheus/pull/15531 #10258
- Ruler: Fix an issue when using the experimental `-ruler.max-independent-rule-evaluation-concurrency` feature, where if a rule group was eligible for concurrency, it would flap between running concurrently or not based on the time it took after running concurrently. #9726 #10189
- Mimirtool: `remote-read` commands now return data. #10286
- PromQL: Fix deriv, predict_linear and double_exponential_smoothing with histograms https://github.com/prometheus/prometheus/pull/15686 #10383
- MQE: Fix deriv with histograms. #10383
- PromQL: Fix <aggr_over_time> functions with histograms. https://github.com/prometheus/prometheus/pull/15711 #10400
- MQE: Fix <aggr_over_time> functions with histograms. #10400
- Distributor: Return HTTP status 415, Unsupported Media Type, instead of 200, Success, for Remote Write 2.0 until we support it. #10423 #10916
- Query-frontend: Add `-query-frontend.prom2-range-compat` flag and corresponding YAML to rewrite queries with ranges that worked in Prometheus 2 but are invalid in Prometheus 3. #10445 #10461 #10502
- Distributor: Fix edge case at the HA-tracker with memberlist as KVStore, where when a replica in the KVStore is marked as deleted but not yet removed, it fails to update the KVStore. #10443
- Distributor: Fix panics in `DurationWithJitter` util functions when computed variance is zero. #10507
- Ingester: Fixed a race condition in the `PostingsForMatchers` cache that may have infrequently returned expired cached postings. #10500
- Distributor: Report partially converted OTLP requests with status 400, Bad Request. #10588
- Ruler: Fix issue where rule evaluations could be missed while shutting down a ruler instance if that instance owns many rule groups. prometheus/prometheus#15804 #10762
- Ingester: Add additional check on reactive limiter queue sizes. #10722
- TSDB: Fix unknown series errors and possible lost data during WAL replay when series are removed from the head due to inactivity and reappear before the next WAL checkpoint. https://github.com/prometheus/prometheus/pull/16060 #10824
- Querier: Fix issue where `label_join` could incorrectly return multiple series with the same labels rather than failing with `vector cannot contain metrics with the same labelset`. https://github.com/prometheus/prometheus/pull/15975 #10826
- Querier: Fix issue where counter resets on native histograms could be incorrectly under or over-counted when using subqueries. https://github.com/prometheus/prometheus/pull/15987 #10871
- Ingester: Fix goroutines and memory leak when experimental ingest storage is enabled and a server-side error occurs during metrics ingestion. #10915
- Mimirtool: Fix issue where `MIMIR_HTTP_PREFIX` environment variable was ignored and the value from `MIMIR_MIMIR_HTTP_PREFIX` was used instead. #10207

### Helm chart improvements

The Grafana Mimir and Grafana Enterprise Metrics Helm chart is released independently.
Refer to the [Grafana Mimir Helm chart documentation](/docs/helm-charts/mimir-distributed/latest/).

# Changelog

## 2.16.0

### Grafana Mimir

* [CHANGE] Querier: pass context to queryable `IsApplicable` hook. #10451
* [CHANGE] Distributor: OTLP and push handler replace all non-UTF8 characters with the unicode replacement character `\uFFFD` in error messages before propagating them. #10236
* [CHANGE] Querier: pass query matchers to queryable `IsApplicable` hook. #10256
* [CHANGE] Build: removed Mimir Alpine Docker image and related CI tests. #10469
* [CHANGE] Query-frontend: Add `topic` label to `cortex_ingest_storage_strong_consistency_requests_total`, `cortex_ingest_storage_strong_consistency_failures_total`, and `cortex_ingest_storage_strong_consistency_wait_duration_seconds` metrics. #10220
* [CHANGE] Ruler: cap the rate of retries for remote query evaluation to 170/sec. This is configurable via `-ruler.query-frontend.max-retries-rate`. #10375 #10403
* [CHANGE] Query-frontend: Add `topic` label to `cortex_ingest_storage_reader_last_produced_offset_requests_total`, `cortex_ingest_storage_reader_last_produced_offset_failures_total`, `cortex_ingest_storage_reader_last_produced_offset_request_duration_seconds`, `cortex_ingest_storage_reader_partition_start_offset_requests_total`, `cortex_ingest_storage_reader_partition_start_offset_failures_total`, `cortex_ingest_storage_reader_partition_start_offset_request_duration_seconds` metrics. #10462
* [CHANGE] Ingester: Set `-ingester.ooo-native-histograms-ingestion-enabled` to true by default. #10483
* [CHANGE] Ruler: Add `user` and `reason` labels to `cortex_ruler_write_requests_failed_total` and `cortex_ruler_queries_failed_total`; add `user` to
    `cortex_ruler_write_requests_total` and `cortex_ruler_queries_total` metrics. #10536
* [CHANGE] Querier / Query-frontend: Remove experimental `-querier.promql-experimental-functions-enabled` and `-query-frontend.block-promql-experimental-functions` CLI flags and respective YAML configuration options to enable experimental PromQL functions. Instead access to experimental PromQL functions is always blocked. You can enable them using the per-tenant setting `enabled_promql_experimental_functions`. #10660 #10712
* [CHANGE] Store-gateway: Include posting sampling rate in sparse index headers. When the sampling rate isn't set in a sparse index header, store gateway rebuilds the sparse header with the configured `blocks-storage.bucket-store.posting-offsets-in-mem-sampling` value. If the sparse header's sampling rate is set but doesn't match the configured rate, store gateway either rebuilds the sparse header or downsamples to the configured sampling rate. #10684 #10878
* [CHANGE] Distributor: Return specific error message when burst size limit is exceeded. #10835
* [CHANGE] Ingester: enable native histograms ingestion by default, meaning`ingester.native-histograms-ingestion-enabled` defaults to true. #10867
* [FEATURE] Ingester/Distributor: Add support for exporting cost attribution metrics (`cortex_ingester_attributed_active_series`, `cortex_distributor_received_attributed_samples_total`, and `cortex_discarded_attributed_samples_total`) with labels specified by customers to a custom Prometheus registry. This feature enables more flexible billing data tracking. #10269 #10702
* [FEATURE] Ruler: Added `/ruler/tenants` endpoints to list the discovered tenants with rule groups. #10738
* [FEATURE] Distributor: Add experimental Influx handler. #10153
* [ENHANCEMENT] Compactor: Expose `cortex_bucket_index_last_successful_update_timestamp_seconds` for all tenants assigned to the compactor before starting the block cleanup job. #10569
* [ENHANCEMENT] Query Frontend: Return server-side `samples_processed` statistics. #10103
* [ENHANCEMENT] Distributor: OTLP receiver now converts also metric metadata. See also https://github.com/prometheus/prometheus/pull/15416. #10168
* [ENHANCEMENT] Distributor: discard float and histogram samples with duplicated timestamps from each timeseries in a request before the request is forwarded to ingesters. Discarded samples are tracked by `cortex_discarded_samples_total` metrics with the reason `sample_duplicate_timestamp`. #10145 #10430
* [ENHANCEMENT] Ruler: Add `cortex_prometheus_rule_group_last_rule_duration_sum_seconds` metric to track the total evaluation duration of a rule group regardless of concurrency #10189
* [ENHANCEMENT] Distributor: Add native histogram support for `electedReplicaPropagationTime` metric in ha_tracker. #10264
* [ENHANCEMENT] Ingester: More efficient CPU/memory utilization-based read request limiting. #10325
* [ENHANCEMENT] OTLP: In addition to the flag `-distributor.otel-created-timestamp-zero-ingestion-enabled` there is now `-distributor.otel-start-time-quiet-zero` to convert OTel start timestamps to Prometheus QuietZeroNaNs. This flag is to make the change rollout safe between Ingesters and Distributors. #10238
* [ENHANCEMENT] Ruler: When rule concurrency is enabled for a rule group, its rules will now be reordered and run in batches based on their dependencies. This increases the number of rules that can potentially run concurrently. Note that the global and tenant-specific limits still apply #10400
* [ENHANCEMENT] Query-frontend: include more information about read consistency in trace spans produced when using experimental ingest storage. #10412
* [ENHANCEMENT] Ingester: Hide tokens in ingester ring status page when ingest storage is enabled #10399
* [ENHANCEMENT] Ingester: add `active_series_additional_custom_trackers` configuration, in addition to the already existing `active_series_custom_trackers`. The `active_series_additional_custom_trackers` configuration allows you to configure additional custom trackers that get merged with `active_series_custom_trackers` at runtime. #10428
* [ENHANCEMENT] Query-frontend: Allow blocking raw http requests with the `blocked_requests` configuration. Requests can be blocked based on their path, method or query parameters #10484
* [ENHANCEMENT] Ingester: Added the following metrics exported by `PostingsForMatchers` cache: #10500 #10525
  * `cortex_ingester_tsdb_head_postings_for_matchers_cache_hits_total`
  * `cortex_ingester_tsdb_head_postings_for_matchers_cache_misses_total`
  * `cortex_ingester_tsdb_head_postings_for_matchers_cache_requests_total`
  * `cortex_ingester_tsdb_head_postings_for_matchers_cache_skips_total`
  * `cortex_ingester_tsdb_head_postings_for_matchers_cache_evictions_total`
  * `cortex_ingester_tsdb_block_postings_for_matchers_cache_hits_total`
  * `cortex_ingester_tsdb_block_postings_for_matchers_cache_misses_total`
  * `cortex_ingester_tsdb_block_postings_for_matchers_cache_requests_total`
  * `cortex_ingester_tsdb_block_postings_for_matchers_cache_skips_total`
  * `cortex_ingester_tsdb_block_postings_for_matchers_cache_evictions_total`
* [ENHANCEMENT] Add support for the HTTP header `X-Filter-Queryables` which allows callers to decide which queryables should be used by the querier, useful for debugging and testing queryables in isolation. #10552 #10594
* [ENHANCEMENT] Compactor: Shuffle users' order in `BlocksCleaner`. Prevents bucket indexes from going an extended period without cleanup during compactor restarts. #10513
* [ENHANCEMENT] Distributor, querier, ingester and store-gateway: Add support for `limit` parameter for label names and values requests. #10410
* [ENHANCEMENT] Ruler: Adds support for filtering results from rule status endpoint by `file[]`, `rule_group[]` and `rule_name[]`. #10589
* [ENHANCEMENT] Query-frontend: Add option to "spin off" subqueries as actual range queries, so that they benefit from query acceleration techniques such as sharding, splitting, and caching. To enable this feature, set the `-query-frontend.instant-queries-with-subquery-spin-off=<comma separated list>` option on the frontend or the `instant_queries_with_subquery_spin_off` per-tenant override with regular expressions matching the queries to enable. #10460 #10603 #10621 #10742 #10796
* [ENHANCEMENT] Querier, ingester: The series API respects passed `limit` parameter. #10620 #10652
* [ENHANCEMENT] Store-gateway: Add experimental settings under `-store-gateway.dynamic-replication` to allow more than the default of 3 store-gateways to own recent blocks. #10382 #10637
* [ENHANCEMENT] Ingester: Add reactive concurrency limiters to protect push and read operations from overload. #10574
* [ENHANCEMENT] Compactor: Add experimental `-compactor.max-lookback` option to limit blocks considered in each compaction cycle. Blocks uploaded prior to the lookback period aren't processed. This option helps reduce CPU utilization in tenants with large block metadata files that are processed before each compaction. #10585 #10794
* [ENHANCEMENT] Distributor: Optionally expose the current HA replica for each tenant in the `cortex_ha_tracker_elected_replica_status` metric. This is enabled with the `-distributor.ha-tracker.enable-elected-replica-metric=true` flag. #10644
* [ENHANCEMENT] Enable three Go runtime metrics: #10641
  * `go_cpu_classes_gc_total_cpu_seconds_total`
  * `go_cpu_classes_total_cpu_seconds_total`
  * `go_cpu_classes_idle_cpu_seconds_total`
* [ENHANCEMENT] All: Add experimental support for cluster validation in gRPC calls. When it is enabled, gRPC server verifies if a request coming from a gRPC client comes from an expected cluster. This validation can be configured by the following experimental configuration options: #10767
  * `-server.cluster-validation.label`
  * `-server.cluster-validation.grpc.enabled`
  * `-server.cluster-validation.grpc.soft-validation`
* [ENHANCEMENT] gRPC clients: Add experimental support to include the cluster validation label in gRPC metadata. When cluster validation is enabled on gRPC server side, the cluster validation label from gRPC metadata is compared with the gRPC server's cluster validation label. #10869 #10883
  * By setting `-<grpc-client-config-path>.cluster-validation.label`, you configure the cluster validation label of _a single_ gRPC client, whose `grpcclient.Config` object is configurable through `-<grpc-client-config-path>`.
  * By setting `-common.client-cluster-validation.label`, you configure the cluster validation label of _all_ gRPC clients.
* [ENHANCEMENT] gRPC clients: Add `cortex_client_request_invalid_cluster_validation_labels_total` metrics, that are used by Mimir's gRPC clients to track invalid cluster validations. #10767
* [ENHANCEMENT] Add experimental metric `cortex_distributor_dropped_native_histograms_total` to measure native histograms silently dropped when native histograms are disabled for a tenant. #10760
* [ENHANCEMENT] Compactor: Add experimental `-compactor.upload-sparse-index-headers` option. When enabled, the compactor will attempt to upload sparse index headers to object storage. This prevents latency spikes after adding store-gateway replicas. #10684
* [ENHANCEMENT] Memcached: Add experimental `-<prefix>.memcached.addresses-provider` flag to use alternate DNS service discovery backends when discovering Memcached hosts. #10895
* [BUGFIX] Distributor: Use a boolean to track changes while merging the ReplicaDesc components, rather than comparing the objects directly. #10185
* [BUGFIX] Querier: fix timeout responding to query-frontend when response size is very close to `-querier.frontend-client.grpc-max-send-msg-size`. #10154
* [BUGFIX] Query-frontend and querier: show warning/info annotations in some cases where they were missing (if a lazy querier was used). #10277
* [BUGFIX] Query-frontend: Fix an issue where transient errors are inadvertently cached. #10537 #10631
* [BUGFIX] Ruler: fix indeterminate rules being always run concurrently (instead of never) when `-ruler.max-independent-rule-evaluation-concurrency` is set. https://github.com/prometheus/prometheus/pull/15560 #10258
* [BUGFIX] PromQL: Fix various UTF-8 bugs related to quoting. https://github.com/prometheus/prometheus/pull/15531 #10258
* [BUGFIX] Ruler: Fixed an issue when using the experimental `-ruler.max-independent-rule-evaluation-concurrency` feature, where if a rule group was eligible for concurrency, it would flap between running concurrently or not based on the time it took after running concurrently. #9726 #10189
* [BUGFIX] Mimirtool: `remote-read` commands will now return data. #10286
* [BUGFIX] PromQL: Fix deriv, predict_linear and double_exponential_smoothing with histograms https://github.com/prometheus/prometheus/pull/15686 #10383
* [BUGFIX] MQE: Fix deriv with histograms #10383
* [BUGFIX] PromQL: Fix <aggr_over_time> functions with histograms https://github.com/prometheus/prometheus/pull/15711 #10400
* [BUGFIX] MQE: Fix <aggr_over_time> functions with histograms #10400
* [BUGFIX] Distributor: return HTTP status 415 Unsupported Media Type instead of 200 Success for Remote Write 2.0 until we support it. #10423
* [BUGFIX] Query-frontend: Add flag `-query-frontend.prom2-range-compat` and corresponding YAML to rewrite queries with ranges that worked in Prometheus 2 but are invalid in Prometheus 3. #10445 #10461 #10502
* [BUGFIX] Distributor: Fix edge case at the HA-tracker with memberlist as KVStore, where when a replica in the KVStore is marked as deleted but not yet removed, it fails to update the KVStore. #10443
* [BUGFIX] Distributor: Fix panics in `DurationWithJitter` util functions when computed variance is zero. #10507
* [BUGFIX] Ingester: Fixed a race condition in the `PostingsForMatchers` cache that may have infrequently returned expired cached postings. #10500
* [BUGFIX] Distributor: Report partially converted OTLP requests with status 400 Bad Request. #10588
* [BUGFIX] Ruler: fix issue where rule evaluations could be missed while shutting down a ruler instance if that instance owns many rule groups. prometheus/prometheus#15804 #10762
* [BUGFIX] Ingester: Add additional check on reactive limiter queue sizes. #10722
* [BUGFIX] TSDB: fix unknown series errors and possible lost data during WAL replay when series are removed from the head due to inactivity and reappear before the next WAL checkpoint. https://github.com/prometheus/prometheus/pull/16060 #10824
* [BUGFIX] Querier: fix issue where `label_join` could incorrectly return multiple series with the same labels rather than failing with `vector cannot contain metrics with the same labelset`. https://github.com/prometheus/prometheus/pull/15975 #10826
* [BUGFIX] Querier: fix issue where counter resets on native histograms could be incorrectly under- or over-counted when using subqueries. https://github.com/prometheus/prometheus/pull/15987 #10871
* [BUGFIX] Ingester: fix goroutines and memory leak when experimental ingest storage enabled and a server-side error occurs during metrics ingestion. #10915
* [BUGFIX] Alertmanager: Avoid fetching Grafana state if Grafana AM compatibility is not enabled. #10857

### Mixin

* [CHANGE] Alerts: Only alert on errors performing cache operations if there are over 10 request/sec to avoid flapping. #10832
* [FEATURE] Add compiled mixin for GEM installations in `operations/mimir-mixin-compiled-gem`. #10690 #10877
* [ENHANCEMENT] Dashboards: clarify that the ingester and store-gateway panels on the 'Reads' dashboard show data from all query requests to that component, not just requests from the main query path (ie. requests from the ruler query path are included as well). #10598
* [ENHANCEMENT] Dashboards: add ingester and store-gateway panels from the 'Reads' dashboard to the 'Remote ruler reads' dashboard as well. #10598
* [ENHANCEMENT] Dashboards: add ingester and store-gateway panels showing only requests from the respective dashboard's query path to the 'Reads' and 'Remote ruler reads' dashboards. For example, the 'Remote ruler reads' dashboard now has panels showing the ingester query request rate from ruler-queriers. #10598
* [ENHANCEMENT] Dashboards: 'Writes' dashboard: show write requests broken down by request type. #10599
* [ENHANCEMENT] Dashboards: clarify when query-frontend and query-scheduler dashboard panels are expected to show no data. #10624
* [ENHANCEMENT] Alerts: Add warning alert `DistributorGcUsesTooMuchCpu`. #10641
* [ENHANCEMENT] Dashboards: Add "Federation-frontend" dashboard for GEM. #10697 #10736
* [ENHANCEMENT] Dashboards: Add Query-Scheduler <-> Querier Inflight Requests row to Query Reads and Remote Ruler reads dashboards. #10290
* [ENHANCEMENT] Alerts: Add "Federation-frontend" alert for remote clusters returning errors. #10698
* [BUGFIX] Dashboards: fix how we switch between classic and native histograms. #10018
* [BUGFIX] Alerts: Ignore cache errors performing `delete` operations since these are expected to fail when keys don't exist. #10287
* [BUGFIX] Dashboards: fix "Mimir / Rollout Progress" latency comparison when gateway is enabled. #10495
* [BUGFIX] Dashboards: fix autoscaling panels when Mimir is deployed using Helm. #10473
* [BUGFIX] Alerts: fix `MimirAutoscalerNotActive` alert. #10564

### Jsonnet

* [CHANGE] Update rollout-operator version to 0.23.0. #10229 #10750
* [CHANGE] Memcached: Update to Memcached 1.6.34. #10318
* [CHANGE] Change multi-AZ deployments default toleration value from 'multi-az' to 'secondary-az', and make it configurable via the following settings: #10596
  * `_config.multi_zone_schedule_toleration` (default)
  * `_config.multi_zone_distributor_schedule_toleration` (distributor's override)
  * `_config.multi_zone_etcd_schedule_toleration` (etcd's override)
* [CHANGE] Ring: relaxed the hash ring heartbeat timeout for store-gateways: #10634
  * `-store-gateway.sharding-ring.heartbeat-timeout` set to `10m`
* [CHANGE] Memcached: Use 3 replicas for all cache types by default. #10739
* [ENHANCEMENT] Enforce `persistentVolumeClaimRetentionPolicy` `Retain` policy on partition ingesters during migration to experimental ingest storage. #10395
* [ENHANCEMENT] Allow to not configure `topologySpreadConstraints` by setting the following configuration options to a negative value: #10540
  * `distributor_topology_spread_max_skew`
  * `query_frontend_topology_spread_max_skew`
  * `querier_topology_spread_max_skew`
  * `ruler_topology_spread_max_skew`
  * `ruler_querier_topology_spread_max_skew`
* [ENHANCEMENT] Validate the `$._config.shuffle_sharding.ingester_partitions_shard_size` value when partition shuffle sharding is enabled in the ingest-storage mode. #10746
* [BUGFIX] Ports in container rollout-operator. #10273
* [BUGFIX] When downscaling is enabled, the components must annotate `prepare-downscale-http-port` with the value set in `$._config.server_http_port`. #10367

### Mimirtool

* [BUGFIX] Fix issue where `MIMIR_HTTP_PREFIX` environment variable was ignored and the value from `MIMIR_MIMIR_HTTP_PREFIX` was used instead. #10207
* [ENHANCEMENT] Unify mimirtool authentication options and add extra-headers support for commands that depend on MimirClient. #10178
* [ENHANCEMENT] `mimirtool grafana analyze` now supports custom panels. #10669
* [ENHANCEMENT] `mimirtool grafana analyze` now supports bar chart, pie chart, state timeline, status history,
  histogram, candlestick, canvas, flame graph, geomap, node graph, trend, and XY chart panels. #10669

### Mimir Continuous Test

### Query-tee

* [ENHANCEMENT] Allow skipping comparisons when preferred backend fails. Disabled by default, enable with `-proxy.compare-skip-preferred-backend-failures=true`. #10612

### Documentation

* [CHANGE] Add production tips related to cache size, heavy multi-tenancy and latency spikes. #9978
* [ENHANCEMENT] Update `MimirAutoscalerNotActive` and `MimirAutoscalerKedaFailing` runbooks, with an instruction to check whether Prometheus has enough CPU allocated. #10257

### Tools

* [CHANGE] `copyblocks`: Remove /pprof endpoint. #10329
* [CHANGE] `mark-blocks`: Replace `markblocks` with added features including removing markers and reading block identifiers from a file. #10597


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.15.1...mimir-2.16.0


================================================================================

# 2.16.1

Tag: mimir-2.16.1
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.16.1

This release contains 14 PRs from 8 authors. Thank you!

# Changelog

## 2.16.1

### Grafana Mimir

* [BUGFIX] Update to Go v1.23.9 to address [CVE-2025-22871](https://nvd.nist.gov/vuln/detail/CVE-2025-22871). #11543
* [BUGFIX] Update `golang.org/x/net` to v0.38.0 to address [CVE-2025-22872](https://nvd.nist.gov/vuln/detail/CVE-2025-22872). #11281
* [BUGFIX] Query-frontend: Fix a panic in monolithic mode caused by a clash in labels of the `cortex_client_invalid_cluster_validation_label_requests_total` metric definition. #11455


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.16.0...mimir-2.16.1


================================================================================

# 2.16.2

Tag: mimir-2.16.2
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.16.2

This release contains 3 PRs from 3 authors. Thank you!

# Changelog

## 2.16.2

### Grafana Mimir

* [BUGFIX] Update to Go v1.23.12 to address [CVE-2025-22871](https://nvd.nist.gov/vuln/detail/CVE-2025-22871), [CVE-2025-4673](https://nvd.nist.gov/vuln/detail/CVE-2025-4673), [CVE-2025-0913](https://nvd.nist.gov/vuln/detail/CVE-2025-0913). #12582
* [BUGFIX] Update Docker base images for tools from `alpine:3.21.3` to `alpine:3.21.5` to address [CVE-2025-9230](https://nvd.nist.gov/vuln/detail/CVE-2025-9230), [CVE-2025-9231](https://nvd.nist.gov/vuln/detail/CVE-2025-9231), [CVE-2025-2025-9232](https://nvd.nist.gov/vuln/detail/CVE-2025-9232). #12990


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.16.1...mimir-2.16.2


================================================================================

# 2.17.0

Tag: mimir-2.17.0
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.17.0

This release contains 735 PRs from 78 authors, including new contributors Bernaud Vincent, Carrie Edwards, danieleandreatta, David Vávra, Edgaras Giedrė, Gabija Bruzgaitė, Henrique Lourenço, Innokentii Konstantinov, Jasper Maes, Jeanette Tan, Joobi S B, Julius Hinze, Lukas Bischofberger, mihaelmiklec, mimir-vendoring[bot], Nasiel, pierremahot, rektabhi, sam clulow, Shay Pletcher, Thor K. Høgås, Toni Cárdenas, Yuran Ou, zhuoyuan-liu. Thank you!

# Grafana Mimir version 2.17.0 release notes

Grafana Labs is excited to announce version 2.17 of Grafana Mimir.

The highlights that follow include the top features, enhancements, and bug fixes in this release.
For the complete list of changes, refer to the [CHANGELOG](https://github.com/grafana/mimir/blob/main/CHANGELOG.md).

## Features and enhancements

MQE is enabled by default in queriers. MQE provides benefits over the Prometheus engine, inluding reduced memory and CPU consumption and improved performance. To use the Prometheus engine instead of MQE, set `-querier.query-engine=prometheus`.

Grafana Mimir now supports using the Mimir Query Engine (MQE) in query-frontends in addition to queriers. You can enable MQE in query-frontends by setting the experimental CLI flag `-query-frontend.query-engine=mimir` or through the corresponding YAML option.

You can export the `cortex_ingester_attributed_active_native_histogram_series` and `cortex_ingester_attributed_active_native_histogram_buckets` native histogram cost attribution metrics to a custom Prometheus registry with user-specified labels.

Grafana Mimir supports converting OTel explicit bucket histograms to Prometheus native histograms with custom buckets using the `distributor.otel-convert-histograms-to-nhcb` flag.

The following experimental features have been removed:

- The `max_cost_attribution_labels_per_user` cost attribution limit
- Read-write deployment mode in the mixin

## Important changes

In Grafana Mimir 2.17, the following behavior has changed:

The following default configuration values now apply to the memberlist KV store:

| Key                                 | Value   |
| ----------------------------------- | ------- |
| `memberlist.packet-dial-timeout`    | `500ms` |
| `memberlist.packet-write-timeout`   | `500ms` |
| `memberlist.max-concurrent-writes`  | `5`     |
| `memberlist.acquire-writer-timeout` | `1s`    |

These values perform better but might cause long-running packets to be dropped in high-latency networks.

The `-ruler-storage.cache.rule-group-enabled` experimental CLI flag has been removed. Caching rule group contents is now always enabled when a cache is configured for the ruler.

The `-ingester.ooo-native-histograms-ingestion-enabled` CLI flag and corresponding `ooo_native_histograms_ingestion_enabled` runtime configuration option have been removed. Out-of-order native histograms are now enabled whenever both native histogram and out-of-order ingestion is enabled.

The `-ingester.stream-chunks-when-using-blocks` CLI flag and corresponding `ingester_stream_chunks_when_using_blocks` runtime configuration option have been deprecated and will be removed in a future release.

The `cortex_distributor_label_values_with_newlines_total` metric has been removed.

In the distributor, `memberlist` is marked as a stable option for backend storage for the high availability tracker. `etcd` has been deprecated for this purpose.

## Experimental features

Grafana Mimir 2.17 includes some features that are experimental and disabled by default.
Use these features with caution and report any issues that you encounter:

- Prometheus Remote-Write 2.0 protocol.
- Duration expressions in PromQL. These are simple arithmetics on numbers in offset and range specification. For example, `rate(http_requests_total[5m * 2])`.
- Promoting OTel scope metadata, including name, version, schema URL, and attributes, to metric labels, prefixed with `otel_scope_`. Enable this feature through the `-distributor.otel-promote-scope-metadata` flag.
- Allowing primitive delta metrics ingestion through the OTLP endpoint with the `-distributor.otel-native-delta-ingestion` option.
- Support for `sort_by_label` and `sort_by_label_desc` PromQL functions.
- Support for cluster validation in HTTP calls. When enabled, the HTTP server verifies if a request coming from an HTTP client comes from an expected cluster. You can configure this validation with the following options:
  - `-server.cluster-validation.label`
  - `-server.cluster-validation.http.enabled`
  - `-server.cluster-validation.http.soft-validation`
  - `-server.cluster-validation.http.exclude-paths`

## Bug fixes

For a detailed list of bug fixes, refer to the [CHANGELOG](https://github.com/grafana/mimir/blob/main/CHANGELOG.md).

### Helm chart improvements

The Grafana Mimir and Grafana Enterprise Metrics Helm chart is released independently.
Refer to the [Grafana Mimir Helm chart documentation](https://grafana.com/docs/helm-charts/mimir-distributed/latest/).

# Changelog

## 2.17.0

### Grafana Mimir

* [CHANGE] Query-frontend: Ensure that cache keys generated from cardinality estimate middleware are less than 250 bytes in length by hashing the tenant IDs that are included in them. This change invalidates all cardinality estimates in the cache. #11568
* [CHANGE] Ruler: Remove experimental CLI flag `-ruler-storage.cache.rule-group-enabled` to enable or disable caching the contents of rule groups. Caching rule group contents is now always enabled when a cache is configured for the ruler. #10949
* [CHANGE] Ingester: Out-of-order native histograms are now enabled whenever both native histogram and out-of-order ingestion is enabled. The `-ingester.ooo-native-histograms-ingestion-enabled` CLI flag and corresponding `ooo_native_histograms_ingestion_enabled` runtime configuration option have been removed. #10956
* [CHANGE] Distributor: removed the `cortex_distributor_label_values_with_newlines_total` metric. #10977
* [CHANGE] Ingester/Distributor: renamed the experimental `max_cost_attribution_cardinality_per_user` config to `max_cost_attribution_cardinality`. #11092
* [CHANGE] Frontend: The subquery spin-off feature is now enabled with `-query-frontend.subquery-spin-off-enabled=true` instead of `-query-frontend.instant-queries-with-subquery-spin-off=.*` #11153
* [CHANGE] Overrides-exporter: Don't export per-tenant overrides that are set to their default values. #11173
* [CHANGE] gRPC/HTTP clients: Rename metric `cortex_client_request_invalid_cluster_validation_labels_total` to `cortex_client_invalid_cluster_validation_label_requests_total`. #11237
* [CHANGE] Querier: Use Mimir Query Engine (MQE) by default. Set `-querier.query-engine=prometheus` to continue using Prometheus' engine. #11501
* [CHANGE] Memcached: Ignore initial DNS resolution failure, meaning don't depend on Memcached on startup. #11602
* [CHANGE] Ingester: The `-ingester.stream-chunks-when-using-blocks` CLI flag and `ingester_stream_chunks_when_using_blocks` runtime configuration option have been deprecated and will be removed in a future release. #11711
* [CHANGE] Distributor: track `cortex_ingest_storage_writer_latency_seconds` metric for failed writes too. Added `outcome` label to distinguish between `success` and `failure`. #11770
* [CHANGE] Distributor: renamed few metrics used by experimental ingest storage. #11766
  * Renamed `cortex_ingest_storage_writer_produce_requests_total` to `cortex_ingest_storage_writer_produce_records_enqueued_total`
  * Renamed `cortex_ingest_storage_writer_produce_failures_total` to `cortex_ingest_storage_writer_produce_records_failed_total`
* [CHANGE] Distributor: moved HA tracker timeout config to limits. #11774
  * Moved `distributor.ha_tracker.ha_tracker_update_timeout` to `limits.ha_tracker_update_timeout`.
  * Moved `distributor.ha_tracker.ha_tracker_update_timeout_jitter_max` to `limits.ha_tracker_update_timeout_jitter_max`.
  * Moved `distributor.ha_tracker.ha_tracker_failover_timeout` to `limits.ha_tracker_failover_timeout`.
* [CHANGE] Distributor: `Memberlist` marked as stable as an option for backend storage for the HA tracker. #11861
* [CHANGE] Distributor: `etcd` deprecated as an option for backend storage for the HA tracker. #12047
* [CHANGE] Memberlist: Apply new default configuration values for MemberlistKV. This unlocks using it as backend storage for the HA Tracker. We have observed better performance with these defaults across different production loads. #11874
  * `memberlist.packet-dial-timeout`: `500ms`
  * `memberlist.packet-write-timeout`: `500ms`
  * `memberlist.max-concurrent-writes`: `5`
  * `memberlist.acquire-writer-timeout`: `1s`
    These defaults perform better but may cause long-running packets to be dropped in high-latency networks.
* [CHANGE] Query-frontend: Apply query pruning and check for disabled experimental functions earlier in query processing. #11939
* [FEATURE] Distributor: Experimental support for Prometheus Remote-Write 2.0 protocol. Limitations: Created timestamp is ignored, per series metadata is merged on metric family level automatically, ingestion might fail if client sends ProtoBuf fields out of order. The label `version` is added to the metric `cortex_distributor_requests_in_total` with a value of either `1.0` or `2.0` depending on the detected Remote-Write protocol. #11100 #11101 #11192 #11143
* [FEATURE] Query-frontend: expand `query-frontend.cache-errors` and `query-frontend.results-cache-ttl-for-errors` configuration options to cache non-transient response failures for instant queries. #11120
* [FEATURE] Query-frontend: Allow use of Mimir Query Engine (MQE) via the experimental CLI flags `-query-frontend.query-engine` or `-query-frontend.enable-query-engine-fallback` or corresponding YAML. #11417 #11775
* [FEATURE] Querier, query-frontend, ruler: Enable experimental support for duration expressions in PromQL, which are simple arithmetics on numbers in offset and range specification. #11344
* [FEATURE] You can configure Mimir to export traces in OTLP exposition format through the standard `OTEL_` environment variables. #11618
* [FEATURE] distributor: Allow configuring tenant-specific HA tracker failover timeouts. #11774
* [FEATURE] OTLP: Add experimental support for promoting OTel scope metadata (name, version, schema URL, attributes) to metric labels, prefixed with `otel_scope_`. Enable via the `-distributor.otel-promote-scope-metadata` flag. #11795
* [FEATURE] Distributor: Add experimental `-distributor.otel-native-delta-ingestion` option to allow primitive delta metrics ingestion via the OTLP endpoint. #11631
* [FEATURE] MQE: Add support for experimental `sort_by_label` and `sort_by_label_desc` PromQL functions. #11930
* [FEATURE] Ingester/Block-builder: Handle the created timestamp field for remote-write requests. #11977
* [FEATURE] Cost attribution: Labels specified in the limit configuration may specify an output label in order to override emitted label names. #12035
* [ENHANCEMENT] Dashboards: Add "Influx write requests" row to Writes Dashboard. #11731
* [ENHANCEMENT] Mixin: Add `MimirHighVolumeLevel1BlocksQueried` alert that fires when level 1 blocks are queried for more than 6 hours, indicating potential compactor performance issues. #11803
* [ENHANCEMENT] Querier: Make the maximum series limit for cardinality API requests configurable on a per-tenant basis with the `cardinality_analysis_max_results` option. #11456
* [ENHANCEMENT] Querier: Add configurable concurrency limit for remote read queries with the `--querier.max-concurrent-remote-read-queries` flag. Defaults to 2. Set to 0 for unlimited concurrency. #11892
* [ENHANCEMENT] Dashboards: Add "Queries / sec by read path" to Queries Dashboard. #11640
* [ENHANCEMENT] Dashboards: Add "Added Latency" row to Writes Dashboard. #11579
* [ENHANCEMENT] Ingester: Add support for exporting native histogram cost attribution metrics (`cortex_ingester_attributed_active_native_histogram_series` and `cortex_ingester_attributed_active_native_histogram_buckets`) with labels specified by customers to a custom Prometheus registry. #10892
* [ENHANCEMENT] Distributor: Add new metrics `cortex_distributor_received_native_histogram_samples_total` and `cortex_distributor_received_native_histogram_buckets_total` to track native histogram samples and bucket counts separately for billing calculations. Updated `cortex_distributor_received_samples_total` description to clarify it includes native histogram samples. #11728
* [ENHANCEMENT] Store-gateway: Download sparse headers uploaded by compactors. Compactors have to be configured with `-compactor.upload-sparse-index-headers=true` option. #10879 #11072.
* [ENHANCEMENT] Compactor: Upload block index file and multiple segment files concurrently. Concurrency scales linearly with block size up to `-compactor.max-per-block-upload-concurrency`. #10947
* [ENHANCEMENT] Ingester: Add per-user `cortex_ingester_tsdb_wal_replay_unknown_refs_total` and `cortex_ingester_tsdb_wbl_replay_unknown_refs_total` metrics to track unknown series references during WAL/WBL replay. #10981
* [ENHANCEMENT] Added `-ingest-storage.kafka.fetch-max-wait` configuration option to configure the maximum amount of time a Kafka broker waits for some records before a Fetch response is returned. #11012
* [ENHANCEMENT] Ingester: Add `cortex_ingester_tsdb_forced_compactions_in_progress` metric reporting a value of 1 when there's a forced TSDB head compaction in progress. #11006
* [ENHANCEMENT] Ingester: Add `cortex_ingest_storage_reader_records_batch_fetch_max_bytes` metric reporting the distribution of `MaxBytes` specified in the Fetch requests sent to Kafka. #11014
* [ENHANCEMENT] All: Add experimental support for cluster validation in HTTP calls. When it is enabled, HTTP server verifies if a request coming from an HTTP client comes from an expected cluster. This validation can be configured by the following experimental configuration options: #11010 #11549
  * `-server.cluster-validation.label`
  * `-server.cluster-validation.http.enabled`
  * `-server.cluster-validation.http.soft-validation`
  * `-server.cluster-validation.http.exclude-paths`
* [ENHANCEMENT] Query-frontend: Add experimental support to include the cluster validation label in HTTP request headers. When cluster validation is enabled on the HTTP server side, cluster validation labels from HTTP request headers are compared with the HTTP server's cluster validation label. #11010 #11145
  * By setting `-query-frontend.client-cluster-validation.label`, you configure the query-frontend's client cluster validation label.
  * The flag `-common.client-cluster-validation.label`, if set, provides the default for `-query-frontend.client-cluster-validation.label`.
* [ENHANCEMENT] Distributor: Add  `ignore_ingest_storage_errors` and `ingest_storage_max_wait_time` flags to control error handling and timeout behavior during ingest storage migration. #11291
  * `-ingest-storage.migration.ignore-ingest-storage-errors`
  * `-ingest-storage.migration.ingest-storage-max-wait-time`
* [ENHANCEMENT] Memberlist: Add `-memberlist.abort-if-fast-join-fails` support and retries on DNS resolution. #11067
* [ENHANCEMENT] Querier: Allow configuring all gRPC options for store-gateway client, similar to other gRPC clients. #11074
* [ENHANCEMENT] Ruler: Log the number of series returned for each query as `result_series_count` as part of `query stats` log lines. #11081
* [ENHANCEMENT] Ruler: Don't log statistics that are not available when using a remote query-frontend as part of `query stats` log lines. #11083
* [ENHANCEMENT] Ingester: Remove cost-attribution experimental `max_cost_attribution_labels_per_user` limit. #11090
* [ENHANCEMENT] Update Go to 1.24.2. #11114
* [ENHANCEMENT] Query-frontend: Add `cortex_query_samples_processed_total` metric. #11110
* [ENHANCEMENT] Query-frontend: Add `cortex_query_samples_processed_cache_adjusted_total` metric. #11164
* [ENHANCEMENT] Ingester/Distributor: Add `cortex_cost_attribution_*` metrics to observe the state of the cost-attribution trackers. #11112
* [ENHANCEMENT] Querier: Process multiple remote read queries concurrently instead of sequentially for improved performance. #11732
* [ENHANCEMENT] gRPC/HTTP servers: Add `cortex_server_invalid_cluster_validation_label_requests_total` metric, that is increased for every request with an invalid cluster validation label. #11241 #11277
* [ENHANCEMENT] OTLP: Add support for converting OTel explicit bucket histograms to Prometheus native histograms with custom buckets using the `distributor.otel-convert-histograms-to-nhcb` flag. #11077
* [ENHANCEMENT] Add configurable per-tenant `limited_queries`, which you can only run at or less than an allowed frequency. #11097
* [ENHANCEMENT] Ingest-Storage: Add `ingest-storage.kafka.producer-record-version` to allow control Kafka record versioning. #11244
* [ENHANCEMENT] Ruler: Update `<prometheus-http-prefix>/api/v1/rules` and `<prometheus-http-prefix>/api/v1/alerts` to reply with HTTP error 422 if rule evaluation is completely disabled for the tenant. If only recording rule or alerting rule evaluation is disabled for the tenant, the response now includes a corresponding warning. #11321 #11495 #11511
* [ENHANCEMENT] Add tenant configuration block `ruler_alertmanager_client_config` which allows the Ruler's Alertmanager client options to be specified on a per-tenant basis. #10816
* [ENHANCEMENT] Distributor: Trace when deduplicating a metric's samples or histograms. #11159 #11715
* [ENHANCEMENT] Store-gateway: Retry querying blocks from store-gateways with dynamic replication until trying all possible store-gateways. #11354 #11398
* [ENHANCEMENT] Query-frontend: Add optional reason to blocked_queries config. #11407 #11434
* [ENHANCEMENT] Distributor: Gracefully handle type assertion of WatchPrefix in HA Tracker to continue checking for updates. #11411 #11461
* [ENHANCEMENT] Querier: Include chunks streamed from store-gateway in Mimir Query Engine memory estimate of query memory usage. #11453 #11465
* [ENHANCEMENT] Querier: Include chunks streamed from ingester in Mimir Query Engine memory estimate of query memory usage. #11457
* [ENHANCEMENT] Query-frontend: Add retry mechanism for remote reads, series, and cardinality prometheus endpoints #11533
* [ENHANCEMENT] Ruler: Ignore rulers in non-operation states when getting and syncing rules #11569
* [ENHANCEMENT] Query-frontend: add optional reason to blocked_queries config. #11407 #11434
* [ENHANCEMENT] Tracing: Add HTTP headers as span attributes when `-server.trace-request-headers` is enabled. You can configure which headers to exclude using the `-server.trace-request-headers-exclude-list` flag. #11655
* [ENHANCEMENT] Ruler: Add new per-tenant limit on minimum rule evaluation interval. #11665
* [ENHANCEMENT] store-gateway: download sparse headers on startup when lazy loading is enabled. #11686
* [ENHANCEMENT] Distributor: added more metrics to troubleshoot Kafka records production latency when experimental ingest storage is enabled: #11766 #11771
  * `cortex_ingest_storage_writer_produce_remaining_deadline_seconds`: measures the remaining deadline (in seconds) when records are requested to be produced.
  * `cortex_ingest_storage_writer_produce_records_enqueue_duration_seconds`: measures how long it takes to enqueue produced Kafka records in the client.
  * `cortex_ingest_storage_writer_kafka_write_wait_seconds`: measures the time spent waiting to write to Kafka backend.
  * `cortex_ingest_storage_writer_kafka_write_time_seconds`: measures the time spent writing to Kafka backend.
  * `cortex_ingest_storage_writer_kafka_read_wait_seconds`: measures the time spent waiting to read from Kafka backend.
  * `cortex_ingest_storage_writer_kafka_read_time_seconds`: measures the time spent reading from Kafka backend.
  * `cortex_ingest_storage_writer_kafka_request_duration_e2e_seconds`: measures the time from the start of when a Kafka request is written to the end of when the response for that request was fully read from the Kafka backend.
  * `cortex_ingest_storage_writer_kafka_request_throttled_seconds`: measures how long Kafka requests have been throttled by the Kafka client.
* [ENHANCEMENT] Distributor: Add per-user `cortex_distributor_sample_delay_seconds` to track delay of ingested samples with regard to wall clock. #11573
* [ENHANCEMENT] Distributor: added circuit breaker to not produce Kafka records at all if the context is already canceled / expired. This applied only when experimental ingest storage is enabled. #11768
* [ENHANCEMENT] Compactor: Optimize the planning phase for tenants with a very large number of blocks, such as tens or hundreds of thousands, at the cost of making it slightly slower for tenants with a very a small number of blocks. #11819
* [ENHANCEMENT] Query-frontend: Accurate tracking of samples processed from cache. #11719
* [ENHANCEMENT] Store-gateway: Change level 0 blocks to be reported as 'unknown/old_block' in metrics instead of '0' to improve clarity. Level 0 indicates blocks with metadata from before compaction level tracking was added to the bucket index. #11891
* [ENHANCEMENT] Compactor, distributor, ruler, scheduler and store-gateway: Makes `-<component-ring-config>.auto-forget-unhealthy-periods` configurable for each component. Deprecates the `-store-gateway.sharding-ring.auto-forget-enabled` flag. #11923
* [ENHANCEMENT] otlp: Stick to OTLP vocabulary on invalid label value length error. #11889
* [ENHANCEMENT] Ingester: Display user grace interval in the tenant list obtained through the `/ingester/tenants` endpoint. #11961
* [ENHANCEMENT] `kafkatool`: add `consumer-group delete-offset` command as a way to delete the committed offset for a consumer group. #11988
* [ENHANCEMENT] Block-builder-scheduler: Detect gaps in scheduled and completed jobs. #11867
* [ENHANCEMENT] Distributor: Experimental support for Prometheus Remote-Write 2.0 protocol has been updated. Created timestamps are now supported. This feature includes some limitations. If samples in a write request aren't ordered by time, the created timestamp might be dropped. Additionally, per-series metadata is automatically merged on the metric family level. Ingestion might fail if the client sends ProtoBuf fields out-of-order. The label `version` is added to the metric `cortex_distributor_requests_in_total` with a value of either `1.0` or `2.0`, depending on the detected remote-write protocol. #11977
* [ENHANCEMENT] Query-frontend: Added labels query optimizer that automatically removes redundant `__name__!=""` matchers from label names and label values queries, improving query performance. You can enable the optimizer per-tenant with the `labels_query_optimizer_enabled` runtime configuration flag. #12054 #12066 #12076 #12080
* [ENHANCEMENT] Query-frontend: Standardise non-regex patterns in query blocking upon loading of config. #12102
* [ENHANCEMENT] Ruler: Propagate GCS object mutation rate limit for rule group uploads. #12086
* [ENHANCEMENT] Stagger head compaction intervals across zones to prevent compactions from aligning simultaneously, which could otherwise cause strong consistency queries to fail when experimental ingest storage is enabled. #12090
* [ENHANCEMENT] Compactor: Add `-compactor.update-blocks-concurrency` flag to control concurrency for updating block metadata during bucket index updates, separate from deletion marker concurrency. #12117
* [ENHANCEMENT] Query-frontend: Allow users to set the `query-frontend.extra-propagated-headers` flag to specify the extra headers allowed to pass through to the rest of the query path. #12174
* [BUGFIX] OTLP: Fix response body and Content-Type header to align with spec. #10852
* [BUGFIX] Compactor: fix issue where block becomes permanently stuck when the Compactor's block cleanup job partially deletes a block. #10888
* [BUGFIX] Storage: fix intermittent failures in S3 upload retries. #10952
* [BUGFIX] Querier: return NaN from `irate()` if the second-last sample in the range is NaN and Prometheus' query engine is in use. #10956
* [BUGFIX] Ruler: don't count alerts towards `cortex_prometheus_notifications_dropped_total` if they are dropped due to alert relabelling. #10956
* [BUGFIX] Querier: Fix issue where an entire store-gateway zone leaving caused high CPU usage trying to find active members of the leaving zone. #11028
* [BUGFIX] Query-frontend: Fix blocks retention period enforcement when a request has multiple tenants (tenant federation). #11069
* [BUGFIX] Query-frontend: Fix `-query-frontend.query-sharding-max-sharded-queries` enforcement for instant queries with binary operators. #11086
* [BUGFIX] Memberlist: Fix hash ring updates before the full-join has been completed, when `-memberlist.notify-interval` is configured. #11098
* [BUGFIX] Query-frontend: Fix an issue where transient errors could be inadvertently cached. #11198
* [BUGFIX] Ingester: read reactive limiters should activate and deactivate when the ingester changes state. #11234
* [BUGFIX] Query-frontend: Fix an issue where errors from date/time parsing methods did not include the name of the invalid parameter. #11304
* [BUGFIX] Query-frontend: Fix a panic in monolithic mode caused by a clash in labels of the `cortex_client_invalid_cluster_validation_label_requests_total` metric definition. #11455
* [BUGFIX] Compactor: Fix issue where `MimirBucketIndexNotUpdated` can fire even though the index has been updated within the alert threshold. #11303
* [BUGFIX] Distributor: fix old entries in the HA Tracker with zero valued "elected at" timestamp. #11462
* [BUGFIX] Query-scheduler: Fix issue where deregistered querier goroutines can cause a panic if their backlogged dequeue requests are serviced. #11510
* [BUGFIX] Ruler: Failures during initial sync must be fatal for the service's startup. #11545
* [BUGFIX] Querier and query-frontend: Fix issue where aggregation functions like `topk` and `quantile` could return incorrect results if the scalar parameter is not a constant and Prometheus' query engine is in use. #11548
* [BUGFIX] Querier and query-frontend: Fix issue where range vector selectors could incorrectly ignore samples at the beginning of the range. #11548
* [BUGFIX] Querier: Fix rare panic if a query is canceled while a request to ingesters or store-gateways has just begun. #11613
* [BUGFIX] Ruler: Fix QueryOffset and AlignEvaluationTimeOnInterval being ignored when either recording or alerting rule evaluation is disabled. #11647
* [BUGFIX] Ingester: Fix issue where ingesters could leave read-only mode during forced compactions, resulting in write errors. #11664
* [BUGFIX] Ruler: Fix rare panic when the ruler is shutting down. #11781
* [BUGFIX] Block-builder-scheduler: Fix data loss bug in job assignment. #11785
* [BUGFIX] Compactor: start tracking `-compactor.max-compaction-time` after the initial compaction planning phase, to avoid rare cases where planning takes longer than `-compactor.max-compaction-time` and so actual compaction never runs for a tenant. #11834
* [BUGFIX] Distributor: Validate the RW2 symbols field and reject invalid requests that don't have an empty string as the first symbol. #11953
* [BUGFIX] Distributor: Check `max_inflight_push_requests_bytes` before decompressing incoming requests. #11967
* [BUGFIX] Query-frontend: Allow limit parameter to be 0 in label queries to explicitly request unlimited results. #12054
* [BUGFIX] Distributor: Fix a possible panic in the OTLP push path while handling a gRPC status error. #12072
* [BUGFIX] Query-frontend: Evaluate experimental duration expressions before sharding, splitting, and caching. Otherwise, the result is not correct. #12038
* [BUGFIX] Block-builder-scheduler: Fix bugs in handling of partitions with no commit. #12130
* [BUGFIX] Ingester: Fix issue where ingesters can exit read-only mode during idle compactions, resulting in write errors. #12128
* [BUGFIX] otlp: Reverts #11889 which has a pooled memory re-use bug. #12266

### Mixin

* [CHANGE] Alerts: Update the query for `MimirBucketIndexNotUpdated` to use `max_over_time` to prevent alert firing when pods rotate. #11311, #11426
* [CHANGE] Alerts: Make alerting threshold for `DistributorGcUsesTooMuchCpu` configurable. #11508
* [CHANGE] Remove support for the experimental read-write deployment mode. #11975
* [CHANGE] Alerts: Replace namespace with job label in golang_alerts. #11957
* [FEATURE] Add an alert if the block-builder-scheduler detects that it has skipped data. #12118
* [ENHANCEMENT] Dashboards: Include absolute number of notifications attempted to alertmanager in 'Mimir / Ruler'. #10918
* [ENHANCEMENT] Alerts: Make `MimirRolloutStuck` a critical alert if it has been firing for 6h. #10890
* [ENHANCEMENT] Dashboards: Add panels to the `Mimir / Tenants` and `Mimir / Top Tenants` dashboards showing the rate of gateway requests. #10978
* [ENHANCEMENT] Alerts: Improve `MimirIngesterFailsToProcessRecordsFromKafka` to not fire during forced TSDB head compaction. #11006
* [ENHANCEMENT] Alerts: Add alerts for invalid cluster validation labels. #11255 #11282 #11413
* [ENHANCEMENT] Dashboards: Improve "Kafka 100th percentile end-to-end latency when ingesters are running (outliers)" panel, computing the baseline latency on `max(10, 10%)` of ingesters instead of a fixed 10 replicas. #11581
* [ENHANCEMENT] Dashboards: Add "per-query memory consumption" and "fallback to Prometheus' query engine" panels to the Queries dashboard. #11626
* [ENHANCEMENT] Alerts: Add `MimirGoThreadsTooHigh` alert. #11836 #11845
* [ENHANCEMENT] Dashboards: Add autoscaling row for ruler query-frontends to `Mimir / Remote ruler reads` dashboard. #11838
* [BUGFIX] Dashboards: fix "Mimir / Tenants" legends for non-Kubernetes deployments. #10891
* [BUGFIX] Dashboards: fix Query-scheduler RPS panel legend in "Mimir / Reads". #11515
* [BUGFIX] Recording rules: fix `cluster_namespace_deployment:actual_replicas:count` recording rule when there's a mix on single-zone and multi-zone deployments. #11287
* [BUGFIX] Alerts: Enhance the `MimirRolloutStuck` alert, so it checks whether rollout groups as a whole (and not spread across instances) are changing or stuck. #11288

### Jsonnet

* [CHANGE] Increase the allowed number of rule groups for small, medium_small, and extra_small user tiers by 20%. #11152
* [CHANGE] Update rollout-operator to latest release. #11232 #11748
* [CHANGE] Memcached: Set a timeout of `500ms` for the `ruler-storage` cache instead of the default `200ms`. #11231
* [CHANGE] Ruler: If ingest storage is enabled, set the maximum buffered bytes in the Kafka client used by the ruler based on the expected maximum rule evaluation response size, clamping it between 1 GB (default) and 4 GB. #11602
* [CHANGE] All: Environment variable `JAEGER_REPORTER_MAX_QUEUE_SIZE` is no longer set. Components will use OTel's default value of `2048` unless explicitly configured. You can still configure `JAEGER_REPORTER_MAX_QUEUE_SIZE` if you configure tracing using Jaeger env vars, and you can always set `OTEL_BSP_MAX_QUEUE_SIZE` OTel configuration. #11700
* [CHANGE] Removed jaeger-agent-mixin and `_config.jaeger_agent_host` configuration. You can configure tracing using an OTLP endpoint through `_config.otlp_traces_endpoint`, see `tracing.libsonnet` for more configuration options. #11773
* [CHANGE] Removed `ingester_stream_chunks_when_using_blocks` option. #11711
* [CHANGE] Enable `memberlist.abort-if-fast-join-fails` for ingesters using memberlist #11931 #11950
* [CHANGE] Remove average per-pod series scaling trigger for ingest storage ingester HPA and use one based on max owned series instead. #11952
* [CHANGE] Add `store_gateway_grpc_max_query_response_size_bytes` config option to set the max store-gateway gRCP query response send size (and corresponsing querier receive size), and set to 200MB by default. #11968
* [CHANGE] Removed support for the experimental read-write deployment mode. #11974
* [FEATURE] Make ingest storage ingester HPA behavior configurable through `_config.ingest_storage_ingester_hpa_behavior`. #11168
* [FEATURE] Add an alternate ingest storage HPA trigger that targets maximum owned series per pod. #11356
* [FEATURE] Make tracing of HTTP headers as span attributes configurable through `_config.trace_request_headers`. You can exclude certain headers from being traced using `_config.trace_request_exclude_headers_list`. #11655 #11714
* [FEATURE] Allow configuring tracing with OTel environment variables through `$._config.otlp_traces_endpoint`. When configured, the `$.jaeger_mixin` is no longer available for use. #11773 #11981 #12074
* [FEATURE] Updated rollout-operator to support `OTEL_` environment variables for tracing. #11787
* [ENHANCEMENT] Add `query_frontend_only_args` option to specify CLI flags that apply only to query-frontends but not ruler-query-frontends. #11799
* [ENHANCEMENT] Make querier scale up (`$_config.autoscaling_querier_scaleup_percent_cap`) and scale down rates (`$_config.autoscaling_querier_scaledown_percent_cap`) configurable. #11862
* [ENHANCEMENT] Set resource requests and limits for the Memcached Prometheus exporter. #11933 #11946
* [ENHANCEMENT] Add assertion to ensure ingester ScaledObject has minimum and maximum replicas set to a value greater than 0. #11979
* [ENHANCEMENT] Add `ingest_storage_migration_ignore_ingest_storage_errors` and `ingest_storage_migration_ingest_storage_max_wait_time` configs to control error handling of the partition ingesters during ingest storage migrations. #12105
* [ENHANCEMENT] Add block-builder job processing duration timings and offset-skipped errors to the Block-builder dashboard. #12118
* [BUGFIX] Honor `weight` argument when building memory HPA query for resource scaled objects. #11935

### Mimirtool

* [FEATURE] Add `--enable-experimental-functions` flag to commands that parse PromQL to allow parsing experimental functions such as `sort_by_label()`.
* [ENHANCEMENT] Add `--block-size` CLI flag to `remote-read export` that allows setting the output block size. #12025
* [BUGFIX] Fix issue where `remote-read` doesn't behave like other mimirtool commands for authentication. #11402
* [BUGFIX] Fix issue where `remote-read export` could omit some samples if the query time range spans multiple blocks. #12025
* [BUGFIX] Fix issue where `remote-read export` could omit some output blocks in the list printed to the console or fail with `read/write on closed pipe`. #12025

### Mimir Continuous Test

* [FEATURE] Add `-tests.client.cluster-validation.label` flag to send the `X-Cluster` header with queries. #11418

### Query-tee

### Documentation

* [ENHANCEMENT] Update Thanos to Mimir migration guide with a tip to add the `__tenant_id__` label. #11584
* [ENHANCEMENT] Update the `MimirIngestedDataTooFarInTheFuture` runbook with a note about false positives and the endpoint to flush TSDB blocks by user. #11961

### Tools

* [ENHANCEMENT] `kafkatool`: Add `offsets` command for querying various partition offsets. #11115
* [ENHANCEMENT] `listblocks`: Output can now also be JSON or YAML for easier parsing. #11184
* [ENHANCEMENT] `mark-blocks`: Allow specifying blocks from multiple tenants. #11343
* [ENHANCEMENT] `undelete-blocks`: Support removing S3 delete markers to avoid copying data when recovering blocks. #11256
* [BUGFIX] `screenshots`: Update to tar-fs v3.1.0 to address [CVE-2025-48387](https://nvd.nist.gov/vuln/detail/CVE-2025-48387). #12030


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.16.1...mimir-2.17.0


================================================================================

# 2.17.1

Tag: mimir-2.17.1
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.17.1

This release contains 7 PRs from 5 authors. Thank you!

# Changelog

## 2.17.1

### Grafana Mimir

* [BUGFIX] Ingester: Fix a bug ingesters would get stuck in read-only mode after compactions. #12538
* [BUGFIX] Update to Go v1.24.6 to address [CVE-2025-4674](https://www.cve.org/CVERecord?id=CVE-2025-4674), [CVE-2025-47907](https://www.cve.org/CVERecord?id=CVE-2025-47907). #12580


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.17.0...mimir-2.17.1


================================================================================

# 2.17.2

Tag: mimir-2.17.2
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.17.2

This release contains 11 PRs from 6 authors. Thank you!

# Changelog

## 2.17.2

### Grafana Mimir

* [BUGFIX] Add a missing attribute to the list of default promoted OTel resource attributes in the docs: deployment.environment. #12181
* [BUGFIX] Ingest: Fix memory pool poisoning in Remote-Write 2.0/OTLP by not cleaning created timestamp field before returning time series to the memory pool. #12735
* [BUGFIX] Distributor: Fix error when native histograms bucket limit is set then no NHCB passes validation. #12746
* [BUGFIX] Update Docker base images for tools from `alpine:3.22.1` to `alpine:3.22.2` to address [CVE-2025-9230](https://nvd.nist.gov/vuln/detail/CVE-2025-9230), [CVE-2025-9231](https://nvd.nist.gov/vuln/detail/CVE-2025-9231), [CVE-2025-2025-9232](https://nvd.nist.gov/vuln/detail/CVE-2025-9232). #12993
* [BUGFIX] Memcached: Ignore invalid responses when discovering cache servers using `dnssrv+` or `dnssrvnoa+` service discovery prefixes. #13206

### Tools

* [ENHANCEMENT] Base `mimirtool`, `metaconvert`, `copyblocks`, and `query-tee` images on `distroless/static-debian12`. #13014


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.17.1...mimir-2.17.2


================================================================================

# 2.17.3

Tag: mimir-2.17.3
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.17.3

This release contains 11 PRs from 4 authors. Thank you!

# Changelog

## 2.17.3

### Grafana Mimir

* [BUGFIX] Update to Go v1.25.4 to address [CVE-2025-61725](https://www.cve.org/CVERecord?id=CVE-2025-61725), [CVE-2025-58188](https://www.cve.org/CVERecord?id=CVE-2025-58188). #13697


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.17.2...mimir-2.17.3


================================================================================

# 2.17.4

Tag: mimir-2.17.4
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.17.4

This release contains 5 PRs from 2 authors. Thank you!

# Changelog

## 2.17.4

### Grafana Mimir

* [BUGFIX] Update to Go v1.25.5 to address [CVE-2025-61729](https://pkg.go.dev/vuln/GO-2025-4155), [CVE-2025-61727](https://pkg.go.dev/vuln/GO-2025-4175). #13755, #13896


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.17.3...mimir-2.17.4


================================================================================

# 2.17.5

Tag: mimir-2.17.5
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.17.5

This release contains 8 PRs from 5 authors. Thank you!

# Changelog

## 2.17.5

### Grafana Mimir

* [BUGFIX] Distributor: Calculate `WriteResponseStats` before validation and `PushWrappers`. This prevents clients using Remote-Write 2.0 from seeing a diff in written samples, histograms and exemplars. #12682 #14144
* [BUGFIX] Distributor: Fix issue where distributors didn't send custom values of native histograms. #13849 #14145
* [BUGFIX] Distributor: Fix metric metadata of type Unknown being silently dropped from RW2 requests. #12461 #14150
* [BUGFIX] Ingester: Query all ingesters when shuffle sharding is disabled. #14041


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.17.4...mimir-2.17.5


================================================================================

# 2.17.6

Tag: mimir-2.17.6
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.17.6

This release contains 8 PRs from 3 authors. Thank you!

# Changelog

## 2.17.6

### Grafana Mimir

* [BUGFIX] Update to Go v1.25.7 to address [CVE-2025-61726](https://pkg.go.dev/vuln/GO-2026-4341). #14243 #14255
* [BUGFIX] Ruler: Add path traversal checks when parsing namespaces and groups, which prevents namespace and group name from containing non-local paths. #14246


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.17.5...mimir-2.17.6


================================================================================

# 2.17.7

Tag: mimir-2.17.7
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.17.7

This release contains 3 PRs from 2 authors. Thank you!

# Changelog

## 2.17.7

### Grafana Mimir

* [BUGFIX] Update go.opentelemetry.io/otel/sdk to v1.40.0 to address [CVE-2026-24051](https://nvd.nist.gov/vuln/detail/CVE-2026-24051) #14432


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.17.6...mimir-2.17.7


================================================================================

# 2.17.8

Tag: mimir-2.17.8
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.17.8

This release contains 4 PRs from 3 authors. Thank you!

# Changelog

## 2.17.8

### Grafana Mimir

* [BUGFIX] Update module google.golang.org/grpc to v1.79.3 to address [CVE-2026-33186](https://nvd.nist.gov/vuln/detail/CVE-2026-33186) #14762


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.17.7...mimir-2.17.8


================================================================================

# 2.17.9

Tag: mimir-2.17.9
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.17.9

This release contains 2 PRs from 1 authors. Thank you!

# Changelog

## 2.17.9

### Grafana Mimir

* [BUGFIX] Update to Go v1.25.8 to address [CVE-2026-27142](https://pkg.go.dev/vuln/GO-2026-4603), [CVE-2026-27139](https://pkg.go.dev/vuln/GO-2026-4602), [CVE-2026-25679](https://pkg.go.dev/vuln/GO-2026-4601), [CVE-2026-27138](https://pkg.go.dev/vuln/GO-2026-4600), [CVE-2026-27137](https://pkg.go.dev/vuln/GO-2026-4599). #14908


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.17.8...mimir-2.17.9


================================================================================

# 2.17.10

Tag: mimir-2.17.10
URL: https://github.com/grafana/mimir/releases/tag/mimir-2.17.10

## What's Changed

* chore(deps): update module github.com/go-jose/go-jose/v4 to v4.1.4 [security] (release-2.17) by @renovate-sh-app[bot] in https://github.com/grafana/mimir/pull/14918
* [release 2.17] Backport of ruler: Fix rule expressions with leading newlines failing to parse by @zenador in https://github.com/grafana/mimir/pull/15032
* [2.17] Upgrade to Go 1.25.9 by @tcard in https://github.com/grafana/mimir/pull/15042
* [2.17] Update deps to address vulnerabilities by @tcard in https://github.com/grafana/mimir/pull/15050

**Full Changelog**: https://github.com/grafana/mimir/compare/mimir-2.17.9...mimir-2.17.10


================================================================================

# 3.0.0

Tag: mimir-3.0.0
URL: https://github.com/grafana/mimir/releases/tag/mimir-3.0.0

This release contains 590 PRs from 62 authors, including new contributors Andrew Hall, Frank Kloeker, Gregor Zeitlinger, Ilia Lazebnik, Julien, Maruth Goyal, Matt Clegg, Mattia Barbon, Mohijeet, Oleg Vorobev, Oliver Herrmann, Phil Kates, Pranshu Raj, Rob B, Timon Engelke, Vadim Stepanov, dannyc-grafana, renovate-sh-app[bot], unkls ben. Thank you!

# Grafana Mimir version 3.0.0 release notes


Grafana Labs is excited to announce version 3.0 of Grafana Mimir.

The highlights that follow include the top features, enhancements, and bug fixes in this release. For the complete list of changes, refer to the [CHANGELOG](https://github.com/grafana/mimir/blob/main/CHANGELOG.md).

## Features and enhancements

Grafana Mimir version 3.0 includes the following key features and enhancements.

### Ingest storage architecture

Mimir 3.0 introduces ingest storage architecture, a next-generation architecture that separates the read and write paths using a Kafka-based ingest storage layer. In previous versions, the ingester handled both ingestion and querying, which could cause contention under heavy query loads. By introducing Kafka as an asynchronous buffer between ingestion and query, reads and writes now scale independently. This design improves ingestion stability, query performance, and operational flexibility for large deployments.

Note that in Grafana Mimir version 3.0, classic architecture is still supported.

### Mimir Query Engine (MQE)

The Mimir Query Engine (MQE) is now the default query engine for all queriers and query-frontends. MQE is fully PromQL-compatible and processes data in a streaming fashion, reducing peak memory usage by up to 92% compared to the Prometheus engine. You can expect faster, more stable query performance and lower resource consumption under load.

### Additional improvements

Grafana Mimir 3.0 also includes:

- Optimizations to MQE for histogram queries and query rewrites
- Improvements to query planning in frontends and queriers
- General stability and performance updates across core components

## Important changes

Grafana Mimir 3.0 introduces several updates that change default behavior and configuration. Review these changes before upgrading:

- Ingest storage architecture: Grafana Mimir now uses a Kafka-based ingest storage layer that separates reads and writes. This change improves performance by altering data flow between components.
- MQE as the default engine: MQE replaces the Prometheus engine as the default query engine. To continue using the Prometheus engine, set `-querier.query-engine=prometheus`.
- Removal of experimental features: Some deprecated and experimental flags, including the read-write deployment mode, have been removed.
- Configuration updates: Some deprecated CLI flags and configuration options have been removed or renamed.

## Experimental features

Grafana Mimir 3.0 includes some features that are experimental and disabled by default. Use these features with caution and report any issues that you encounter:

- Prometheus Remote-Write 2.0 protocol
- PromQL duration expressions that allow simple arithmetic in range or offset values
- Cluster validation for HTTP requests (`-server.cluster-validation.*` flags)
- Native OTLP delta metric ingestion (`-distributor.otel-native-delta-ingestion`)

## Bug fixes

For a detailed list of bug fixes, refer to the [CHANGELOG](https://github.com/grafana/mimir/blob/main/CHANGELOG.md).

### Helm chart improvements

The Grafana Mimir Helm chart is released independently. Refer to the [Grafana Mimir Helm chart documentation](https://grafana.com/docs/helm-charts/mimir-distributed/latest/).


# Changelog

## 3.0.0

### Grafana Mimir

* [CHANGE] Build: Include updated Mozilla CA bundle from Debian Testing. #12247
* [CHANGE] Query-frontend: Add support for UTF-8 label and metric names in `/api/v1/cardinality/{label_values|label_values|active_series}` endpoints. #11848.
* [CHANGE] Querier: Add support for UTF-8 label and metric names in `label_join`, `label_replace` and `count_values` PromQL functions. #11848.
* [CHANGE] Remove support for Redis as a cache backend. #12163
* [CHANGE] Memcached: Remove experimental `-<prefix>.memcached.addresses-provider` flag to use alternate DNS service discovery backends. The more reliable backend introduced in 2.16.0 (#10895) is now the default. As a result of this change, DNS-based cache service discovery no longer supports search domains. #12175 #12385
* [CHANGE] Query-frontend: Remove the CLI flag `-query-frontend.downstream-url` and corresponding YAML configuration and the ability to use the query-frontend to proxy arbitrary Prometheus backends. #12191 #12517
* [CHANGE] Query-frontend: Remove experimental instant query splitting feature. #12267
* [CHANGE] Query-frontend, querier: Replace `query-frontend.prune-queries` flag with `querier.mimir-query-engine.enable-prune-toggles` as pruning middleware has been moved into MQE. #12303 #12375
* [CHANGE] Distributor: Remove deprecated global HA tracker timeout configuration flags. #12321
* [CHANGE] Query-frontend: Use the Mimir Query Engine (MQE) by default. #12361
* [CHANGE] Query-frontend: Remove the CLI flags `-querier.frontend-address`, `-querier.max-outstanding-requests-per-tenant`, and `-query-frontend.querier-forget-delay` and corresponding YAML configurations. This is part of a change that makes the query-scheduler a required component. This removes the ability to run the query-frontend with an embedded query-scheduler. Instead, you must run a dedicated query-scheduler component. #12200
* [CHANGE] Ingester: Remove deprecated `-ingester.stream-chunks-when-using-blocks` CLI flag and `ingester_stream_chunks_when_using_blocks` runtime configuration option. #12615
* [CHANGE] Querier: Require non-zero values for `-querier.streaming-chunks-per-ingester-buffer-size` and `-querier.streaming-chunks-per-store-gateway-buffer-size` CLI flags and corresponding YAML configurations. This is part of a change that makes streaming required between queriers, ingesters, and store-gateways. Streaming has been the default since Mimir 2.14. #12790 #12818 #12897 #12929 #12973
* [CHANGE] Remove support for the experimental read-write deployment mode. #12584
* [CHANGE] Store-gateway: Update default value of `-store-gateway.dynamic-replication.multiple` to `5` to increase replication of recent blocks. #12433
* [CHANGE] Cost attribution: Reduce the default maximum per-user cardinality of cost attribution labels to 2000. #12625
* [CHANGE] Querier, query-frontend: Add `_total` suffix to `cortex_mimir_query_engine_common_subexpression_elimination_duplication_nodes_introduced`, `cortex_mimir_query_engine_common_subexpression_elimination_selectors_eliminated` and `cortex_mimir_query_engine_common_subexpression_elimination_selectors_inspected` metric names. #12636
* [CHANGE] Distributor: Remove the experimental setting `service_overload_status_code_on_rate_limit_enabled` which used an HTTP 529 error (non-standard) instead of HTTP 429 for rate limiting. #13012
* [CHANGE] Alertmanager: Change the severity for InitialSyncFailed from 'critical' to 'warning'. #12824
* [CHANGE] Ingester: Renamed experimental reactive limiter options. #12773
* [CHANGE] Distributor: gRPC errors with the `mimirpb.ERROR_CAUSE_INSTANCE_LIMIT` cause are now mapped to `codes.Unavailable` and `http.StatusServiceUnavailable` instead of `codes.Internal` and `http.StatusInternalServerError`. #13003 #13032
* [CHANGE] Admin: use relative links instead of absolute ones in the administration web UI. #13034
* [CHANGE] Distributor: Use memberlist by default for the HA tracker. #12998
* [CHANGE] Block-builder: Remove `cortex_blockbuilder_process_partition_duration_seconds` metric and related dashboard panels. #12631
* [FEATURE] Ingester: Expose the number of active series ingested via OTLP as `cortex_ingester_active_otlp_series`. #12678
* [FEATURE] Distributor, ruler: Add experimental `-validation.name-validation-scheme` flag to specify the validation scheme for metric and label names. #12215
* [FEATURE] Ruler: Add support to use a Prometheus-compatible HTTP endpoint for remote rule evaluation. See [remote evaluation mode](https://grafana.com/docs/mimir/latest/operators-guide/architecture/components/ruler/#remote-over-http-https) for more details. This feature can be used to federate data from multiple Mimir instances. #11415 #11833
* [FEATURE] Distributor: Add experimental `-distributor.otel-translation-strategy` flag to support configuring the metric and label name translation strategy in the OTLP endpoint. #12284 #12306 #12369
* [FEATURE] Query-frontend: Add `query-frontend.rewrite-propagate-matchers` flag that enables a new MQE AST optimization pass that copies relevant label matchers across binary operations. #12304
* [FEATURE] Query-frontend: Add `query-frontend.rewrite-histogram-queries` flag that enables a new MQE AST optimization pass that rewrites histogram queries for a more efficient order of execution. #12305
* [FEATURE] Query-frontend: Support delayed name removal (Prometheus experimental feature) in MQE. #12509
* [FEATURE] Usage-tracker: Introduce a new experimental service to enforce active series limits before Kafka ingestion. #12358 #12895 #12940 #12942 #12970 #13085
* [FEATURE] Ingester: Add experimental `-include-tenant-id-in-profile-labels` flag to include tenant ID in pprof profiling labels for sampled traces. Currently only supported by the ingester. This can help debug performance issues for specific tenants. #12404
* [FEATURE] Alertmanager: Add experimental `-alertmanager.storage.state-read-timeout` flag to configure the timeout for reading the Alertmanager state (notification log, silences) from object storage during the initial sync. #12425
* [FEATURE] Ingester: Add experimental `-blocks-storage.tsdb.index-lookup-planning.*` flags to configure use of a cost-based index lookup planner. This should reduce the cost of queries in the ingester. #12197 #12199 #12245 #12248 #12457 #12530 #12407 #12460 #12550 #12597 #12603 #12608 #12658 #12696 #12731 #12755 #12738 #12752 #12807 #12830 #12896 #13039
* [FEATURE] MQE: Add support for applying extra selectors to one side of a binary operation to reduce data fetched. #12577
* [FEATURE] Query-frontend: Add a native histogram presenting the length of query expressions handled by the query-frontend #12571
* [FEATURE] Query-frontend and querier: Add experimental support for performing query planning in query-frontends and distributing portions of the plan to queriers for execution. #12302 #12551 #12665 #12687 #12745 #12757 #12798 #12808 #12809 #12835 #12856 #12870 #12883 #12885 #12886 #12911 #12933 #12934 #12961 #13016 #13027
* [FEATURE] Alertmanager: add Microsoft Teams V2 as a supported integration. #12680
* [FEATURE] Distributor: Add experimental flag `-validation.label-value-length-over-limit-strategy` to configure how to handle label values over the length limit. #12627 #12844
* [FEATURE] Ingester: Introduce metric `cortex_ingester_owned_target_info_series` for counting the number of owned `target_info` series by tenant. #12681
* [FEATURE] MQE: Add support for step invariant expression handling in query planning and evaluation. #12931
* [FEATURE] MQE: Add support for experimental `ts_of_min_over_time`, `ts_of_max_over_time`, `ts_of_first_over_time` and `ts_of_last_over_time` PromQL functions. #12819
* [FEATURE] Ingester: Add experimental flags `-ingest-storage.write-logs-fsync-before-kafka-commit-enabled` and `-ingest-storage.write-logs-fsync-before-kafka-commit-concurrency` to fsync write logs before the offset is committed to Kafka. This is enabled by default. #12816
* [FEATURE] MQE: Add support for experimental `mad_over_time` PromQL function. #12995
* [FEATURE] Continuous test: Add experimental `-tests.ingest-storage-record.enabled` flag to verify ingest-storage record correctness by validating the V2 record format against live write requests. #12500
* [ENHANCEMENT] Query-frontend: CLI flag `-query-frontend.enabled-promql-experimental-functions` and its associated YAML configuration is now stable. #12368
* [ENHANCEMENT] Query-scheduler/query-frontend: Add native histogram definitions to `cortex_query_{scheduler|frontend}_queue_duration_seconds`. #12288
* [ENHANCEMENT] Querier: Add native histogram definition to `cortex_bucket_index_load_duration_seconds`. #12094
* [ENHANCEMENT] Query-frontend: Allow users to set the `query-frontend.extra-propagated-headers` flag to specify the extra headers allowed to pass through to the rest of the query path. #12174
* [ENHANCEMENT] MQE: Add support for applying common subexpression elimination to range vector expressions in instant queries. #12236
* [ENHANCEMENT] Ingester: Improve the performance of active series custom trackers matchers. #12184
* [ENHANCEMENT] Ingester: Add postings cache sharing and invalidation. You can enable sharing and head cache invalidation via `-blocks-storage.tsdb.shared-postings-for-matchers-cache` and `-blocks-storage.tsdb.head-postings-for-matchers-cache-invalidation` respectively, and you can configure the number of metric versions per cache via `-blocks-storage.tsdb.head-postings-for-matchers-cache-versions`. #12333 #12932
* [ENHANCEMENT] Overrides-exporter: The overrides-exporter can now export arbitrary fields from the limits configuration. Metric names are automatically discovered from YAML tags in the limits structure, eliminating the need to maintain hardcoded lists when adding new exportable metrics. #12244
* [ENHANCEMENT] OTLP: Stick to OTLP vocabulary on invalid label value length error. #12273
* [ENHANCEMENT] Elide SeriesChunksStreamReader.StartBuffering span on queries; show as events on parent span. #12257
* [ENHANCEMENT] Ruler: Add `-ruler.max-notification-batch-size` CLI flag that can be used to configure the maximum Alertmanager notification batch size. #12469
* [ENHANCEMENT] Ingester: Skip read path load shedding when an ingester is the only available replica. #12448
* [ENHANCEMENT] Querier: Include more information about inflight queries in the activity tracker. A querier logs this information after it restarts following a crash. #12526
* [ENHANCEMENT] Ruler: Add native histogram version of `cortex_ruler_sync_rules_duration_seconds`. #12628
* [ENHANCEMENT] Block-builder: Implement concurrent consumption within a job when `-ingest-storage.kafka.fetch-concurrency-max` is given. #12222
* [ENHANCEMENT] Query-frontend: Labels query optimizer is no longer experimental and is enabled by default. It can be disabled with `-query-frontend.labels-query-optimizer-enabled=false` CLI flag. #12606
* [ENHANCEMENT] Distributor: Add value length to "label value too long" error. #12583
* [ENHANCEMENT] Distributor: The metric `cortex_distributor_uncompressed_request_body_size_bytes` now differentiates by the handler serving the request. #12661
* [ENHANCEMENT] Query-frontend, querier: Add support for experimental `first_over_time` PromQL function. #12662
* [ENHANCEMENT] OTLP: native support for OpenTelemetry metric start time to Prometheus metric created timestamp conversion, instead of converting to QuietZeroNaNs introduced in #10238. The configuration parameter `-distributor.otel-start-time-quiet-zero` is therefore deprecated and will be removed. Now supports start time for exponential histograms. This is a major rewrite of the endpoint in upstream Prometheus and Mimir. #12652
* [ENHANCEMENT] Distributor: Support zstd decompression of OTLP messages. #12229
* [ENHANCEMENT] Distributor: Optimize Remote Write 1.0 to 2.0 translation by improving symbolization and reducing allocations. #12329
* [ENHANCEMENT] Ingester: Improved the performance of active series custom trackers matchers. #12663
* [ENHANCEMENT] Compactor: Log sizes of downloaded and uploaded blocks. #12656
* [ENHANCEMENT] Block-builder-scheduler: The scheduler now handles multiple concurrent jobs within a partition if allowed by `-block-builder-scheduler.max-jobs-per-partition`. #12772
* [ENHANCEMENT] Ingester: Add `cortex_ingest_storage_reader_receive_and_consume_delay_seconds` metric tracking the time between when a write request is received in the distributor and its content is ingested in ingesters, when the ingest storage is enabled. #12751
* [ENHANCEMENT] Ruler: Add `ruler_evaluation_consistency_max_delay` per-tenant configuration option support, to specify the maximum tolerated ingestion delay for eventually consistent rule evaluations. This feature is used only when ingest storage is enabled. By default, no maximum delay is enforced. #12751
* [ENHANCEMENT] Ingester: Export `cortex_attributed_series_overflow_labels` metric on the `/usage-metrics` metrics endpoint with the configured cost-attribution labels set to overflow value. #12846
* [ENHANCEMENT] Usage stats: Report ingest-storage mode as part of usage statistics. #12753
* [ENHANCEMENT] All: Add cluster validation flag `-server.cluster-validation.additional-labels` configuration support, to accept multiple cluster labels during cluster migrations. #12850
* [ENHANCEMENT] Distributor: Add new optional config flag `distributor.ha-tracker.failover-sample-timeout` for HA tracker as an additional failover timeout check based on sample time instead of server time. #12331
* [ENHANCEMENT] Distributor: Add reactive concurrency limiters to protect push operations from overload. #12923 #13003 #13033
* [ENHANCEMENT] Ingester: Add experimental matcher set reduction to cost-based lookup planning. #12831
* [ENHANCEMENT] Ruler: Add `reason` label to `cortex_prometheus_rule_evaluation_failures_total` metric to distinguish between "user" and "operator" errors. #12971
* [ENHANCEMENT] Update Docker base images from `alpine:3.22.1` to `alpine:3.22.2`. #12991
* [ENHANCEMENT] Ruler: Add the `ruler_max_rule_evaluation_results` per-tenant configuration option to limit the maximum number of alerts an alerting rule or series a recording rule can produce for the group. By default, no limit is enforced. #12832
* [ENHANCEMENT] Jsonnet: Changed the default KV store for the HA tracker from etcd to memberlist. Etcd and Consul are now deprecated for HA tracker usage but remain supported for backward compatibility. #13000
* [ENHANCEMENT] Querier: prefer querying ingesters and store-gateways in a specific zone when `-querier.prefer-availability-zone` is configured. Added the following metrics tracking the data transfer between the querier and ingesters / store-gateways respectively: #13045
  * `cortex_ingester_client_transferred_bytes_total{ingester_zone="..."}`
  * `cortex_storegateway_client_transferred_bytes_total{store_gateway_zone="..."}`
* [ENHANCEMENT] Compactor: Add experimental `-compactor.first-level-compaction-skip-future-max-time` flag to skip first-level compaction if any source block has a MaxTime more recent than the wait period threshold. #13040
* [ENHANCEMENT] Block-builder-scheduler: Add gap monitoring for planned and completed jobs via `cortex_blockbuilder_scheduler_job_gap_detected` metric. #11867
* [BUGFIX] Distributor: Calculate `WriteResponseStats` before validation and `PushWrappers`. This prevents clients using Remote-Write 2.0 from seeing a diff in written samples, histograms and exemplars. #12682
* [BUGFIX] Compactor: Fix cortex_compactor_block_uploads_failed_total metric showing type="unknown". #12477
* [BUGFIX] Querier: Samples with the same timestamp are merged deterministically. Previously, this could lead to flapping query results when an out-of-order sample is ingested that conflicts with a previously ingested in-order sample's value. #8673
* [BUGFIX] Store-gateway: Fix potential goroutine leak by passing the scoped context in LabelValues. #12048
* [BUGFIX] Distributor: Fix pooled memory reuse bug that can cause corrupt data to appear in the err-mimir-label-value-too-long error message. #12266
* [BUGFIX] Querier: Fix timeout responding to query-frontend when response size is very close to `-querier.frontend-client.grpc-max-send-msg-size`. #12261
* [BUGFIX] Block-builder-scheduler: Fix a caching bug in initial job probing causing excessive memory usage at startup. #12389
* [BUGFIX] Ruler: Support labels at the rule group level. These were previously ignored even when set via the API. #12397
* [BUGFIX] Distributor: Fix metric metadata of type Unknown being silently dropped from RW2 requests. #12461
* [BUGFIX] Distributor: Preserve inconsistent metric metadata in Remote Write 1.0 to 2.0 conversion. Previously, when converting RW1.0 requests with multiple different metadata for the same series, only the first metadata was kept. Now all inconsistent metadata are preserved to match Prometheus behavior. This only affects experimental Remote Write 2.0. #12541 #12804
* [BUGFIX] Ruler: Fix ruler remotequerier request body consumption on retries. #12514
* [BUGFIX] Block-builder: Fix a bug where a consumption error can cause a job to stay assigned to a worker for the remainder of its lifetime. #12522
* [BUGFIX] Querier: Fix possible panic when evaluating a nested subquery where the parent has no steps. #12524
* [BUGFIX] Querier: Fix bug where the pruning toggles AST optimization pass doesn't work in the query planner. #12783
* [BUGFIX] Ingester: Fix a bug where prepare-instance-ring-downscale endpoint would return an error while compacting and not read-only. #12548
* [BUGFIX] Block-builder: Fix a bug where lease renewals would cease during graceful shutdown, leading to an elevated rate of job reassignments. #12643
* [BUGFIX] OTLP: Return HTTP OK for partially rejected requests, e.g. due to OOO exemplars. #12579
* [BUGFIX] Store-gateway: Fix a panic in BucketChunkReader when chunk loading encounter a broken chunk length. #12693 #12729
* [BUGFIX] Ingester, Block-builder: silently ignore duplicate sample if it's due to zero sample from created timestamp. Created timestamp equal to the timestamp of the first sample of series is a common case if created timestamp comes from OTLP where start time equal to timestamp of the first sample simply means unknown start time. #12726
* [BUGFIX] Distributor: Fix error when native histograms bucket limit is set then no NHCB passes validation. #12741
* [BUGFIX] Ingester: Fix continous reload of active series counters when cost-attribution labels are above the max cardinality. #12822
* [BUGFIX] Distributor: Report the correct size in the `err-mimir-distributor-max-write-message-size` error. #12799
* [BUGFIX] Query-frontend: Fix issue where expressions containing unary negation could be sharded incorrectly in some cases. #12911
* [BUGFIX] Query-frontend: Fix issue where shardable expressions containing aggregations with a shardable parameter (eg. `sum(foo)` in `topk(scalar(sum(foo)), sum by (pod) (bar))`) would not have the parameter sharded. #12958
* [BUGFIX] Ingester: Fix `max_inflight_push_requests` metric and internal counter not decremented under pressure, possibly causing the rejection of all push requests. #12975
* [BUGFIX] Store-gateway: Fix not being able to scale down via the `POST /prepare-shutdown` endpoint unless there are some active tenants with sharded blocks to the store-gateway replica. #12972
* [BUGFIX] MQE: Fix invalid source label name in `label_join` error message, so it refers to the source label rather than the destination label. #12185
* [BUGFIX] Continuous test: Fix false positive in metadata assertion when duplicate metadata is present in ingest-storage record correctness test. #12891
* [BUGFIX] Query-frontend: Fix issue where the query-frontend could behave unpredictably if a response was received from queriers multiple times for the same query. #12639
* [BUGFIX] Memcached: Ignore invalid responses when discovering cache servers using `dnssrv+` or `dnssrvnoa+` service discovery prefixes. #13203

### Mixin

* [CHANGE] Enable ingest storage panels by default in all compiled mixins. #13023
* [CHANGE] Alerts: Removed `MimirFrontendQueriesStuck` alert given this is not relevant when the query-scheduler is running and the query-scheduler is now a required component. #12810
* [CHANGE] Alerts: Make `MimirIngesterHasNotShippedBlocksSinceStart` weaker to account for block-builder restarts. The change only affects the block-builder version of the alert. #12319
* [ENHANCEMENT] Rollout progress dashboard: make panels higher to fit more components. #12429
* [ENHANCEMENT] Add `max_series` limit to Writes Resources > Ingester > In-memory series panel. #12476
* [ENHANCEMENT] Alerts: Add `MimirHighGRPCConcurrentStreamsPerConnection` alert. #11947
* [ENHANCEMENT] Alerts: Add `rollout_stuck_alert_ignore_deployments` and `rollout_stuck_alert_ignore_statefulsets` configuration options to exclude particular Deployments or StatefulSets from the `MimirRolloutStuck` alert. #12951
* [ENHANCEMENT] Alerts: Replace experimental `BlockBuilderLagging` alert with `BlockBuilderSchedulerPendingJobs` alert. The new alert triggers when the block-builder scheduler has pending jobs, indicating that block-builders are unable to keep up with the workload. #12593
* [ENHANCEMENT] Rollout-operator: Vendor rollout-operator monitoring dashboard from rollout-operator repository. #12688
* [BUGFIX] Block-builder dashboard: fix reference to detected gaps metric in errors panel. #12401

### Jsonnet

* [CHANGE] Removed etcd-operator from the Jsonnet configuration. Users can still use etcd as a KV store for rings, but need to deploy and manage etcd themselves rather than via the operator. #13049
* [CHANGE] Distributor: Reduce calculated `GOMAXPROCS` to be closer to the requested number of CPUs. #12150
* [CHANGE] Query-scheduler: The query-scheduler is now a required component that is always used by queriers and query-frontends. #12187
* [CHANGE] Rollout-operator: Add `watch` permission to the rollout-operators's cluster role. #12360. See [rollout-operator#262](https://github.com/grafana/rollout-operator/pull/262)
* [CHANGE] Updates to CPU and memory scaling metric. Use `irate()` when calculating the CPU metric and remove `or vector(0)` from a leg of the memory query. These changes prevent downscaling deployments when scraping fails. #12406
* [CHANGE] Memcached: Remove configuration for enabling mTLS connections to Memcached servers. #12434
* [CHANGE] Ingester: Disable shipping of blocks on the third zone (zone-c) when using `ingest_storage_ingester_zones: 3` on ingest storage #12743 #12744
* [CHANGE] Distributor: Increase `server.grpc-max-concurrent-streams` from 100 to 1000. #12742
* [CHANGE] Ruler Query Frontend: Increase `server.grpc-max-concurrent-streams` from 100 to 300. #12742
* [CHANGE] Rollout-operator: Vendor jsonnet from rollout-operator repository. #12688 #12962 #12996
* [CHANGE] Mimir-continuous-test: Use `mimir -target=continuous-test` instead of standalone binary/image. #13097
* [CHANGE] Removed per-component configuration options to set the pods toleration when multi-zone is enabled. Tolerations can still be configured globally using `_config.multi_zone_schedule_toleration`. The following configuration options have been removed: #13043
  * `_config.multi_zone_distributor_schedule_toleration`
  * `_config.multi_zone_etcd_schedule_toleration`
* [FEATURE] Memcached: Allow `minReadySeconds` to be set via `_config.cache_frontend_min_ready_seconds` (etc.) to slow down Memcached rollouts. #12938
* [FEATURE] Distributor: Allow setting GOMEMLIMIT equal to memory request, via `_config.distributor_gomemlimit_enabled`. If enabled, distributor horizontal auto-scaling memory trigger is also removed, since it doesn't make sense in combination with GOMEMLIMIT. #12963
* [ENHANCEMENT] Add timeout validation for querier and query-frontend. Enhanced `parseDuration` to support milliseconds and combined formats (e.g., "4m30s"). #12766
* [ENHANCEMENT] Allow the max number of OTEL events in a span to be configure via `_config.otel_span_event_count_limit`. #12865
* [ENHANCEMENT] Memcached: added the following fields to customise the memcached's node affinity matchers: #12987
  * `$.memcached_frontend_node_affinity_matchers`
  * `$.memcached_index_queries_node_affinity_matchers`
  * `$.memcached_chunks_node_affinity_matchers`
  * `$.memcached_metadata_node_affinity_matchers`
* [ENHANCEMENT] Rollout-operator: expose `rollout_operator_enabled` in `$._config`. #12419

### Documentation

* [CHANGE] Remove references to queriers having a Prometheus HTTP API. Instead, the query-frontend is now required for a Prometheus HTTP API. #12949
* [CHANGE] Helm: Remove GEM (Grafana Enterprise Metrics) references from Helm chart documentation. #13019 #13020 #13021
* [CHANGE] Update HA tracker documentation to use memberlist as the default KV store instead of consul/etcd. Consul and etcd are now marked as deprecated for the HA tracker as of Mimir 3.0. #13002
* [ENHANCEMENT] Add migration guide for HA tracker from Consul or etcd to memberlist. #13011
* [ENHANCEMENT] Improve the MimirIngesterReachingSeriesLimit runbook. #12356
* [ENHANCEMENT] Improve the description of how to limit the number of buckets in native histograms. #12797
* [ENHANCEMENT] Document native histograms with custom buckets. #12823
* [BUGFIX] Add a missing attribute to the list of default promoted OTel resource attributes in the docs: deployment.environment. #12181

### Tools

* [CHANGE] Mimir-continuous-test: Remove standalone binary and image. #13097
* [ENHANCEMENT] Base `mimirtool`, `metaconvert`, `copyblocks`, and `query-tee` images on `distroless/static-debian12`. #13014
* [ENHANCEMENT] kafkatool: add `format=json` to `kafkatool dump print`. #12737

### Query-tee

* [CHANGE] If you configure multiple secondary backends and enable comparisons, query-tee reports comparison results of the preferred backend against each of the secondaries. #13022


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-2.17.2...mimir-3.0.0


================================================================================

# 3.0.1

Tag: mimir-3.0.1
URL: https://github.com/grafana/mimir/releases/tag/mimir-3.0.1

# Changelog

## 3.0.1

### Grafana Mimir

* [CHANGE] Build: Upgrade Go to 1.25.4. #13692 #13695


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-3.0.0...mimir-3.0.1


================================================================================

# 3.0.2

Tag: mimir-3.0.2
URL: https://github.com/grafana/mimir/releases/tag/mimir-3.0.2

This release contains 2 PRs from 1 authors. Thank you!

# Changelog

## 3.0.2

### Grafana Mimir

* [BUGFIX] Update to Go v1.25.5 to address [CVE-2025-61729](https://pkg.go.dev/vuln/GO-2025-4155). #13909


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-3.0.1...mimir-3.0.2


================================================================================

# 3.0.3

Tag: mimir-3.0.3
URL: https://github.com/grafana/mimir/releases/tag/mimir-3.0.3

This release contains 9 PRs from 3 authors. Thank you!

# Changelog

## 3.0.3

### Grafana Mimir

* [BUGFIX] Update to Go v1.25.7 to address [CVE-2025-61726](https://pkg.go.dev/vuln/GO-2026-4341). #14242 #14254
* [BUGFIX] Ruler: Add path traversal checks when parsing namespaces and groups, which prevents namespace and group name from containing non-local paths. #14245


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-3.0.2...mimir-3.0.3


================================================================================

# 3.0.4

Tag: mimir-3.0.4
URL: https://github.com/grafana/mimir/releases/tag/mimir-3.0.4

This release contains 4 contributions from 2 authors. Thank you!

# Changelog

## 3.0.4

### Grafana Mimir

* [BUGFIX] Update module go.opentelemetry.io/otel/sdk to v1.40.0 to address [CVE-2026-24051](https://www.cve.org/CVERecord?id=CVE-2026-24051). #14431
* [BUGFIX] Update to Go v1.25.8 to address [CVE-2026-27142](https://pkg.go.dev/vuln/GO-2026-4603), [CVE-2026-27139](https://pkg.go.dev/vuln/GO-2026-4602), [CVE-2026-25679](https://pkg.go.dev/vuln/GO-2026-4601), [CVE-2026-27138](https://pkg.go.dev/vuln/GO-2026-4600), [CVE-2026-27137](https://pkg.go.dev/vuln/GO-2026-4599). #14623

**All changes in this release**:  https://github.com/grafana/mimir/compare/mimir-3.0.3...mimir-3.0.4


================================================================================

# 3.0.5

Tag: mimir-3.0.5
URL: https://github.com/grafana/mimir/releases/tag/mimir-3.0.5

This release contains 3 PRs from 3 authors. Thank you!

# Changelog

## 3.0.5

### Grafana Mimir

* [BUGFIX] Update to google.golang.org/grpc to address [CVE-2026-33186](https://nvd.nist.gov/vuln/detail/CVE-2026-33186). #14761


**All changes in this release**: https://github.com/grafana/mimir/compare/mimir-3.0.4...mimir-3.0.5

