# Vault auto-unseal for this homelab

Research notes for enabling auto-unseal on the HashiCorp Vault deployment in this repo (`templates/apps/vault.yaml`, Helm chart `0.31.0`). Cluster facts treated as given: single replica `vault-0`, `storage=file` on Longhorn PVC, Seal Type=Shamir (1 share / threshold 1), HA disabled, TLS disabled on listener, k3s on Oracle Cloud compute (`shardblade-001/002`), ESO `ClusterSecretStore` backed by a static `vault-policy-token`.

Sources are HashiCorp Vault docs, vault-helm, and OCI Key Management docs unless noted.

## What auto-unseal is (and why Shamir reseals on restart)

When Vault starts it is **sealed**: it can reach storage but cannot decrypt data. Unsealing reconstructs the plaintext **root key** so Vault can decrypt the encryption keyring. With the default **Shamir** seal, that root key is protected by an unseal key split into shares; operators must present a threshold of shares after every process start.

A node stays unsealed until it is sealed via API, **the server restarts**, or storage hits an unrecoverable error. That restart behavior is why a CrashLoop (or any pod restart) left this cluster sealed and, with a strict liveness probe, kept resealing.

**Auto-unseal** delegates decrypting the root key to a trusted device or service (cloud KMS, another Vault’s Transit engine, or an HSM). At startup Vault asks that backend to decrypt the stored root key—no manual `vault operator unseal` for normal restarts.

With auto-unseal, operations that still need human quorum (e.g. generate-root) use **recovery keys**, not unseal keys. Recovery keys **cannot** decrypt the root key if the KMS/HSM is gone: losing the seal mechanism (or permanently deleting its key) means the cluster is unrecoverable even from backups.

## Supported seal backends (official)

Configured via a `seal` stanza. If omitted, Vault uses Shamir.

