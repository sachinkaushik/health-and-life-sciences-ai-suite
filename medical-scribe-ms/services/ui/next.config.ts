// Copyright (C) 2026 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
import type { NextConfig } from 'next'

// Presentation only: every /api call goes to the scribe-aggregator through the gateway.
const nextConfig: NextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  reactStrictMode: true,
}

export default nextConfig
