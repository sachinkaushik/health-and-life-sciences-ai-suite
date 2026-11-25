#!/bin/sh
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# Serves the model in configs/model-config.yaml (text-generation) on :8004 with the OpenAI-compatible
# API (/v3/chat/completions). On first start OVMS pulls it into /opt/medical-scribe/models/text-generation.
set -eu

config="$(PYTHONPATH=/opt/model-config python3 /opt/model-config/model_config.py text-generation)"
eval "$config"
echo "text-generation: model=$MODEL device=$DEVICE cache_size=${CACHE_SIZE:-0}"

exec ovms \
    --source_model "$MODEL" \
    --model_repository_path /opt/medical-scribe/models/text-generation \
    --model_name "$MODEL" \
    --task text_generation \
    --target_device "$DEVICE" \
    --cache_size "${CACHE_SIZE:-0}" \
    --enable_prefix_caching true \
    --rest_port 8004 \
    --rest_bind_address 0.0.0.0 \
    --log_level INFO
