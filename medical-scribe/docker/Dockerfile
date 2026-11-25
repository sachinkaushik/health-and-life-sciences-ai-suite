# syntax=docker/dockerfile:1.7
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# Medical Scribe images; build context is the medical-scribe folder (see docker-compose.yaml).
#   workers  diarization, medical-scribe-database and the multiserve text-generation engine
#   stt      speech-to-text: the OEP audio-analyzer wrapper (workers/services/speech-to-text/oep)
#   ui       the Next.js app with EXTERNAL_SERVICES (on `workers`, for the list_models.py catalogs)

ARG UBUNTU_VERSION=24.04

# ---------------------------------------------------------------- runtime --
FROM ubuntu:${UBUNTU_VERSION} AS runtime

ARG DEBIAN_FRONTEND=noninteractive
ARG APP_UID=1000
ARG APP_GID=1000
# Intel GPU/NPU user-space runtime, pinned as upstream audio-analyzer's Dockerfile pins it.
ARG GPU_DRIVER_VERSION=26.18.38308.1
ARG IGC_TAG=v2.34.4
ARG IGC_VERSION=2.34.4+21428
ARG GMMLIB_VERSION=22.10.0
ARG NPU_DRIVER_VERSION=1.33.0
ARG NPU_DRIVER_BUILD=v1.33.0.20260529-26625960453-ubuntu2404
ARG LEVEL_ZERO_VERSION=1.34.0-1~24.04~ppa1
# FFmpeg as the root setup pins it (scripts/bash/setup_thirdparty.sh).
ARG FFMPEG_URL=https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-08-31-13-27/ffmpeg-n9.0.1-11-ge47273f4d9-linux64-gpl-9.0.tar.xz
ARG FFMPEG_SHA256=182c1b509720e939bb47bfb47dc29cc0c298640401128e3dce8627d10707eb5a

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl git python3 python3-dev build-essential lsb-release xz-utils \
        libnuma1 ocl-icd-libopencl1 libtbb12 libsndfile1 libgomp1 libxml2 \
    && mkdir -p /tmp/deps && cd /tmp/deps \
    && for url in \
        "https://github.com/intel/compute-runtime/releases/download/${GPU_DRIVER_VERSION}/libze-intel-gpu1_${GPU_DRIVER_VERSION}-0_amd64.deb" \
        "https://github.com/intel/compute-runtime/releases/download/${GPU_DRIVER_VERSION}/intel-opencl-icd_${GPU_DRIVER_VERSION}-0_amd64.deb" \
        "https://github.com/intel/compute-runtime/releases/download/${GPU_DRIVER_VERSION}/libigdgmm12_${GMMLIB_VERSION}_amd64.deb" \
        "https://github.com/intel/intel-graphics-compiler/releases/download/${IGC_TAG}/intel-igc-core-2_${IGC_VERSION}_amd64.deb" \
        "https://github.com/intel/intel-graphics-compiler/releases/download/${IGC_TAG}/intel-igc-opencl-2_${IGC_VERSION}_amd64.deb" \
        "https://github.com/intel/linux-npu-driver/releases/download/v${NPU_DRIVER_VERSION}/linux-npu-driver-${NPU_DRIVER_BUILD}.tar.gz" \
        "https://ppa.launchpadcontent.net/kobuk-team/intel-graphics/ubuntu/pool/main/l/level-zero-loader/libze1_${LEVEL_ZERO_VERSION}_amd64.deb" \
      ; do curl -fsSL --retry 5 --retry-delay 5 --retry-all-errors -O "$url" || exit 1; done \
    && tar -xf "linux-npu-driver-${NPU_DRIVER_BUILD}.tar.gz" \
    && dpkg -i ./*.deb && ldconfig \
    && curl -fsSL --retry 5 --retry-delay 5 --retry-all-errors -o ffmpeg.tar.xz "$FFMPEG_URL" \
    && echo "${FFMPEG_SHA256}  ffmpeg.tar.xz" | sha256sum -c - \
    && mkdir -p /opt/medical-scribe/thirdparty/ffmpeg/bin \
    && tar -xJf ffmpeg.tar.xz --strip-components=2 -C /opt/medical-scribe/thirdparty/ffmpeg/bin \
        --wildcards '*/bin/ffmpeg' '*/bin/ffprobe' \
    && cd / && rm -rf /tmp/deps /var/lib/apt/lists/* \
    # The base image's `ubuntu` user holds uid 1000.
    && (userdel -r ubuntu 2>/dev/null || true) \
    && groupadd -g "${APP_GID}" appuser \
    && useradd -m --no-log-init -u "${APP_UID}" -g "${APP_GID}" appuser \
    && chown -R "${APP_UID}:${APP_GID}" /opt/medical-scribe

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    HF_HOME=/opt/medical-scribe/models/huggingface \
    PATH=/opt/medical-scribe/thirdparty/ffmpeg/bin:$PATH

