# Vault (agent access)

HashiCorp Vault runs in-cluster and is exposed on the public mesh as **`https://vault.adryan.me`**. ESO’s `ClusterSecretStore` `vault` talks to `http://vault.vault.svc.cluster.local:8200` inside the cluster; agents on a laptop should use the public URL.

## Do this

```bash
export VAULT_ADDR=https://vault.adryan.me
export VAULT_TOKEN=$(kubectl get secret vault-policy-token -n vault -o jsonpath='{.data.token}' | base64 -d)

vault status
vault kv get kv/<path>
vault kv put kv/<path> KEY=value
vault kv patch kv/<path> KEY=value
```

KV is mount `kv` (v2). Paths in ExternalSecrets omit the `data/` segment (e.g. ESO `key: inbox-zero/app` ↔ `vault kv get kv/inbox-zero/app`).

## Do not

- **Do not** `kubectl port-forward` to Vault for routine reads/writes. It races (connection refused before the forward is ready), breaks under interrupted sessions, and is unnecessary while `vault.adryan.me` is healthy.
- **Do not** invent a second Vault address. UI/`VAULT_ADDR` for operators and agents is `https://vault.adryan.me`.
