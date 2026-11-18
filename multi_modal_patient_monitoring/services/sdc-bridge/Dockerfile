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
COPY sdc_bridge ./sdc_bridge

RUN useradd --system --uid 10001 sdc
USER sdc

# Control API (/start, /stop, /status, /predict_stream_next).
EXPOSE 8092

CMD ["python", "-m", "sdc_bridge.main"]
