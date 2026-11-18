# Copyright © 2026 Intel Corporation. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

FROM python:3.12-slim

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --default-timeout=300 --retries=5 -r requirements.txt

COPY proto ./proto
COPY sdc_gateway ./sdc_gateway

RUN useradd --system --uid 10001 sdc
USER sdc

# rPPG gRPC ingest and device-management REST API; SDC/DPWS uses WS-Discovery (UDP 3702) and
# one ephemeral HTTP port per bed.
EXPOSE 50061 8093

CMD ["python", "-m", "sdc_gateway.main"]
