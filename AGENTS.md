## Agent skills

### Issue tracker

Issues live in GitHub Issues for `adryan30/infra` (via `gh`). See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Workload packs

App-owned extras (chart workarounds, CronJobs, EnvoyFilters) live in `workloads/<name>/` and sync as a second Application source. Platform companions (VS, ESO, Sphere, mounts) stay in App-of-apps domain trees. See `docs/adr/0006-workload-pack-multisource.md`.

### Git workflow

`main` is live (Argo CD auto-syncs). Never commit or push to `main` — branch + PR only. Use Conventional Commits. See `docs/agents/git-workflow.md`.

### Vault

Operator/agent CLI access is `https://vault.adryan.me` plus the `vault-policy-token` Secret — not port-forward. See `docs/agents/vault.md`.
