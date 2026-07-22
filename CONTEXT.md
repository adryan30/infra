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
A deployable application plus the companions it needs to be reachable and configured (Application, VirtualService, secrets, and optional DB user wiring).
_Avoid_: app (too vague), service, helm release alone

**Sphere**:
The shared CloudNativePG Postgres cluster used by database-backed Workloads.
_Avoid_: the database, postgres, CNPG cluster (when you mean this specific one)
