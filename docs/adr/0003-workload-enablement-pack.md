# Workload enablement registry and companion gating

ADR-0002 deepened the Application shell and deferred companions until a Workload pack existed; enablement still only omitted the Application while VirtualServices, ExternalSecrets, oauth hosts, and mounts stayed live. We deepen Workload enablement into a chart-values registry (`workloads.<name>.enabled` plus an ingress list of host/oauth/backend entries): Application and all Workload companions share one gate; companions stay in their domain trees and name their Workload explicitly; missing registry keys fail the Helm render; oauth Workload hosts are derived from enabled ingress entries with oauth opted in; VirtualServices for chart Workloads render from that ingress list. Application `valuesObject`s stay in hybrid Application files (ADR-0002 unchanged). Sphere roles, Databases, and password generation stay with Sphere. A small platform ingress set (Bootstrap Argo, oauth callback) stays outside the registry. Disable and remove are both first-class; chart-local scale-to-zero is not disablement. Roll out expand–contract.

## Considered Options

- Co-locate companions next to each Application file — rejected; hurts Istio/ESO browse and blame locality; deepen is one enablement seam, not one directory
- Repeat `enabled` on every companion file — rejected; booleans drift; no single source of truth
- Separate `oauthHosts` list beside VirtualService hosts — rejected; duplicates hostname; oauth is a flag on the same ingress entry
- VirtualService file as sole host source with values only holding `enabled`/`oauth` — rejected; Helm cannot read other templates as data without convention hacks
- Phased companion kinds (VS/ESO first, mounts later) — rejected; no urgency; design the full Workload companion set once
- Silent default when a Workload key is missing — rejected; fail-closed keeps the registry a complete index
- Fake Workloads for Bootstrap-owned ingress (Argo) — rejected; small platform ingress set outside the registry
- Big-bang cutover — rejected; expand–contract keeps each step verifiable
