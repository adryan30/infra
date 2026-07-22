#!/usr/bin/env python3
"""Tests for Workload Application shell helpers (ADR-0002) and enablement registry (ADR-0003).

Seam: helm-rendered Application CRs under templates/apps/ —
registry enablement gate, syncPolicy profiles, destination server.
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
    docs = [d for d in yaml.safe_load_all(proc.stdout) if d]
    return docs


def applications(docs: list[dict]) -> dict[str, dict]:
    return {
        d["metadata"]["name"]: d
        for d in docs
        if d.get("kind") == "Application" and d.get("metadata", {}).get("namespace") == "argocd"
    }


def sync_options(app: dict) -> list[str]:
    return app["spec"]["syncPolicy"].get("syncOptions") or []


def test_workload_profile_storyteller() -> None:
    apps = applications(render())
    assert "storyteller" in apps, "storyteller Application missing from render"
    app = apps["storyteller"]
    sp = app["spec"]["syncPolicy"]
    assert sp["managedNamespaceMetadata"]["labels"]["istio-injection"] == "enabled"
    assert sp["automated"] == {"enabled": True, "prune": True, "selfHeal": True}
    assert sync_options(app) == [
        "CreateNamespace=true",
        "ServerSideApply=true",
        "RespectIgnoreDifferences=true",
    ]
    assert sp["retry"]["limit"] == 5
    assert app["spec"]["destination"]["server"] == "https://kubernetes.default.svc"
    assert app["spec"]["revisionHistoryLimit"] == 3
    assert app["metadata"]["finalizers"] == ["resources-finalizer.argocd.argoproj.io"]


def test_platform_profile_keycloak() -> None:
    apps = applications(render())
    assert "keycloak" in apps, "keycloak Application missing — migrate to helpers"
    app = apps["keycloak"]
    sp = app["spec"]["syncPolicy"]
    assert "managedNamespaceMetadata" not in sp
    assert sync_options(app) == ["CreateNamespace=true"]


def test_workload_istio_disabled_tailscale() -> None:
    apps = applications(render())
    assert "tailscale" in apps, "tailscale Application missing — migrate to helpers"
    app = apps["tailscale"]
    sp = app["spec"]["syncPolicy"]
    assert sp["managedNamespaceMetadata"]["labels"]["istio-injection"] == "disabled"
    assert "ServerSideApply=true" in sync_options(app)


def test_platform_with_ssa_reloader() -> None:
    apps = applications(render())
    assert "reloader" in apps, "reloader Application missing — migrate to helpers"
    app = apps["reloader"]
    sp = app["spec"]["syncPolicy"]
    assert "managedNamespaceMetadata" not in sp
    assert sync_options(app) == [
        "CreateNamespace=true",
        "ServerSideApply=true",
        "RespectIgnoreDifferences=true",
    ]


def test_enabled_false_omits_application() -> None:
    """Disabled Workloads (enabled: false) must not appear as Applications."""
    apps = applications(render())
    for name in (
        "streaming",
        "jellyfin",
        "plex",
        "zurg",
        "suwayomi",
        "discord-music",
    ):
        assert name not in apps, f"{name} should be omitted when enabled is false"


def test_missing_registry_key_fails_render() -> None:
    """A Workload Application whose name is absent from the registry must fail helm template."""
    proc = subprocess.run(
        [
            "helm",
            "template",
            "test",
            str(ROOT),
            "--set",
            "workloads.storyteller=null",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0, "render must fail when a Workload key is missing from the registry"
    assert "not in the enablement registry" in proc.stderr


def test_registry_override_controls_application_presence() -> None:
    """Applications gate on the values registry, not inline enablement literals."""
    disabled = applications(render("--set", "workloads.storyteller.enabled=false"))
    assert "storyteller" not in disabled, "registry enabled=false must omit the Application"

    enabled = applications(render("--set", "workloads.streaming.enabled=true"))
    assert "streaming" in enabled, "registry enabled=true must render the Application"


def main() -> int:
    tests = [
        test_workload_profile_storyteller,
        test_platform_profile_keycloak,
        test_workload_istio_disabled_tailscale,
        test_platform_with_ssa_reloader,
        test_enabled_false_omits_application,
        test_missing_registry_key_fails_render,
        test_registry_override_controls_application_presence,
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
