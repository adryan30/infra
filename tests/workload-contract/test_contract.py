#!/usr/bin/env python3
"""Contract: old Workload enablement dialects are retired (ADR-0003 / issue #6).

Seam: helm-rendered App-of-apps chart — registry is the only Workload disable
path; comment-out-as-disable is gone; chart-local scale-to-zero is not disablement.
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


def tor_crs(docs: list[dict]) -> dict[tuple[str, str], dict]:
    return {
        (d["metadata"]["namespace"], d["metadata"]["name"]): d
        for d in docs
        if d.get("kind") == "Tor"
    }


def test_scale_to_zero_is_not_disablement() -> None:
    """Chart-local replicaCount: 0 must not omit the Workload Application."""
    docs = render()
    apps = applications(docs)
    assert "minecraft" in apps, "minecraft stays enabled in the registry while scaled to zero"
    values = apps["minecraft"]["spec"]["source"]["helm"]["valuesObject"]
    assert values["replicaCount"] == 0

    disabled = applications(render("--set", "workloads.minecraft.enabled=false"))
    assert "minecraft" not in disabled, "only registry enabled=false omits the Application"


def test_streaming_tor_gates_on_registry_not_comment_out() -> None:
    """Workload-scoped Tor in streaming gates on the registry, not comment-out."""
    disabled = tor_crs(render("--set", "workloads.streaming.enabled=false"))
    assert ("streaming", "tor") not in disabled, "registry enabled=false must omit streaming Tor"

    enabled = tor_crs(render("--set", "workloads.streaming.enabled=true"))
    assert ("streaming", "tor") in enabled, "registry enabled=true must render streaming Tor"


def main() -> int:
    tests = [
        test_scale_to_zero_is_not_disablement,
        test_streaming_tor_gates_on_registry_not_comment_out,
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
