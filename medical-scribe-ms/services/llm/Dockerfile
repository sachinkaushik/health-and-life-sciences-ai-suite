# syntax=docker/dockerfile:1.7
# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#
# LLM: OpenVINO Model Server 2026.4.1 (the release archive, checksum-verified) on the driver-pinned
# base. The model is set at start from the environment (LLM_MODEL), downloaded on first start into
# the models volume. Build context: the app root.

ARG BASE_IMAGE=intel/hl-ai-medical-scribe-base:latest
FROM ${BASE_IMAGE}

ARG OVMS_URL=https://github.com/openvinotoolkit/model_server/releases/download/v2026.4.1/ovms_ubuntu24_2026.4.1_python_off.tar.gz
ARG OVMS_SHA256=2b7198671a9e99e030b408601733fbd61798d8a741337c867b96eb41c295b3f8

USER root
RUN curl -fsSL --retry 5 --retry-delay 5 --retry-all-errors -o /tmp/ovms.tar.gz "$OVMS_URL" \
    && echo "${OVMS_SHA256}  /tmp/ovms.tar.gz" | sha256sum -c - \
    && mkdir -p /opt/ovms \
    && tar -xzf /tmp/ovms.tar.gz --strip-components=1 -C /opt/ovms \
    && rm /tmp/ovms.tar.gz \
    # Chat templates, as workers/setup.sh adds them.
    && uv pip install --no-cache --target /opt/ovms/lib/python "Jinja2==3.1.6" "MarkupSafe==3.0.2"
COPY services/llm/entrypoint.sh /usr/local/bin/llm-entrypoint
RUN chmod 755 /usr/local/bin/llm-entrypoint
USER appuser

ENV LD_LIBRARY_PATH=/opt/ovms/lib \
    PYTHONPATH=/opt/ovms/lib/python \
    PATH=/opt/ovms/bin:$PATH

EXPOSE 8004
ENTRYPOINT ["/usr/local/bin/llm-entrypoint"]
