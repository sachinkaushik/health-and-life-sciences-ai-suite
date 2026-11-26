# Copyright (C) 2026 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
FROM nginxinc/nginx-unprivileged:1.29-alpine
COPY default.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
# -Y off: Docker injects the host's proxy settings, and busybox wget ignores no_proxy.
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD wget -Y off -q -O /dev/null http://127.0.0.1:8080/api/healthz || exit 1
