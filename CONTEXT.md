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

**Sphere**:
The shared CloudNativePG Postgres cluster used by database-backed Workloads. Owns roles, Databases, and password material for those roles; Workloads only consume projected credentials.
_Avoid_: the database, postgres, CNPG cluster (when you mean this specific one)
