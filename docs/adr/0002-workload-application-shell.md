# Workload Application shell helpers in App-of-apps

Argo Application CRs under `templates/apps/` duplicated the same shell (finalizers, destination server, automated sync, retry, syncOptions, istio namespace labels, revisionHistoryLimit) while drifting on which pieces each Workload got. We deepen that shell into Helm helpers inside the App-of-apps chart: each Workload file stays (hybrid), keeps its `source` / `valuesObject` as plain YAML, declares an explicit `profile` (`workload` = full mesh defaults, `platform` = minimal), and gates the CR with `enabled` (default true; false omits the Application). Rare outliers may pass explicit syncPolicy overrides (`istioInjection`, `serverSideApply`, `respectIgnoreDifferences`) on top of a profile — overrides are caller intent, not inferred defaults. Scope is Applications in `templates/apps/` only — not `operators/`, `istio/`, or non-Application CRs in `apps/`. Companions (VirtualService, secrets, Sphere) stay out of this module until a Workload pack exists.

## Considered Options

- Values-driven list of all Workloads in `values.yaml` — rejected; fights giant inline `valuesObject`s and hurts per-Workload diff/blame locality
- One helper renders the entire Application including values as a dict — rejected; Helm is a poor editor for large nested values
- Infer `workload` vs `platform` from namespace or allowlist — rejected; recreates syncPolicy drift; profile is caller intent
- Disable via comment-out or chart `replicaCount: 0` only — rejected; enablement belongs on the Application seam; companions may still orphan until a later pack
- Apply the same helpers to `templates/operators/` and `templates/istio/` in v1 — rejected; those aren't the churn hot spot and aren't Workloads in the domain sense
