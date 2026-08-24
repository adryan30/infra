# CPU requests sized from Prometheus p95, not left at chart defaults

Auditing node CPU commitment (#116) found both cluster nodes 92-97% committed on CPU requests while real usage sat at 14-38%. The gap wasn't the app workloads under `templates/apps/*.yaml` — those mostly already follow a `cpu: 1m` convention — it was platform-component Applications (keycloak, longhorn, cert-manager, csi-driver-rclone, vault, kiali, netbird-operator, oauth2-proxy, reloader, tailscale, kube-prometheus-stack) declaring no `cpu:` override at all and inheriting their upstream Helm chart's default request.

We decided to size each component's CPU request from its observed p95 CPU usage over Prometheus's retention window (`kube-prometheus-stack`, ~10 days by default), multiplied by 1.3-1.5x headroom. Auth- and storage-critical components (keycloak, vault, cert-manager, longhorn) get a wider margin (2x or more) instead of the standard multiplier — undersizing those risks an outage, not just latency, and the point of this audit is reclaiming slack from over-provisioned workloads, not squeezing the ones load-bearing for cluster identity and storage.

## Considered Options

- Live `kubectl top` snapshot instead of p95 — rejected; a single point-in-time reading can miss a real recurring peak
- Leave platform components at chart defaults — rejected; that's what caused the over-commitment in the first place
- One uniform multiplier for every component — rejected; conflates the blast radius of throttling a batch job with throttling auth

## Consequences

Future workloads and platform components should size their CPU request the same way rather than guessing a value or leaving it unset; a deviation should be justified in the Application's PR description.
