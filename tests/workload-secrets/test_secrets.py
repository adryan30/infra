#!/usr/bin/env python3
"""Tests for Workload ExternalSecret companion gating (ADR-0003 / issue #4).

Seam: helm-rendered ExternalSecrets (and Applications) — registry enablement
gate with explicit Workload names, including awkward secret metadata names.
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


def test_disabled_workload_omits_application_and_externalsecrets() -> None:
    """Disabled Workloads omit Application and Workload ExternalSecrets together."""
    docs = render()
    apps = applications(docs)
    secrets = external_secrets(docs)

    assert "plex" not in apps
    assert "plex-key" not in secrets

    assert "discord-music" not in apps
    assert "discord-config" not in secrets

    assert "zurg" not in apps
    assert "zurg-config" not in secrets

    assert "streaming" not in apps
    assert "vpn-riven" not in secrets


def test_disable_enabled_workload_drops_application_and_secret() -> None:
    """Flipping an enabled Workload off drops Application and its ExternalSecret together."""
    docs = render("--set", "workloads.storyteller.enabled=false")
    apps = applications(docs)
    secrets = external_secrets(docs)
    assert "storyteller" not in apps
    assert "storyteller-env" not in secrets


def test_reenable_restores_externalsecrets() -> None:
    """Re-enabling a Workload restores its ExternalSecrets (awkward names included)."""
    docs = render(
        "--set",
        "workloads.plex.enabled=true",
        "--set",
        "workloads.discord-music.enabled=true",
        "--set",
        "workloads.zurg.enabled=true",
    )
    secrets = external_secrets(docs)
    assert "plex-key" in secrets
    assert "discord-config" in secrets
    assert "zurg-config" in secrets


def test_awkward_secret_names_gate_on_explicit_workload() -> None:
    """Secret metadata names that differ from the Workload key still gate correctly."""
    # storyteller-env → storyteller (covered by disable above when false)
    enabled = external_secrets(render())
    assert "storyteller-env" in enabled
    assert "rcon" in enabled
    assert "monitoring-grafana-admin" in enabled

    disabled = external_secrets(
        render(
            "--set",
            "workloads.minecraft.enabled=false",
            "--set",
            "workloads.monitoring.enabled=false",
        )
    )
    assert "rcon" not in disabled
    assert "monitoring-grafana-admin" not in disabled
    # Application must drop with the secret
    apps = applications(
        render(
            "--set",
            "workloads.minecraft.enabled=false",
            "--set",
            "workloads.monitoring.enabled=false",
        )
    )
    assert "minecraft" not in apps
    assert "monitoring" not in apps


def test_non_workload_secrets_still_render() -> None:
    """Platform / non-Workload secrets are not gated by the Workload registry."""
    docs = render(
        "--set",
        "workloads.cert-manager.enabled=false",
        "--set",
        "workloads.keycloak.enabled=false",
    )
    secrets = external_secrets(docs)
    # pgadmin is not a registry Workload; its secret must remain
    assert "pgadmin-root-password" in secrets
    # Sphere-owned password material in storage must survive Workload disablement
    assert "riven-user" in secrets
    assert "zilean-user" in secrets
    assert "keycloak-user" in secrets
    kinds = {d["metadata"]["name"]: d["kind"] for d in docs}
    assert kinds.get("wildcard-certificate") == "ClusterExternalSecret"


def main() -> int:
    tests = [
        test_disabled_workload_omits_application_and_externalsecrets,
        test_disable_enabled_workload_drops_application_and_secret,
        test_reenable_restores_externalsecrets,
        test_awkward_secret_names_gate_on_explicit_workload,
        test_non_workload_secrets_still_render,
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
