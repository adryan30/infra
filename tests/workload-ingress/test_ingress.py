#!/usr/bin/env python3
"""Tests for Workload ingress and oauth derivation (ADR-0003 / issue #3).

Seam: helm-rendered VirtualServices and AuthorizationPolicy — registry ingress
lists, enablement gating, platform ingress outside the registry.
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


def virtual_services(docs: list[dict]) -> dict[str, dict]:
    return {
        d["metadata"]["name"]: d
        for d in docs
        if d.get("kind") == "VirtualService"
    }


def oauth_hosts(docs: list[dict]) -> set[str]:
    for d in docs:
        if d.get("kind") == "AuthorizationPolicy" and d.get("metadata", {}).get("name") == "oauth2-general":
            hosts = d["spec"]["rules"][0]["to"][0]["operation"]["hosts"]
            return set(hosts)
    raise AssertionError("oauth2-general AuthorizationPolicy missing from render")


def test_multi_host_workload_renders_ingress_virtual_services() -> None:
    """Enabled multi-host Workloads render one VirtualService per registry ingress entry."""
    vss = virtual_services(render())
    assert "calibre" in vss
    assert vss["calibre"]["spec"]["hosts"] == ["calibre.adryan.me"]
    assert vss["calibre"]["spec"]["http"][0]["route"][0]["destination"] == {
        "host": "calibre-main.books.svc.cluster.local",
        "port": {"number": 8083},
    }
    assert "calibre-downloader" in vss
    assert vss["calibre-downloader"]["spec"]["hosts"] == ["cdownloader.adryan.me"]

    assert "grafana" in vss
    assert vss["grafana"]["spec"]["hosts"] == ["grafana.adryan.me"]
    assert "prometheus" in vss
    assert vss["prometheus"]["spec"]["hosts"] == ["prometheus.adryan.me"]

    disabled = virtual_services(render("--set", "workloads.calibre.enabled=false"))
    assert "calibre" not in disabled
    assert "calibre-downloader" not in disabled


def test_single_host_workload_renders_from_registry() -> None:
    """Single-host Workload VirtualServices take host/backend from the registry."""
    vss = virtual_services(render())
    assert "homepage" in vss
    assert vss["homepage"]["spec"]["hosts"] == ["home.adryan.me"]
    assert vss["homepage"]["spec"]["http"][0]["route"][0]["destination"] == {
        "host": "homepage.homepage.svc.cluster.local",
        "port": {"number": 3000},
    }
    omitted = virtual_services(render("--set", "workloads.homepage.enabled=false"))
    assert "homepage" not in omitted


def test_disabled_workload_omits_ingress_virtual_services() -> None:
    """Disabled Workloads omit their registry-driven VirtualServices."""
    vss = virtual_services(render())
    for name in ("riven", "prowlarr", "seerr", "jellyfin", "plex", "suwayomi"):
        assert name not in vss, f"{name} VirtualService should be omitted when Workload is disabled"


def test_oauth_hosts_track_enablement() -> None:
    """Oauth Workload hosts come from enabled ∧ oauth ingress; platform hosts stay."""
    hosts = oauth_hosts(render())
    assert "kiali.adryan.me" in hosts, "platform oauth host must remain"
    assert "longhorn.adryan.me" in hosts
    assert "grafana.adryan.me" in hosts
    assert "prometheus.adryan.me" in hosts
    assert "cdownloader.adryan.me" in hosts
    # streaming is disabled — its oauth hosts must not appear
    assert "riven.adryan.me" not in hosts
    assert "prowlarr.adryan.me" not in hosts

    flipped = oauth_hosts(render("--set", "workloads.longhorn.enabled=false"))
    assert "longhorn.adryan.me" not in flipped
    assert "kiali.adryan.me" in flipped


def test_platform_ingress_outside_registry_still_renders() -> None:
    """Bootstrap Argo and oauth-callback VirtualServices stay outside the registry."""
    vss = virtual_services(render("--set", "workloads.monitoring.enabled=false"))
    assert "argocd" in vss
    assert vss["argocd"]["spec"]["hosts"] == ["argo.adryan.me"]
    assert "oauth" in vss
    assert vss["oauth"]["spec"]["http"][0]["match"][0]["uri"]["prefix"] == "/oauth2/callback"
    assert "kiali" in vss
    assert "grafana" not in vss
    assert "prometheus" not in vss


def main() -> int:
    tests = [
        test_multi_host_workload_renders_ingress_virtual_services,
        test_single_host_workload_renders_from_registry,
        test_disabled_workload_omits_ingress_virtual_services,
        test_oauth_hosts_track_enablement,
        test_platform_ingress_outside_registry_still_renders,
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
