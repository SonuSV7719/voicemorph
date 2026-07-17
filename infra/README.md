# infra

Enterprise scale-out and operations (fills in alongside M3+):

- **k8s/helm** — API deployment + horizontally scaled GPU worker pool, HPA on
  queue depth, node selectors/taints for GPU nodes.
- **observability** — Prometheus metrics (latency, real-time factor, GPU util,
  queue depth), Grafana dashboards, structured logging, tracing.
- **CI/CD** — build/test/lint, container publishing, signed release artifacts for
  `.exe` and `.apk`.
