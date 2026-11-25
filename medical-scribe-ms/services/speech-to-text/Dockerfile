# syntax=docker/dockerfile:1.7
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# Speech to text: the OEP audio-analyzer (edge-ai-libraries, tag pinned in libs/workers/upstream.json)
# behind the thin `oep` wrapper (health check, browser formats, --model/--device flags).
# Build context: the app root.

ARG BASE_IMAGE=intel/hl-ai-medical-scribe-base:latest
FROM ${BASE_IMAGE}

COPY --chown=appuser:appuser libs/scripts/bash scripts/bash
COPY --chown=appuser:appuser libs/workers/scripts workers/scripts
COPY --chown=appuser:appuser libs/workers/common workers/common
COPY --chown=appuser:appuser libs/workers/upstream.json libs/workers/upstream.schema.json libs/workers/upstream-setup.sh workers/
COPY --chown=appuser:appuser libs/workers/services/speech-to-text/oep workers/services/speech-to-text/oep

# audio-analyzer at the pinned tag, in its own .venv from upstream's requirements.
RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=1000,gid=1000 \
    workers/upstream-setup.sh fetch services/speech-to-text/oep \
    && uv run --no-config --no-project --python 3.12 workers/scripts/oep_env.py \
        --uv workers/thirdparty/uv/uv services/speech-to-text/oep

ENV VIRTUAL_ENV=/opt/medical-scribe/workers/services/speech-to-text/oep/.venv \
    SERVER_HOST=0.0.0.0
ENV PATH=$VIRTUAL_ENV/bin:$PATH
WORKDIR /opt/medical-scribe/workers/services/speech-to-text/oep

EXPOSE 8002
CMD ["sh", "-c", "exec python main.py --port=8002 --model=\"${STT_MODEL}\" --device=\"${STT_DEVICE}\" --precision=\"${STT_PRECISION}\" --instance-id=speech-to-text --data-dir=/opt/medical-scribe/data/speech-to-text"]