| Type | Doc | OSS auto-unseal | Notes for this lab |
|------|-----|-----------------|--------------------|
| `awskms` | [AWS KMS seal](https://developer.hashicorp.com/vault/docs/configuration/seal/awskms) | Yes (all Vault versions) | Needs AWS account + IAM `kms:Encrypt/Decrypt/DescribeKey`. Seal wrap = Enterprise only. |
| `azurekeyvault` | [Azure Key Vault seal](https://developer.hashicorp.com/vault/docs/configuration/seal/azurekeyvault) | Yes | Needs Azure tenant/credentials or MSI on Azure VMs. |
| `gcpckms` | [GCP CKMS seal](https://developer.hashicorp.com/vault/docs/configuration/seal/gcpckms) | Yes | Chart `values.yaml` ships a commented example; matches the live ConfigMap comment. |
| `ocikms` | [OCI KMS seal](https://developer.hashicorp.com/vault/docs/configuration/seal/ocikms) | Yes | Official; fits OCI compute. Instance principal or API key. |
| `transit` | [Transit seal](https://developer.hashicorp.com/vault/docs/configuration/seal/transit) | Yes | Needs a **second** Vault (already unsealed) with Transit encrypt/decrypt. |
| `pkcs11` | [PKCS#11 seal](https://developer.hashicorp.com/vault/docs/configuration/seal/pkcs11) | **Enterprise only** | Not usable with OSS Vault from this Helm chart’s default image. |

Seal wrapping (extra wrap of storage entries) is an Enterprise feature for these backends; Community Edition still gets auto-unseal.

## Fit for this setup (single file-storage Vault on OCI k3s)

### Recommendation 1 (preferred): `ocikms`

**Why:** Nodes already run on Oracle Cloud; HashiCorp documents `seal "ocikms"` as a first-class backend for all Vault versions. You create an OCI Vault + master encryption key, point Vault at the crypto/management endpoints and `key_id`, and grant decrypt/encrypt via IAM.

**Auth options** ([OCI KMS seal auth](https://developer.hashicorp.com/vault/docs/configuration/seal/ocikms#authentication)):

1. **Instance principal** (`auth_type_api_key` unset/false) — Dynamic Group of compute instances + policy to `use keys`. On k3s this only works if the Vault pod can reach IMDS and OCI treats the host instance as the principal (usually true for hostNetwork or default routing to `169.254.169.254`; verify before relying on it).
2. **API key** (`auth_type_api_key = true`) — User principal with OCI SDK config / env; easier to inject as a Kubernetes Secret via `extraSecretEnvironmentVars` / mounted config. Better default for k3s if IMDS or dynamic-group matching is awkward.

**Tradeoffs:** Couples unseal to OCI tenancy/region availability and IAM. OCI KMS vault type and key protection mode affect cost (virtual private vault vs shared; HSM vs software keys)—see [OCI Vaults and Key Management overview](https://docs.oracle.com/en-us/iaas/Content/KeyManagement/Concepts/keyoverview.htm). Deleting the KMS key permanently loses the Vault barrier. Adds tenancy policy surface (dynamic group or API-key user).

### Recommendation 2 (runner-up): `gcpckms` (or `awskms`)

**Why:** vault-helm 0.31.0 already documents a standalone `gcpckms` example in `server.standalone.config`; your live ConfigMap comment matches that pattern. Useful if you want the seal **outside** the same OCI failure domain as the VMs, or you already operate GCP/AWS.

**Tradeoffs:** Another cloud account, SA/IAM keys in-cluster, egress to that KMS, and monthly KMS cost. Same permanent-key-loss risk. Cross-cloud dependency for a homelab that is otherwise OCI-only.

### Not recommended here

- **`transit`:** Classic chicken-egg—needs another always-unsealed Vault (or manual unseal on the “parent”). Wrong for a single Vault that ESO already depends on.
- **`pkcs11`:** Auto-unseal requires Vault Enterprise.
- **Staying on Shamir + probe `sealedcode=204`:** Valid mitigation (avoids CrashLoop reseal loops) but does not restore secrets after restart until someone unseals; ESO’s static token cannot help while sealed.

**HA / Raft:** Not required for auto-unseal. File storage + standalone remains fine; do not flip `server.ha` only for seal migration.

## Migration path: Shamir → auto-unseal

Official rules ([Seal migration](https://developer.hashicorp.com/vault/docs/concepts/seal#seal-migration)):

- Migration **requires downtime**; the whole cluster must briefly be down.
- **Backup first.**
- Old and new seal mechanisms must both be available during migration.
- Shamir → auto-unseal: add the new `seal` block; on bring-up, run unseal with **`-migrate`**; Shamir shares become **recovery keys**.

This cluster is **one node, file storage, Vault ≫ 1.5.1**, so use the simplified single-node flow derived from “Migration post Vault 1.5.1” / Shamir→auto pre-1.5.1 notes:

1. **Backup** the Longhorn PVC / Vault data path and securely record the current Shamir unseal key (you have 1 share / threshold 1). Confirm `vault status` while healthy.
2. **Provision the KMS key** (OCI Vault key, or GCP/AWS equivalent) and IAM so Vault can encrypt/decrypt **before** cutting over.
3. **Schedule downtime.** ESO and anything using `vault-policy-token` will fail while sealed/down.
4. **Update Helm values** so `server.standalone.config` includes the new `seal "..."` block (see sketch below). Sync Argo / restart so the ConfigMap updates. For a single replica, scale down / delete pod after config is ready so the new config mounts cleanly.
5. Bring **`vault-0` up**. It should report sealed but with the new seal type pending migration.
6. From a client with the old Shamir key:

   ```bash
   vault operator unseal -migrate
   ```

   Enter the single share (threshold 1). Vault migrates; that share becomes a **recovery key**. Monitor logs for migration / re-wrap completion messages as documented for post-1.5.1 migrations.
7. **Verify:** `vault status` shows unsealed and Seal Type = the auto seal (e.g. `ocikms`). Restart the pod once and confirm it comes up **unsealed without** manual unseal.
8. **Store recovery keys** offline (same care as old unseal keys). Optionally rekey recovery shares later (`vault operator rekey -target=recovery`).
9. Keep probe `sealedcode=204` until auto-unseal is proven across several restarts; then you may tighten probes if desired.

Enterprise **Seal HA** online migration does **not** apply to Shamir sources and is Enterprise-oriented; ignore for OSS Shamir → KMS.

## Helm values sketch (`templates/apps/vault.yaml`)

Chart default standalone config (file storage, TLS disabled, commented `gcpckms`) lives in [vault-helm `v0.31.0` `values.yaml`](https://raw.githubusercontent.com/hashicorp/vault-helm/v0.31.0/values.yaml). Sensitive material should use `extraSecretEnvironmentVars` / Secrets, not ConfigMap plaintext ([Protecting sensitive Vault configurations](https://developer.hashicorp.com/vault/docs/platform/k8s/helm/run#protecting-sensitive-vault-configurations)).

### Option A — OCI KMS (preferred sketch)

```yaml
# Under Application.spec.source.helm.valuesObject:
server:
  readinessProbe:
    enabled: true
    path: "/v1/sys/health?standbyok=true&sealedcode=204&uninitcode=204"
  livenessProbe:
    enabled: true
    path: "/v1/sys/health?standbyok=true&sealedcode=204&uninitcode=204"
    initialDelaySeconds: 60
  # Prefer secret-mounted OCI config / env over putting keys in ConfigMap.
  # Example shape only — wire real Secret names after creating OCI API key material
  # (or rely on instance principal and omit API-key secrets).
  extraSecretEnvironmentVars:
    - envName: OCI_CONFIG_FILE
      secretName: vault-oci-kms
      secretKey: config
    # Plus any OCI SDK vars your auth method needs; or use instance principal and skip.
  standalone:
    enabled: true
    config: |
      ui = true

      listener "tcp" {
        tls_disable = 1
        address = "[::]:8200"
        cluster_address = "[::]:8201"
      }

      storage "file" {
        path = "/vault/data"
      }

      seal "ocikms" {
        key_id               = "ocid1.key.oc1...<REPLACE>"
        crypto_endpoint      = "https://<vault>-crypto.kms.<region>.oraclecloud.com"
        management_endpoint  = "https://<vault>-management.kms.<region>.oraclecloud.com"
        # auth_type_api_key  = "true"   # set if not using instance principal
      }
ui:
  enabled: true
```

Equivalent env-driven activation is also documented: `VAULT_SEAL_TYPE=ocikms` plus `VAULT_OCIKMS_SEAL_KEY_ID`, `VAULT_OCIKMS_CRYPTO_ENDPOINT`, `VAULT_OCIKMS_MANAGEMENT_ENDPOINT`.

### Option B — GCP CKMS (chart’s own example, adapted)

```yaml
server:
  extraSecretEnvironmentVars:
    - envName: GOOGLE_APPLICATION_CREDENTIALS
      secretName: gcp-kms-creds
      secretKey: credentials.json
  # Mount path depends on chart extraVolumes convention; see vault-helm GCP example.
  standalone:
    enabled: true
    config: |
      ui = true

      listener "tcp" {
        tls_disable = 1
        address = "[::]:8200"
        cluster_address = "[::]:8201"
      }

      storage "file" {
        path = "/vault/data"
      }

      seal "gcpckms" {
        project     = "<gcp-project>"
        region      = "global"
        key_ring    = "vault-helm-unseal-kr"
        crypto_key  = "vault-helm-unseal-key"
      }
```

Do **not** enable `server.ha` solely for this migration while storage remains `file`.

## Risks and operational notes

| Risk | Detail |
|------|--------|
| **Key loss = data loss** | If the cloud KMS key (or HSM) is permanently deleted/unavailable and you have not migrated off it, Vault cannot be recovered—including from storage backups. Recovery keys do not decrypt the root key. |
| **Chicken-egg (`transit`)** | Transit auto-unseal needs another healthy Vault; unsuitable as the only Vault feeding ESO. |
| **KMS cost / IAM** | OCI/GCP/AWS charge for vaults/keys and API use; mis-scoped IAM or deleted dynamic groups brick unseal. Prefer least privilege: encrypt/decrypt (and describe) on one key only. |
| **Recovery key backup** | After migration, treat recovery keys like the old Shamir share: offline, encrypted backup. Your threshold-1 setup is convenient but fragile—consider rekeying to multi-share recovery later. |
| **Downtime / ESO** | Migration downtime seals or stops Vault; static `vault-policy-token` clients fail until unsealed again. |
| **Probe mitigation vs fix** | `sealedcode=204` stops CrashLoop; it does not auto-unseal. Keep it during and after cutover until auto-unseal is proven. |
| **ConfigMap secrets** | Do not put OCI API keys or cloud credentials in `standalone.config` HCL; use Secrets + env as the chart recommends. |
| **TLS still disabled** | Orthogonal to seal; auto-unseal does not require enabling listener TLS, but production hardening would. |

## Recommended next step for this repo

1. Create a **software-protected** (or HSM if preferred) master key in **OCI Key Management** in the same region as `shardblade-*`, with a Dynamic Group / policy (or API-key user) ready for encrypt/decrypt.
2. Add a draft `server.standalone.config` + `seal "ocikms"` (and Secret wiring) behind a PR on `templates/apps/vault.yaml` **without** syncing until a maintenance window.
3. In that window: backup PVC → apply config → `vault operator unseal -migrate` with the existing single Shamir share → restart pod to prove auto-unseal → store the resulting recovery key offline.

Until that lands, keep the current `sealedcode=204` probe behavior so sealed Vault does not CrashLoop.
