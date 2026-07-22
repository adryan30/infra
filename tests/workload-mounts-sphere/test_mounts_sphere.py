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
    )
    secrets = external_secrets(docs)
    pushes = push_secrets(docs)
    dbs = databases(docs)
    sphere_clusters = clusters(docs)

    # Sphere password ExternalSecrets + push stay
    assert "riven-user" in secrets
    assert "zilean-user" in secrets
    assert "keycloak-user" in secrets
    assert "riven-user-pushsecret" in pushes
    assert "zilean-user-pushsecret" in pushes
    assert "keycloak-user-pushsecret" in pushes

    # Sphere Cluster + Databases stay
    assert "sphere" in sphere_clusters
    assert "riven-db" in dbs
    assert "zilean-db" in dbs
    assert "keycloak-db" in dbs

    # Consumer projections still omitted
    assert "riven-db-credentials" not in secrets
    assert "zilean-db-credentials" not in secrets
    assert "sphere-keycloak" not in secrets


def main() -> int:
    tests = [
        test_disabled_workload_omits_mounts,
        test_disable_enabled_workload_drops_mounts,
        test_reenable_restores_mounts,
        test_disabled_workload_omits_consumer_sphere_credentials,
        test_reenable_restores_consumer_sphere_credentials,
        test_sphere_owned_material_survives_workload_disablement,
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
