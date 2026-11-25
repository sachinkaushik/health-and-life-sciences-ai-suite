# syntax=docker/dockerfile:1.7
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# Shared runtime of the GPU/NPU services (diarization, text-generation). `make build` builds it
# first as ${REGISTRY}hl-ai-medical-scribe-base:${TAG}; the services start FROM it.

ARG UBUNTU_VERSION=24.04
FROM ubuntu:${UBUNTU_VERSION}

ARG DEBIAN_FRONTEND=noninteractive
ARG APP_UID=1000
ARG APP_GID=1000
# GPU stack = the host-validated 26.05: with 26.18 (also in openvino/model_server:2026.4.1-gpu)
# Qwen3.5-4B int4 on OVMS writes garbage on Arrow Lake.
ARG GPU_DRIVER_VERSION=26.05.37020.3
ARG IGC_TAG=v2.28.4
ARG IGC_VERSION=2.28.4+20760
ARG GMMLIB_VERSION=22.9.0
ARG NPU_DRIVER_VERSION=1.33.0
ARG NPU_DRIVER_BUILD=v1.33.0.20260529-26625960453-ubuntu2404
ARG LEVEL_ZERO_VERSION=1.34.0-1~24.04~ppa1
ARG FFMPEG_URL=https://github.com/BtbN/FFmpeg-Builds/releases/download/autobuild-2026-08-31-13-27/ffmpeg-n9.0.1-11-ge47273f4d9-linux64-gpl-9.0.tar.xz
ARG FFMPEG_SHA256=182c1b509720e939bb47bfb47dc29cc0c298640401128e3dce8627d10707eb5a
ARG UV_URL=https://releases.astral.sh/github/uv/releases/download/0.13.7/uv-x86_64-unknown-linux-gnu.tar.gz
ARG UV_SHA256=c5221ff41b7892bfc223543883600125f6a47fe845093e0f5bdff4f359196d83

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
    && curl -fsSL --retry 5 --retry-delay 5 --retry-all-errors -o uv.tar.gz "$UV_URL" \
    && echo "${UV_SHA256}  uv.tar.gz" | sha256sum -c - \
    && mkdir -p /opt/medical-scribe/workers/thirdparty/uv \
    && tar -xzf uv.tar.gz --strip-components=1 -C /opt/medical-scribe/workers/thirdparty/uv \
    && cd / && rm -rf /tmp/deps /var/lib/apt/lists/* \
    # The base image's `ubuntu` user holds uid 1000.
    && (userdel -r ubuntu 2>/dev/null || true) \
    && groupadd -g "${APP_GID}" appuser \
    && useradd -m --no-log-init -u "${APP_UID}" -g "${APP_GID}" appuser \
    && mkdir -p /opt/medical-scribe/models /opt/medical-scribe/data /opt/medical-scribe/logs \
    && chown -R "${APP_UID}:${APP_GID}" /opt/medical-scribe

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    HF_HOME=/opt/medical-scribe/models/huggingface \
    PATH=/opt/medical-scribe/thirdparty/ffmpeg/bin:/opt/medical-scribe/workers/thirdparty/uv:$PATH

WORKDIR /opt/medical-scribe
USER appuser
