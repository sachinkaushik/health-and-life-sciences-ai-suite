#!/bin/sh
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# Starts the intel/audio-analyzer image (mounted read-only, no build) with the speech-to-text and
# diarization sections of configs/model-config.yaml, translated into its AUDIO_ANALYZER__* settings, on :8002.
set -eu

eval "$(python3 /opt/scribe/model_config.py diarization)"
export AUDIO_ANALYZER__MODELS__ASR__DIARIZATION=true
export AUDIO_ANALYZER__MODELS__DIARIZATION__NAME="$MODEL"
export AUDIO_ANALYZER__MODELS__DIARIZATION__DEVICE="$(echo "$DEVICE" | tr '[:lower:]' '[:upper:]')"
echo "diarization: model=$MODEL device=$DEVICE"

eval "$(python3 /opt/scribe/model_config.py speech-to-text)"

export AUDIO_ANALYZER__MODELS__ASR__PROVIDER=openvino
# audio-analyzer takes the Whisper name without the "openai/" owner and adds it back to export.
export AUDIO_ANALYZER__MODELS__ASR__NAME="${MODEL#openai/}"
export AUDIO_ANALYZER__MODELS__ASR__DEVICE="$DEVICE"
# fp32 is audio-analyzer's unset weight format (export directory without a suffix).
if [ "${PRECISION:-int8}" != fp32 ]; then
    export AUDIO_ANALYZER__MODELS__ASR__WEIGHT_FORMAT="${PRECISION:-int8}"
fi
# Upstream's list plus the formats browsers record (MediaRecorder: WebM/Opus, Ogg).
export AUDIO_ANALYZER__AUDIO_UTIL__ALLOWED_EXTENSIONS='[".wav",".mp3",".m4a",".mp4",".mkv",".mov",".avi",".webm",".weba",".ogg",".oga",".opus",".flac"]'

echo "speech-to-text: model=$MODEL device=$DEVICE precision=${PRECISION:-int8}"
exec python3 -m uvicorn main:app --host 0.0.0.0 --port "${AUDIO_ANALYZER_SERVER_PORT:-8002}"
