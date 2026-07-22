# Infra for the Shardblade Cluster

[![App Status](https://argo.adryan.me/api/badge?name=infra&revision=true&showAppName=true)](https://argo.adryan.me/applications/infra)

Public GitOps repository for Shardblade: the **App-of-apps** Helm chart at the repo root (synced by Argo CD) and a small **Bootstrap** Terraform tree under `bootstrap/` (installs Argo and the root Application).

## Layout

| Path | Role |
|------|------|
| `Chart.yaml`, `values.yaml`, `templates/` | App-of-apps chart — Workloads, Istio, ESO, storage, operators |
| `bootstrap/` | Terraform Bootstrap — Argo CD install + root Application (`repoURL` → this repo) |
| `CONTEXT.md`, `docs/adr/` | Domain language and decisions |
| `AGENTS.md`, `docs/agents/` | Agent / issue-tracker conventions |

## Day-to-day

Edit templates under `templates/`, commit, push to `main`. Argo syncs automatically.

```bash
git clone git@github.com:adryan30/infra.git
cd infra
```

## Bootstrap (rare)

```bash
cd bootstrap
cp terraform.tfvars.example terraform.tfvars   # set vault-policy-token locally
terraform init
terraform plan
terraform apply
```

### Vault OCI KMS auto-unseal (`bootstrap/kms`)

Provisions an Always Free software-protected OCI KMS key, a dedicated IAM user/API key, and the `vault/vault-oci-kms` Secret consumed by the Vault Helm chart.

```bash
cd bootstrap/kms
cp terraform.tfvars.example terraform.tfvars   # tenancy + OCI auth
# If using SecurityToken: oci session authenticate --profile DEFAULT
terraform init
terraform apply
```

Then sync Vault (Argo) and migrate once from Shamir:

```bash
kubectl -n vault delete pod vault-0
kubectl -n vault exec -it vault-0 -- vault operator unseal -migrate   # paste current Shamir share
kubectl -n vault delete pod vault-0                                  # prove auto-unseal
kubectl -n vault exec vault-0 -- vault status                        # Seal Type=ocikms, Sealed=false
```

Details: [`docs/research/vault-auto-unseal.md`](./docs/research/vault-auto-unseal.md).

Never commit `*.tfvars` or `*.tfstate*` — they are gitignored. Use a kubeconfig context that can reach the cluster (`shardblade-001` by default in `bootstrap/main.tf`).

## Domain language

See [`CONTEXT.md`](./CONTEXT.md). Architecture decisions: [`docs/adr/`](./docs/adr/).
