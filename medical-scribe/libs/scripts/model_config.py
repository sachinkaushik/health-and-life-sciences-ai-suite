#!/usr/bin/env python3
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Prints one service's section of configs/model-config.yaml as shell assignments, for entrypoints:

    eval "$(python model_config.py speech-to-text)"   # MODEL=... DEVICE=... PRECISION=...

Nested keys are joined with "_" (generation.top_p -> GENERATION_TOP_P). Fails loudly when the file,
the section, or its model / device is missing, so a service never starts on a guessed default."""

from __future__ import annotations

import os
import re
import shlex
import sys

import yaml

CONFIG = os.environ.get("MODEL_CONFIG", "/configs/model-config.yaml")


def flatten(prefix: str, value: object, out: dict[str, str]) -> None:
    if isinstance(value, dict):
        for key, inner in value.items():
            flatten(f"{prefix}_{key}" if prefix else str(key), inner, out)
    else:
        out[re.sub(r"[^A-Za-z0-9]", "_", prefix).upper()] = "" if value is None else str(value)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: model_config.py <service>", file=sys.stderr)
        return 2
    service = sys.argv[1]
    try:
        with open(CONFIG, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except OSError as e:
        print(f"model config: cannot read {CONFIG}: {e}", file=sys.stderr)
        return 1
    section = config.get(service)
    if not isinstance(section, dict):
        print(f"model config: no '{service}' section in {CONFIG}", file=sys.stderr)
        return 1
    for required in ("model", "device"):
        if not str(section.get(required) or "").strip():
            print(f"model config: '{service}.{required}' is empty in {CONFIG}", file=sys.stderr)
            return 1
    values: dict[str, str] = {}
    flatten("", section, values)
    for key, value in values.items():
        print(f"{key}={shlex.quote(value)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