WORKDIR /opt/medical-scribe
USER appuser

# ---------------------------------------------------------------- workers --
FROM runtime AS workers

COPY --chown=appuser:appuser scripts/bash scripts/bash
COPY --chown=appuser:appuser workers workers

# uv and OVMS (checked downloads), then the three workers into the shared workers/.venv.
RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=1000,gid=1000 \
    bash workers/setup.sh \
    && workers/upstream-setup.sh fetch common/downloader \
    && workers/thirdparty/uv/uv sync --frozen --inexact --project workers \
        --package diarization --package medical-scribe-database-worker --package multiserve

# -------------------------------------------------------------------- stt --
FROM runtime AS stt

COPY --chown=appuser:appuser scripts/bash scripts/bash
COPY --chown=appuser:appuser workers/scripts workers/scripts
COPY --chown=appuser:appuser workers/common workers/common
COPY --chown=appuser:appuser workers/upstream.json workers/upstream.schema.json workers/upstream-setup.sh workers/
COPY --chown=appuser:appuser workers/services/speech-to-text/oep workers/services/speech-to-text/oep
COPY --from=workers --chown=appuser:appuser /opt/medical-scribe/workers/thirdparty/uv workers/thirdparty/uv

# audio-analyzer at the tag upstream.json pins, in its own .venv from upstream's requirements.
RUN --mount=type=cache,target=/home/appuser/.cache/uv,uid=1000,gid=1000 \
    workers/upstream-setup.sh fetch services/speech-to-text/oep \
    && workers/thirdparty/uv/uv run --no-config --no-project --python 3.12 workers/scripts/oep_env.py \
        --uv workers/thirdparty/uv/uv services/speech-to-text/oep

ENV VIRTUAL_ENV=/opt/medical-scribe/workers/services/speech-to-text/oep/.venv
ENV PATH=$VIRTUAL_ENV/bin:$PATH
WORKDIR /opt/medical-scribe/workers/services/speech-to-text/oep

# --------------------------------------------------------------------- ui --
FROM workers AS ui

# Node as the root setup pins it (scripts/bash/setup_thirdparty.sh).
ARG NODE_VERSION=v24.22.2
ARG NODE_SHA256=48cc0e21e048790e54c0cf5749c2725005313d652651c40b7a21feb9697aaf75

RUN curl -fsSL --retry 5 --retry-delay 5 --retry-all-errors -o /tmp/node.tar.xz \
        "https://nodejs.org/dist/${NODE_VERSION}/node-${NODE_VERSION}-linux-x64.tar.xz" \
    && echo "${NODE_SHA256}  /tmp/node.tar.xz" | sha256sum -c - \
    && mkdir -p thirdparty/node \
    && tar -xJf /tmp/node.tar.xz --strip-components=1 -C thirdparty/node \
    && rm /tmp/node.tar.xz

ENV PATH=/opt/medical-scribe/thirdparty/node/bin:$PATH \
    NEXT_TELEMETRY_DISABLED=1

COPY --chown=appuser:appuser frontend/package.json frontend/package-lock.json frontend/
RUN --mount=type=cache,target=/home/appuser/.npm,uid=1000,gid=1000 \
    cd frontend && npm ci --no-audit --no-fund

COPY --chown=appuser:appuser frontend frontend
COPY --chown=appuser:appuser docs docs
COPY --chown=appuser:appuser deployment.json EXPORT_MANIFEST.json README.md ./

# Build-time placeholders only; the real secret and database come from docker/.env at run time.
RUN cd frontend \
    && PAYLOAD_SECRET=build-only DATABASE_URL=file:/tmp/build.sqlite npm run build \
    && rm -f /tmp/build.sqlite*

WORKDIR /opt/medical-scribe/frontend
CMD ["npm", "run", "start"]
