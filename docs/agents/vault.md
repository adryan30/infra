# Vault (agent access)

HashiCorp Vault runs in-cluster and is exposed on the public mesh as **`https://vault.adryan.me`**. ESO’s `ClusterSecretStore` `vault` talks to `http://vault.vault.svc.cluster.local:8200` inside the cluster; agents on a laptop should use the public URL.

ESO authenticates via Vault's Kubernetes auth method (role `eso`, policy `eso-kv-read` — read-only except `storage/*`, which Sphere's `PushSecret` writes to). There's no standing static token for it to authenticate with your own personal login instead.

## Do this

```bash
export VAULT_ADDR=https://vault.adryan.me
vault login   # SSO/OIDC — grants the `operators` policy, full kv/* CRUD

vault status
vault kv get kv/<path>
vault kv put kv/<path> KEY=value
vault kv patch kv/<path> KEY=value
```

Cache your session with `vault login` once; the CLI persists the token to `~/.vault-token` for subsequent commands.

KV is mount `kv` (v2). Paths in ExternalSecrets omit the `data/` segment (e.g. ESO `key: inbox-zero/app` ↔ `vault kv get kv/inbox-zero/app`).

## Do not

- **Do not** `kubectl port-forward` to Vault for routine reads/writes. It races (connection refused before the forward is ready), breaks under interrupted sessions, and is unnecessary while `vault.adryan.me` is healthy.
- **Do not** invent a second Vault address. UI/`VAULT_ADDR` for operators and agents is `https://vault.adryan.me`.
