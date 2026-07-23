# bjw-s `app-template` for Shardblade GitOps

Research notes on whether Helm chart `app-template` from **bjw-s-labs** remains a good fit for generic container Workloads in this repo, and how credible alternatives compare. Repo facts treated as given: personal k3s GitOps (Argo CD app-of-apps), Workloads = Argo Applications + companions (`CONTEXT.md`), nine Applications pin `chart: app-template` / `repoURL: https://bjw-s-labs.github.io/helm-charts` under `templates/apps/` (streaming, plex, storyteller, breezewiki, jellyfin, suwayomi, calibre, botato, zurg). At research time the pin was `4.4.0`; the follow-up bump lands on latest 4.x (`4.6.2`). Istio VirtualServices, oauth membership, and secrets stay outside chart values. Upstream charts remain the default when a first-party chart exists (Vault, Longhorn, etc.).

Sources are bjw-s-labs docs/releases/GitHub, Helm and Kubernetes docs, Argo CD docs, and first-party status pages for named alternatives unless noted.

## Project status today

### Org, repos, docs

| Item | Current | Evidence |
|------|---------|----------|
| Org | **bjw-s-labs** (“BJW-S Labs”) | [GitHub org](https://github.com/bjw-s-labs) |
| Chart repo | [bjw-s-labs/helm-charts](https://github.com/bjw-s-labs/helm-charts) — not archived; Apache-2.0 | Repo metadata / [LICENSE](https://github.com/bjw-s-labs/helm-charts/blob/main/LICENSE) |
| Rename | `github.com/bjw-s/helm-charts` **301 →** `bjw-s-labs/helm-charts` | HTTP redirect from old URL |
| Helm repo URL | `https://bjw-s-labs.github.io/helm-charts` (add as `bjw-s`) | [Getting started](https://bjw-s-labs.github.io/helm-charts/docs/app-template/getting-started/); this repo already uses that URL |
| Docs | [bjw-s-labs.github.io/helm-charts/docs/](https://bjw-s-labs.github.io/helm-charts/docs/) | Chart README + site index |
| OCI | `oci://ghcr.io/bjw-s-labs/helm/app-template` | [app-template README](https://github.com/bjw-s-labs/helm-charts/blob/main/charts/other/app-template/README.md) |
| Author’s GitOps | [bjw-s-labs/home-ops](https://github.com/bjw-s-labs/home-ops) still active | Repo `pushed_at` recent; README points charts at this home cluster |

The maintainer’s README states the repo is **not** meant to replace large public chart collections; it is charts developed to run apps in their home cluster ([helm-charts README](https://github.com/bjw-s-labs/helm-charts/blob/main/README.md)). That matches how Shardblade already uses it: generic Workloads only.

**Artifact Hub:** As of this research, Artifact Hub search did not return a first-party `bjw-s-labs` / `bjw-s` `app-template` package (API search for `bjw-s` / `app-template` returned unrelated third-party charts). Treat the GitHub Pages Helm index and GHCR OCI as the authoritative distribution channels, not Artifact Hub.

### `common` vs `app-template`

Official model ([App Template docs](https://bjw-s-labs.github.io/helm-charts/docs/app-template/)):

- **`common`** — Helm **library** chart (`type: library`). Provides rendering for controllers, services, persistence, etc. Library charts are **not installable** on their own ([Helm library charts](https://helm.sh/docs/topics/library_charts/)).
- **`app-template`** — thin **application** chart that depends on `common` and exposes values for deploying arbitrary apps. Chart description: “A common powered chart template. This can be useful for small projects that don't have their own chart.” ([Chart.yaml](https://github.com/bjw-s-labs/helm-charts/blob/main/charts/other/app-template/Chart.yaml))

Values are effectively the common library’s schema (controllers, service, persistence, ingress/routes, probes, …). IDE validation is documented via `$schema` pointing at `charts/library/common/values.schema.json` ([Getting started](https://bjw-s-labs.github.io/helm-charts/docs/app-template/getting-started/)).

### Versions vs this repo’s pin

| Line | Version | Published (GitHub release) |
|------|---------|----------------------------|
| This repo (at research) | **4.4.0** | 2025-10-15 ([app-template-4.4.0](https://github.com/bjw-s-labs/helm-charts/releases/tag/app-template-4.4.0)) |
| This repo (post-bump) | **4.6.2** | 2026-01-16 ([app-template-4.6.2](https://github.com/bjw-s-labs/helm-charts/releases/tag/app-template-4.6.2)) |
| Latest **4.x** | **4.6.2** | 2026-01-16 ([app-template-4.6.2](https://github.com/bjw-s-labs/helm-charts/releases/tag/app-template-4.6.2)) |
| Latest stable | **5.0.1** | 2026-05-14 ([app-template-5.0.1](https://github.com/bjw-s-labs/helm-charts/releases/tag/app-template-5.0.1)) |

`common` 5.0.1 declares `kubeVersion: ">=1.31.0-0"` while `app-template` 5.0.1 still lists `>=1.28.0-0` in Chart.yaml — verify cluster version before a 5.x bump ([common Chart.yaml](https://github.com/bjw-s-labs/helm-charts/blob/main/charts/library/common/Chart.yaml), [app-template Chart.yaml](https://github.com/bjw-s-labs/helm-charts/blob/main/charts/other/app-template/Chart.yaml)). common 5.0.0 also raised minimum Helm to 3.18 ([common-5.0.0 release](https://github.com/bjw-s-labs/helm-charts/releases/tag/common-5.0.0)).

### Cadence and health (not EOL)

- **Majors with written upgrade guides:** 1→2, 2→3, 3→4, 4→5 under [docs/app-template/upgrades/](https://bjw-s-labs.github.io/helm-charts/docs/app-template/upgrades/4-to-5/).
- **4.4 → 4.6:** Additive / fixes in common (PDB, route extras, jobLabel, supplementalGroupsPolicy, HTTPRoute port fixes) — no “breaking” callouts in [common-4.5.0](https://github.com/bjw-s-labs/helm-charts/releases/tag/common-4.5.0) / [4.6.x](https://github.com/bjw-s-labs/helm-charts/releases/tag/common-4.6.2) notes.
- **Activity:** Repo not archived; ~10 open issues; open PRs include feature work (e.g. [feat(common): Release v5.1.0](https://github.com/bjw-s-labs/helm-charts/pull/684)); releases through May 2026. No project deprecation or successor chart announced in README or upgrade docs.

### Major migration notes (official)

**3.x → 4.x** ([3-to-4](https://bjw-s-labs.github.io/helm-charts/docs/app-template/upgrades/3-to-4/)): consistent resource naming (may rename/replace objects); ServiceAccount API reshape; `app.kubernetes.io/component` → `app.kubernetes.io/controller` (immutable labels → controller recreate); kube ≥ 1.28.

**4.x → 5.x** ([4-to-5](https://bjw-s-labs.github.io/helm-charts/docs/app-template/upgrades/4-to-5/)): `rawResources` → `manifest` wrapper; default dedicated ServiceAccount; `automountServiceAccountToken` default **false**; ServiceMonitor/PodMonitor `jobLabel` default change; NetworkPolicy controller/`podSelector` mutual exclusivity. This repo’s sampled `valuesObject`s do **not** use `rawResources`, chart ingress, or ServiceMonitors — so 5.x impact is mostly SA defaults / token mount behavior, not a values rewrite.

No EOL of 4.x is stated; 5.x is the current major.

## What `app-template` is good at (this use case)

Documented capabilities used or available here ([App Template](https://bjw-s-labs.github.io/helm-charts/docs/app-template/), getting-started example):

| Need in Shardblade | Chart support |
|--------------------|---------------|
| Multi-controller Workloads (e.g. `streaming.yaml`) | Named `controllers:` map |
| Multi-container / sidecars (e.g. calibre main + downloader) | Nested `containers:` under a controller |
| PVC / existingClaim / secret mounts (`zurg`, jellyfin library) | `persistence:` with types and `globalMounts` / `advancedMounts` |
| Services + ports | `service:` tied to `controller` |
| Probes, strategies, env, securityContext | Under controller/container values |
| Ingress / Gateway API | Supported in chart — **unused here**; Istio companions own HTTP routing |

**Argo CD fit:** Applications already use `helm.valuesObject` with a remote Helm repo — first-class in Argo ([Helm guide](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/); precedence documents `valuesObject`). Pinning `targetRevision` matches current practice.

**Maintenance vs raw YAML for ~9–10 similar apps:** One shared values vocabulary for Deployment/Service/PVC patterns; Workload files stay compact (ADR [0002](../adr/0002-workload-application-shell.md) keeps large `valuesObject`s local per Application). Companions stay outside the chart, so the chart does not fight Istio/oauth design.

## Sharp edges / reasons people leave

| Edge | Detail | Source |
|------|--------|--------|
| Major schema churn | 2→3 removed default `main` objects + JSON schema; 3→4 naming/labels; 4→5 SA/`rawResources` | [Upgrade guides](https://bjw-s-labs.github.io/helm-charts/docs/app-template/upgrades/4-to-5/) |
| Large / opaque schema | Full power lives in common’s values + schema; rendered objects are indirect | Docs + `values.schema.json` |
| Reviewability | Diffs are values → Helm inflate, not Deployment YAML; harder for agents/humans who prefer raw manifests | Inherent to Helm ([Argo: Helm templates, CD owns lifecycle](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/)) |
| Single-maintainer / home-lab scope | Explicitly not a “Bitnami-scale” catalog | [README](https://github.com/bjw-s-labs/helm-charts/blob/main/README.md) |
| Supply chain | Apache-2.0; Helm index + OCI on GHCR; no first-party SECURITY.md found in repo root; no project-stated CVE process beyond normal GitHub issues | Repo tree / README |
| Chart ingress unused | If someone enables chart Ingress alongside Istio VirtualServices, duplicate routing risk — process issue, not a chart defect | This repo’s companion pattern |

Nothing in official materials frames the project as abandoned or superseded.

---

## Alternatives vs `app-template` (comparison)

Flux `HelmRelease` is **not** evaluated as a migrate target: this cluster is Argo CD. Packaging differences (HelmRelease CR vs Application) do not change the underlying chart/manifest choice.

### 1. Plain Kubernetes manifests (Argo directory)

**What it optimizes for:** Exact API objects; maximum reviewability; no third-party chart schema ([Kubernetes objects](https://kubernetes.io/docs/concepts/overview/working-with-objects/kubernetes-objects/)).

**Maintenance for ~10 Workloads:** Each app needs Deployment + Service + PVC (+ probes, volumes, multi-container) duplicated or copy-pasted. Patterns drift unless you invent your own conventions. `streaming`-class multi-controller apps become large directories of YAML.

**Argo CD fit:** Native [directory applications](https://argo-cd.readthedocs.io/en/stable/user-guide/directory/) (`recurse` / `include` / `exclude`). Application shell helpers in this repo would point `path:` at manifest dirs instead of a Helm chart.

**Migrate cost from current values:** High — every `controllers`/`service`/`persistence` tree must be expanded to full objects (or `helm template` once then freeze). PVC names / labels may change → careful cutover.

**When it beats bjw-s:** You want zero Helm dependency for generic apps; agents/reviewers must edit Deployments directly; chart majors become unacceptable.

### 2. Kustomize (bases + overlays / components)

**What it optimizes for:** Compose and patch plain manifests without a values DSL; reusable [components](https://kubectl.docs.kubernetes.io/references/kustomize/kustomization/components/); image/name/label overrides.

**Maintenance for ~10 Workloads:** One base (or component) for “Deployment+Service+PVC” plus per-app overlays. Still more YAML surface than app-template values; multi-controller apps need multiple resources per overlay. You own the base’s quality forever.

**Argo CD fit:** First-class ([Kustomize guide](https://argo-cd.readthedocs.io/en/stable/user-guide/kustomize/)), including Application-level `components`, `patches`, `images`.

**Migrate cost:** High — same expansion as plain manifests, then factor into bases/components. No automated values→kustomize path from bjw-s.

**When it beats bjw-s:** Homogeneous apps that share a thin base; preference for patch-based GitOps; desire to drop Helm inflate for generic Workloads only (upstream Helm charts can remain).

### 3. In-repo (or private OCI) local Helm chart replacing `app-template`

**What it optimizes for:** Same Argo `helm.valuesObject` UX, but **you** own the schema and release cadence. Options: thin wrappers around vendored `common`, or a small custom chart with only the knobs this cluster needs. Helm documents library charts as non-installable helpers for application charts ([library charts](https://helm.sh/docs/topics/library_charts/)) — same split bjw-s already uses.

**Maintenance for ~10 Workloads:** Values files stay similar **only if** you keep bjw-s schema (vendoring `common` / wrapping `app-template`). A simplified custom chart reduces schema size but requires implementing multi-controller, PVC, probes, etc. You become the chart maintainer (CI, schema, upgrade notes).

**Argo CD fit:** Excellent — `path:` to chart in this git repo, or OCI chart URL ([Argo Helm](https://argo-cd.readthedocs.io/en/stable/user-guide/helm/)). Aligns with ADR 0002 (values stay in Application YAML).

**Migrate cost:** Low–medium if wrapping/vendoring current schema and only changing `repoURL`/`path`/`targetRevision`; **high** if inventing a new values shape (rewrite all nine files).

**When it beats bjw-s:** Upstream majors repeatedly break you; you need features they reject; supply-chain policy requires charts in-repo; or you want a **smaller** schema than common and will invest in maintaining it.

### 4. TrueCharts (and similar “catalog + common” projects)

**Status (first-party):** Alive under TrueForge. Site: [truecharts.org](https://truecharts.org/) — “Community Helm Charts for Kubernetes”. Charts repo [trueforge-org/truecharts](https://github.com/trueforge-org/truecharts) actively pushed; library chart path includes `charts/library/common`. Jan 2026 update describes ongoing chart releases and tooling ([January 2026 update](https://truecharts.org/news/truecharts/january-2026-update/)). 2025 goals describe archiving some mirrored upstream charts and keeping standardized charts where their common layer adds value ([2025 project goals](https://truecharts.org/news/2025-start/)).

**What it optimizes for:** Large catalog of **opinionated per-app** charts on a shared common library, plus TrueForge cluster tooling/images — not a drop-in generic `app-template` for arbitrary images.

**Maintenance / migrate cost for this repo:** Wrong shape. You would either (a) switch each Workload to a TrueCharts app chart (different images, values, assumptions, often Traefik/addon opinions) or (b) try to drive their `common` like bjw-s — different schema, no benefit over staying. High cost, little gain for “generic container + Istio companions.”

**When it beats bjw-s:** Almost never for Shardblade’s generic-app pattern. Consider only if adopting TrueForge’s full stack (not this cluster’s direction).

### 5. Bitnami `common` / Bitnami app charts

**Status:** [bitnami/charts](https://github.com/bitnami/charts) still published; install path is OCI `oci://registry-1.docker.io/bitnamicharts/<chart>` ([README](https://github.com/bitnami/charts/blob/main/README.md)). `common` on Artifact Hub is a **library** chart for grouping logic between Bitnami charts — “not deployable by itself” ([Artifact Hub bitnami/common](https://artifacthub.io/packages/helm/bitnami/common)). Images emphasize Bitnami Secure Images / commercial options; legacy Debian images pointed at `bitnamilegacy` ([README](https://github.com/bitnami/charts/blob/main/README.md)).

**Fit:** Bitnami ships **specific applications**, not a generic “any image” template. Library `common` cannot replace `app-template` as an installable chart ([Helm library charts](https://helm.sh/docs/topics/library_charts/)).

**When it beats bjw-s:** When there is a first-party Bitnami chart for that app **and** you accept their image/values model — same rule you already use for Vault/etc. **Not** a migrate target for jellyfin/plex/zurg-style generic Workloads.

### 6. Geek’s Cookbook / other homelab “app chart” collections

[geek-cookbook/geek-cookbook](https://github.com/geek-cookbook/geek-cookbook) is a **guides** collection for self-hosted stacks, not an actively competing generic Helm app-template (last push mid-2025 at research time). No first-party successor chart to bjw-s was found in project docs. Other Artifact Hub packages named `app-template` (third-party) are not established replacements.

### 7. Operators for “generic apps”

Operators fit CRD-defined domains (databases, certs, etc.). There is no credible operator that replaces Deployment+Service+PVC for arbitrary container images. **Not recommended** as a migrate path for these Workloads.

### Comparison table

| Option | Maturity / maintenance | Schema / boilerplate | Multi-container / PVC / probes | Breaking-change risk | Migrate cost from current | Fit for Shardblade |
|--------|------------------------|----------------------|--------------------------------|----------------------|---------------------------|--------------------|
| **bjw-s `app-template` (stay)** | Healthy single-maintainer; docs + majors through 5.x | Compact values; large upstream schema | Excellent (already used) | Upstream majors (documented) | None | **Best current fit** |
| **Stay + bump 4.4→4.6.x** | Same | Same | Same | Low (additive 4.x notes) | Trivial pin bump | **Recommended near-term** |
| **Stay + upgrade 5.x** | Same; kube/Helm floors | Same + SA defaults | Same; watch SA/token defaults | Medium (documented 4→5) | Low–medium verify | Good when ready |
| Plain manifests | You maintain all YAML | Verbose; max clarity | Manual | Your mistakes only | High | OK if rejecting Helm |
| Kustomize + components | You maintain bases | Medium; patches | Manual / patterned | Your base churn | High | OK if standardizing on Kustomize |
| In-repo/OCI local chart | You own chart CI | Tunable | Only if you build it | Your release process | Low if wrap common; high if new schema | Good **later** if upstream pain |
| TrueCharts | Active catalog | Different opinions | Per-app charts, not generic template | Their common majors | Very high | **Poor** migrate target |
| Bitnami common/apps | Active; app-specific | N/A as generic template | Per Bitnami app | Bitnami / image policy | N/A for generics | Use **per-app** only |
| Operators | N/A for generic apps | CRDs | Wrong tool | — | — | **Not recommended** |

---

## Migration cost for this repo (quantified)

| Scope | Count / note |
|-------|----------------|
| Applications on `app-template` @ `4.4.0` | **9** files under `templates/apps/` |
| Values patterns | Controllers (incl. multi), services, persistence (PVC, existingClaim, secret mounts); Reloader annotations; no chart `ingress` / `rawResources` found |
| Companions | Istio / oauth / secrets unchanged by chart choice |
| Lowest-risk change | `targetRevision: 4.4.0` → `4.6.2` (same major; applied in this follow-up) |
| Next major | `5.0.1` after reading [4-to-5](https://bjw-s-labs.github.io/helm-charts/docs/app-template/upgrades/4-to-5/); confirm k3s ≥ 1.31 for common’s kubeVersion; smoke SA token behavior for any app that talks to the API |
| Full migrate away | Rewrite 9 Workloads + prove PVC/name stability; highest effort, no health-driven urgency |

**Staying and upgrading within 4.x (or carefully to 5.x) is lower risk than migrating away.**

---

## Verdict

### Recommended

1. **Stay on bjw-s-labs `app-template`.** It is actively maintained, documented, and already matched to how this repo deploys generic Workloads (values-driven controllers/persistence, companions outside the chart). Alternatives do not win on maintenance or migrate cost for ~9 similar apps.
2. **Prefer `targetRevision` bump 4.4.0 → latest 4.x (4.6.2)** when convenient — release notes for 4.5/4.6 are additive/fixes, not a schema rewrite.
3. **Plan 5.x as a deliberate PR**, not an emergency: follow official 4→5 notes; verify Kubernetes/Helm floors and default ServiceAccount / `automountServiceAccountToken` behavior.

### Not recommended (now)

- **Migrating to TrueCharts / Bitnami / random Artifact Hub `app-template` clones** for these generic Workloads — wrong abstraction or unproven replacements.
- **Rewriting to plain manifests or Kustomize** solely because Helm indirection exists — cost is high; reviewability gains do not justify churn while the chart is healthy.
- **Inventing urgency** — no deprecation/EOL; project still releasing and documenting majors.

### When migration *would* make sense later

| Trigger | Sensible move |
|---------|----------------|
| Sustained upstream breakage or unfixed bugs blocking you | In-repo chart wrapping/vendoring `common`, or slim custom chart |
| Policy requires all templates in-git / no third-party Helm repos | Path-based or OCI chart you publish |
| Team/agents consistently fail at values→object mental model | Kustomize components or plain manifests for **new** apps first |
| A Workload gains a quality first-party chart | Use that chart (existing pattern for Vault, etc.) — not a wholesale app-template exit |

**Bottom line:** Keep `app-template`; upgrade pins on your schedule. Alternatives are real tools, but none beat bjw-s for Shardblade’s current generic-Workload pattern without a large rewrite or a change in GitOps philosophy.
