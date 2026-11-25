#!/bin/sh
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# Serves LLM_MODEL (a Hugging Face OpenVINO repository) on :8004 with the OpenAI-compatible API
# (/v3/chat/completions). On first start OVMS pulls it into /opt/medical-scribe/models/text-generation.
set -eu

: "${LLM_MODEL:=OpenVINO/Qwen3.5-4B-int4-ov}"
: "${LLM_DEVICE:=GPU}"
# 0, as in the graph multiserve wrote for this model (validated on Arrow Lake).
: "${LLM_CACHE_SIZE:=0}"

exec ovms \
    --source_model "$LLM_MODEL" \
    --model_repository_path /opt/medical-scribe/models/text-generation \
    --model_name "$LLM_MODEL" \
    --task text_generation \
    --target_device "$LLM_DEVICE" \
    --cache_size "$LLM_CACHE_SIZE" \
    --enable_prefix_caching true \
    --rest_port 8004 \
    --rest_bind_address 0.0.0.0 \
    --log_level INFO
