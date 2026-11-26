#!/bin/bash
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# Entrypoint for openvino/model_server: serves the model in configs/model-config.yaml (text-generation)
# on :8004 with the OpenAI-compatible API (/v3/chat/completions), from the snapshot `make download-models`
# put in /models/huggingface (the host's models/text-generation); without one OVMS pulls it on first start.
set -euo pipefail

CONFIG="${MODEL_CONFIG:-/configs/model-config.yaml}"

# The OVMS image has no Python: read the section's top-level keys with awk.
setting() {
    awk -v key="$1" '
        /^[^[:space:]#][^:]*:/ { in_section = ($0 ~ /^text-generation:/); next }
        in_section && $0 ~ "^  " key ":" {
            sub("^  " key ":[[:space:]]*", ""); sub(/[[:space:]]+#.*$/, ""); gsub(/^"|"$/, ""); print; exit
        }' "$CONFIG"
}

[ -r "$CONFIG" ] || { echo "model config: cannot read $CONFIG" >&2; exit 1; }
MODEL="$(setting model)"
DEVICE="$(setting device)"
CACHE_SIZE="$(setting cache_size)"
for required in MODEL DEVICE; do
    [ -n "${!required}" ] || { echo "model config: 'text-generation.${required,,}' is empty in $CONFIG" >&2; exit 1; }
done
echo "text-generation: model=$MODEL device=$DEVICE cache_size=${CACHE_SIZE:-0}"

snapshot="/models/huggingface/${MODEL//\//_}"
if [ -f "$snapshot/openvino_model.xml" ]; then
    source_args=(--model_path "$snapshot")
else
    source_args=(--source_model "$MODEL" --model_repository_path /models)
fi

exec /ovms/bin/ovms \
    "${source_args[@]}" \
    --model_name "$MODEL" \
    --task text_generation \
    --target_device "$DEVICE" \
    --cache_size "${CACHE_SIZE:-0}" \
    --enable_prefix_caching true \
    --rest_port 8004 \
    --rest_bind_address 0.0.0.0 \
    --log_level INFO
