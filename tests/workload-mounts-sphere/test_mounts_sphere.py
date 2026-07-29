#!/usr/bin/env python3
"""Tests for mount and consumer-side Sphere credential gating (ADR-0003 / issue #5).

Seam: helm-rendered PVs/PVCs, consumer ExternalSecrets, and Sphere-owned
material — Workload companions gate on the registry; Sphere roles/Databases/
password generate+push do not.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def render(*extra_args: str) -> list[dict]:
    cmd = ["helm", "template", "test", str(ROOT), *extra_args]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return [d for d in yaml.safe_load_all(proc.stdout) if d]


def applications(docs: list[dict]) -> dict[str, dict]:
    return {
        d["metadata"]["name"]: d
        for d in docs
        if d.get("kind") == "Application" and d.get("metadata", {}).get("namespace") == "argocd"
    }


def external_secrets(docs: list[dict]) -> dict[str, dict]:
    return {
        d["metadata"]["name"]: d
        for d in docs
        if d.get("kind") == "ExternalSecret"
    }


def persistent_volumes(docs: list[dict]) -> dict[str, dict]:
    return {
        d["metadata"]["name"]: d
        for d in docs
        if d.get("kind") == "PersistentVolume"
    }


def persistent_volume_claims(docs: list[dict]) -> dict[str, dict]:
    return {
        d["metadata"]["name"]: d
        for d in docs
        if d.get("kind") == "PersistentVolumeClaim"
    }


def databases(docs: list[dict]) -> dict[str, dict]:
    return {
        d["metadata"]["name"]: d
        for d in docs
        if d.get("kind") == "Database"
    }


def clusters(docs: list[dict]) -> dict[str, dict]:
    return {
        d["metadata"]["name"]: d
        for d in docs
        if d.get("kind") == "Cluster"
    }


def push_secrets(docs: list[dict]) -> dict[str, dict]:
    return {
        d["metadata"]["name"]: d
        for d in docs
        if d.get("kind") == "PushSecret"
    }


def test_disabled_workload_omits_mounts() -> None:
    """Disabled Workloads omit Workload-scoped mounts (PV + PVC) via explicit name."""
    docs = render()
    pvs = persistent_volumes(docs)
    pvcs = persistent_volume_claims(docs)
    apps = applications(docs)

    assert "zurg" not in apps
    assert "zurg" not in pvs
    assert "zurg" not in pvcs


def test_disable_enabled_workload_drops_mounts() -> None:
    """Flipping an enabled Workload off drops its mounts with the Application."""
    docs = render("--set", "workloads.storyteller.enabled=false")
    apps = applications(docs)
    pvs = persistent_volumes(docs)
    pvcs = persistent_volume_claims(docs)

    assert "storyteller" not in apps
    assert "pv-storyteller" not in pvs
    assert "pvc-storyteller" not in pvcs


def test_reenable_restores_mounts() -> None:
    """Re-enabling a Workload restores its mounts."""
    docs = render("--set", "workloads.zurg.enabled=true")
    pvs = persistent_volumes(docs)
    pvcs = persistent_volume_claims(docs)
    assert "zurg" in pvs
    assert "zurg" in pvcs

    enabled = render()
    assert "pv-storyteller" in persistent_volumes(enabled)
    assert "pvc-storyteller" in persistent_volume_claims(enabled)


def test_disabled_workload_omits_consumer_sphere_credentials() -> None:
    """Consumer-side Sphere credential projections gate with the Workload."""
    docs = render()
    secrets = external_secrets(docs)
    apps = applications(docs)

    assert "streaming" not in apps
    assert "riven-db-credentials" not in secrets
    assert "zilean-db-credentials" not in secrets

    disabled = render("--set", "workloads.keycloak.enabled=false")
    assert "keycloak" not in applications(disabled)
    assert "sphere-keycloak" not in external_secrets(disabled)


def test_reenable_restores_consumer_sphere_credentials() -> None:
    """Re-enabling restores consumer-side Sphere credential projections."""
    docs = render("--set", "workloads.streaming.enabled=true")
    secrets = external_secrets(docs)
    assert "riven-db-credentials" in secrets
    assert "zilean-db-credentials" in secrets

    assert "sphere-keycloak" in external_secrets(render())


def test_sphere_owned_material_survives_workload_disablement() -> None:
    """Sphere roles, Databases, and password generate/push stay when Workloads are off."""
    docs = render(
        "--set",
        "workloads.streaming.enabled=false",
        "--set",
        "workloads.keycloak.enabled=false",
        "--set",
        "workloads.botato.enabled=false",
    )
    secrets = external_secrets(docs)
    pushes = push_secrets(docs)
    dbs = databases(docs)
    sphere_clusters = clusters(docs)

    # Sphere password ExternalSecrets + push stay
    assert "riven-user" in secrets
    assert "zilean-user" in secrets
    assert "keycloak-user" in secrets
    assert "botato-user" in secrets
    assert "riven-user-pushsecret" in pushes
    assert "zilean-user-pushsecret" in pushes
    assert "keycloak-user-pushsecret" in pushes
    assert "botato-user-pushsecret" in pushes

    # Sphere Cluster + Databases stay
    assert "sphere" in sphere_clusters
    assert "riven-db" in dbs
    assert "zilean-db" in dbs
    assert "keycloak-db" in dbs
    assert "botato-db" in dbs

    # Consumer projections still omitted
    assert "riven-db-credentials" not in secrets
    assert "zilean-db-credentials" not in secrets
    assert "sphere-keycloak" not in secrets
    assert "botato-env" not in secrets


def test_sphere_password_generators_create_missing_secrets() -> None:
    """Managed-role passwordSecrets must Own the target so new Sphere roles bootstrap.

    creationPolicy=Merge refuses to create a missing secret and leaves CNPG roles /
    Databases / PushSecrets / consumer Vault pulls permanently broken.

    ExternalSecrets that are not referenced as a managed-role passwordSecret (e.g.
    sphere-app) may keep Merge when the Secret pre-exists outside ESO ownership.
    """
    docs = render()
    sphere = next(c for c in docs if c.get("kind") == "Cluster" and c["metadata"]["name"] == "sphere")
    password_secrets = {
        role["passwordSecret"]["name"]
        for role in sphere.get("spec", {}).get("managed", {}).get("roles", [])
        if role.get("passwordSecret", {}).get("name")
    }
    secrets_by_target = {
        es.get("spec", {}).get("target", {}).get("name"): (name, es)
        for name, es in external_secrets(docs).items()
    }
    offenders: list[str] = []
    for secret_name in sorted(password_secrets):
        entry = secrets_by_target.get(secret_name)
        assert entry is not None, f"no ExternalSecret targets password secret {secret_name}"
        name, es = entry
        # ESO default is Owner when omitted.
        policy = es.get("spec", {}).get("target", {}).get("creationPolicy", "Owner")
        if policy != "Owner":
            offenders.append(f"{name} target={secret_name} policy={policy}")
    assert not offenders, (
        "Sphere managed-role password ExternalSecrets must use creationPolicy Owner "
        f"(or omit it); Merge cannot bootstrap new roles: {offenders}"
    )


def test_sphere_password_secrets_include_cnpg_username() -> None:
    """Managed-role password secrets must include username — CNPG refuses to reconcile without it."""
    docs = render()
    sphere = next(c for c in docs if c.get("kind") == "Cluster" and c["metadata"]["name"] == "sphere")
    password_secrets = {
        role["passwordSecret"]["name"]
        for role in sphere.get("spec", {}).get("managed", {}).get("roles", [])
        if role.get("passwordSecret", {}).get("name")
    }
    secrets_by_target = {
        es.get("spec", {}).get("target", {}).get("name"): es
        for es in external_secrets(docs).values()
    }
    missing: list[str] = []
    for secret_name in sorted(password_secrets):
        es = secrets_by_target.get(secret_name)
        assert es is not None, f"no ExternalSecret targets password secret {secret_name}"
        keys = set((es.get("spec", {}).get("target", {}).get("template", {}) or {}).get("data", {}) or {})
        if "password" not in keys or "username" not in keys:
            missing.append(f"{secret_name} keys={sorted(keys)}")
    assert not missing, (
        "Sphere passwordSecret templates must include password and username: " + "; ".join(missing)
    )


def test_sphere_password_uri_fields_use_urlquery() -> None:
    """URI-shaped Sphere password fields must urlquery-encode the password (pack invariant).

    ADO.NET fqdn-uri is not URI-shaped — password stays raw there.
    """
    docs = render()
    uri_keys = ("uri", "jdbc-uri", "fqdn-jdbc-uri")
    offenders: list[str] = []
    for name, es in external_secrets(docs).items():
        if not name.endswith("-user") or es.get("metadata", {}).get("namespace") != "storage":
            continue
        data = (es.get("spec", {}).get("target", {}).get("template", {}) or {}).get("data", {}) or {}
        for key in uri_keys:
            value = data.get(key, "")
            if "urlquery" not in value:
                offenders.append(f"{name}.{key}")
        fqdn = data.get("fqdn-uri", "")
        if fqdn.startswith("Host="):
            if "urlquery" in fqdn:
                offenders.append(f"{name}.fqdn-uri (ado.net must not urlquery)")
        elif fqdn and "urlquery" not in fqdn:
            offenders.append(f"{name}.fqdn-uri")
    assert not offenders, "Sphere URI password templates missing urlquery: " + ", ".join(offenders)


def test_sphere_password_pack_preserves_role_dialects() -> None:
    """Pack keeps per-role fqdn-uri dialects and zilean shortHost."""
    docs = render()
    secrets = external_secrets(docs)

    riven = secrets["riven-user"]["spec"]["target"]["template"]["data"]["fqdn-uri"]
    assert riven.startswith("postgresql+psycopg2://"), riven

    zilean = secrets["zilean-user"]["spec"]["target"]["template"]["data"]
    assert zilean["fqdn-uri"].startswith("Host="), zilean["fqdn-uri"]
    assert "sphere-rw.default" in zilean["uri"], zilean["uri"]

    app = secrets["app-user"]["spec"]["target"]
    assert app.get("creationPolicy") == "Merge"
    assert "username" not in (app.get("template", {}) or {}).get("data", {})


def main() -> int:
    tests = [
        test_disabled_workload_omits_mounts,
        test_disable_enabled_workload_drops_mounts,
        test_reenable_restores_mounts,
        test_disabled_workload_omits_consumer_sphere_credentials,
        test_reenable_restores_consumer_sphere_credentials,
        test_sphere_owned_material_survives_workload_disablement,
        test_sphere_password_generators_create_missing_secrets,
        test_sphere_password_secrets_include_cnpg_username,
        test_sphere_password_uri_fields_use_urlquery,
        test_sphere_password_pack_preserves_role_dialects,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except Exception as exc:  # noqa: BLE001 — report and continue
            failed += 1
            print(f"FAIL  {test.__name__}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
