#!/usr/bin/env python3
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Download the models listed in configs/models.yaml (run with workers/.venv/bin/python)."""

from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def download(name: str, spec: dict) -> None:
    repo, method = spec["repo"], spec["method"]
    print(f"==> {name}: {repo} ({method})", flush=True)

    if method == "ovms-pull":
        cmd = [sys.executable, "-m", "model_downloader", "ovms-pull", repo,
               str(ROOT / spec["dest"]), "--task", spec["task"]]
        if spec.get("target_device"):
            cmd += ["--target-device", spec["target_device"]]
        if spec.get("weight_format"):
            cmd += ["--weight-format", spec["weight_format"]]
        subprocess.run(cmd, check=True)
    elif method == "snapshot":
        cmd = [sys.executable, "-m", "model_downloader", "snapshot", repo, str(ROOT / spec["dest"])]
        subprocess.run(cmd, check=True)
    elif method == "hf-cache":
        from huggingface_hub import snapshot_download
        print(snapshot_download(repo))
    else:
        raise SystemExit(f"{name}: unknown method '{method}'")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(ROOT / "configs" / "models.yaml"))
    parser.add_argument("--only", default="", help="comma-separated model names from the config")
    args = parser.parse_args()

    config = yaml.safe_load(Path(args.config).read_text())
    # Always the app's own cache, even if HF_HOME / HF_HUB_CACHE is set in the shell.
    os.environ["HF_HOME"] = str(ROOT / config.get("huggingface_home", "models/huggingface"))
    os.environ.pop("HF_HUB_CACHE", None)

    only = {n.strip() for n in args.only.split(",") if n.strip()}
    unknown = only - set(config["models"])
    if unknown:
        raise SystemExit(f"Unknown model name(s): {', '.join(sorted(unknown))}")
    selected = {n: s for n, s in config["models"].items()
                if (n in only if only else s.get("enabled", True))}

    if any(s.get("requires_token") for s in selected.values()) and not os.environ.get("HF_TOKEN"):
        if not sys.stdin.isatty():
            raise SystemExit("HF_TOKEN is required for gated models; set it in the environment.")
        os.environ["HF_TOKEN"] = getpass.getpass("Hugging Face token (for gated models): ")

    failed = []
    for name, spec in selected.items():
        try:
            download(name, spec)
        except Exception as exc:  # keep going with the other models
            print(f"!! {name} failed: {exc}", file=sys.stderr)
            failed.append(name)

    if failed:
        raise SystemExit(f"Failed: {', '.join(failed)}")
    print("All models downloaded.")


if __name__ == "__main__":
    main()
