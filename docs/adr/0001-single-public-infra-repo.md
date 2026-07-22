# Single public repository for cluster config and Bootstrap

Shardblade used a private `k8s` repo (Terraform Bootstrap + git submodule) and a public `infra` repo (App-of-apps chart). Day-to-day change locality was in `infra` while issues and agents pointed at `k8s`. We joined into public `adryan30/infra`: chart stays at repo root, Bootstrap lives under `bootstrap/`, agent docs and issues target this repo. Secrets stay local (`*.tfvars` / state gitignored). Private `k8s` is archived as a pointer.

## Considered Options

- Keep two remotes, treat `infra` as primary by habit — rejected; submodule and tracker leak remain
- Join into private `k8s` — rejected; chart should stay public for showcase
- Nest chart under a subdirectory — rejected; would force an Argo `path` change for no gain
