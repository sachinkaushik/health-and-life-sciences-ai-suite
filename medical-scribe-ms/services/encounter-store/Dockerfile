# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
FROM python:3.12-slim

ARG APP_UID=1000
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt \
    && useradd -m --no-log-init -u "${APP_UID}" appuser \
    && mkdir -p /data && chown appuser /data
COPY app app

USER appuser
EXPOSE 8001
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/healthz', timeout=4)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
