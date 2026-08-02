# Shardblade

Personal Kubernetes cluster configuration for Shardblade: GitOps chart, ingress, secrets wiring, and rare bootstrap.

## Language

**Bootstrap**:
The Terraform path that installs Argo CD and the root Application that points at this repository. Rarely touched after the cluster exists.
_Avoid_: k8s repo, terraform root, provisioner

**App-of-apps**:
The Helm chart at the repository root whose templates declare Argo Applications and cluster-wide resources Argo syncs continuously.
_Avoid_: infra chart (ambiguous with the repo name), manifests root

**Workload**:
A deployable application plus the companions it needs to be reachable and configured (Application, VirtualService, secrets, oauth host membership when required, mounts, and optional consumer-side DB credential projection). Enablement is a property of the whole Workload — companions are not independently “on” while the Application is omitted. Chart-local scale-to-zero is not disablement. Sphere roles, Databases, and password generation are not Workload companions; they belong to Sphere and outlive Workload disablement.
_Avoid_: app (too vague), service, helm release alone, disabling via comment-out or replicaCount alone

**Workload pack**:
Application-owned extras for one Workload, living under `workloads/<name>/` and synced as a multi-source directory on that Workload’s Application (so they appear under that app in Argo). Holds upstream workarounds and app-local resources (CronJobs, EnvoyFilters, and similar) — not platform companions (VirtualService, ExternalSecrets, Sphere, mounts), which stay in App-of-apps domain trees per the enablement registry.
_Avoid_: companions (those are the platform/enablement set), overlays (ambiguous with Kustomize), extras dump

**Sphere**:
The shared CloudNativePG Postgres cluster used by database-backed Workloads. Owns roles, Databases, and password material for those roles; Workloads only consume projected credentials.
_Avoid_: the database, postgres, CNPG cluster (when you mean this specific one)

**Pin**:
An explicit image tag, chart `targetRevision`, or other version string recorded in the App-of-apps as desired state. Changing a Pin is a git change; Argo Sync applies it.
_Avoid_: version (ambiguous), release (ambiguous with upstream projects), auto release

**Float**:
A mutable image reference (for example `latest` or `preview`) that is not a Pin. Newest content can change without a git commit.
_Avoid_: unpinned, floating tag (as the concept name)

**Sync**:
Argo applying the App-of-apps desired state from git onto the cluster. Already automated here; it is not version discovery.
_Avoid_: deploy, release, auto update (when you mean Sync alone)
