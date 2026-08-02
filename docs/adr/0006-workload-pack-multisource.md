# Workload pack: Application-owned extras via multi-source

ADR-0003 keeps platform companions (VirtualService, ExternalSecrets, mounts, oauth ingress membership) in App-of-apps domain trees with one enablement registry. That still leaves app-specific extras — upstream chart workarounds, CronJobs, EnvoyFilters — showing under **infra** in Argo if rendered by the App-of-apps. We put those in `workloads/<name>/` and attach the directory as a second Application source (`git@github.com:adryan30/infra.git`, `targetRevision: HEAD`) so they Sync and appear under the Workload Application. Platform companions stay where ADR-0003 put them; a Workload pack is not a dump of every companion into the app UI.

## Considered Options

- Co-locate all companions under each Application (reopen ADR-0003) — rejected; scatters Istio/ESO/Sphere browse and enablement
- Keep every extra on the App-of-apps — rejected; Argo UI ownership stays on infra and mixes platform with app patches
- Separate Argo Application per extras folder — rejected; doubles Application count without clearer Sync boundaries
