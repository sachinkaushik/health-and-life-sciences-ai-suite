#!/usr/bin/env python3
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
"""Downloads the text-generation model of configs/model-config.yaml through the Model Download service
it runs in (`make download-models`), into <MODELS_DIR>/text-generation/huggingface/<org>_<name>, where
the text-generation service serves it from. Skips a model that is already there."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

import yaml

CONFIG = os.environ.get("MODEL_CONFIG", "/configs/model-config.yaml")
API = "http://127.0.0.1:8000"
REQUIRED = ("openvino_model.xml", "openvino_model.bin", "openvino_tokenizer.xml", "openvino_detokenizer.xml")
FAILED = {"failed", "canceled", "cancelled"}
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    request = urllib.request.Request(API + path, data=data, headers={"Content-Type": "application/json"})
    with _OPENER.open(request, timeout=30) as response:
        return json.load(response)


def missing_files(directory: str) -> list[str]:
    return [name for name in REQUIRED if not os.path.isfile(os.path.join(directory, name))]


def main() -> int:
    with open(CONFIG, encoding="utf-8") as f:
        model = str(((yaml.safe_load(f) or {}).get("text-generation") or {}).get("model") or "").strip()
    if not model:
        print(f"model config: 'text-generation.model' is empty in {CONFIG}", file=sys.stderr)
        return 1
    models_dir = os.environ.get("MODELS_DIR", "/opt/models")
    snapshot = os.path.join(models_dir, "text-generation", "huggingface", model.replace("/", "_"))
    if not missing_files(snapshot):
        print(f"text-generation: {model} is already downloaded")
        return 0

    print(f"text-generation: downloading {model}")
    job_id = call("/models/download?download_path=text-generation", {"models": [{"name": model, "hub": "huggingface"}]})[
        "job_ids"
    ][0]
    while True:
        job = call(f"/jobs/{job_id}")
        status = str(job.get("status", "")).lower()
        if status == "completed":
            break
        if status in FAILED:
            print(f"text-generation: download of {model} {status}: {job.get('error', 'no details')}", file=sys.stderr)
            return 1
        time.sleep(5)

    missing = missing_files(snapshot)
    if missing:
        print(f"text-generation: {model} is not an OpenVINO model (missing {', '.join(missing)})", file=sys.stderr)
        return 1
    print(f"text-generation: {model} downloaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
