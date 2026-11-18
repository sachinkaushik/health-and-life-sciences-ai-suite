#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Select the bedside-device path: openice (MD PnP + DDS bridge) or sdc (IEEE 11073 SDC gateway + bridge).
# An exported DEVICE_SOURCE (e.g. from `make run DEVICE_SOURCE=sdc`) overrides configs/device.env.
configure_device_source() {
  case "${DEVICE_SOURCE:-openice}" in
    openice)
      export COMPOSE_PROFILES=openice
      ;;
    sdc)
      export COMPOSE_PROFILES=sdc
      export DEVICE_CONTROL_URL=http://localhost:8092
      export AGGREGATOR_AI_ECG_URL=http://localhost:8092/predict_stream_next
      export RPPG_AGGREGATOR_PORT=50061
      ;;
    *)
      echo "Invalid DEVICE_SOURCE='${DEVICE_SOURCE}' (expected openice or sdc)" >&2
      exit 1
      ;;
  esac
  echo "Device source: ${DEVICE_SOURCE:-openice}" >&2
}

if [[ ! -f "${ROOT_DIR}/configs/device.env" ]]; then
  echo "configs/device.env not found; running without NPU override" >&2
  configure_device_source
  exec docker compose -f "${ROOT_DIR}/docker-compose.yaml" up "$@"
fi

DEVICE_SOURCE_OVERRIDE="${DEVICE_SOURCE:-}"
source "${ROOT_DIR}/configs/device.env"
DEVICE_SOURCE="${DEVICE_SOURCE_OVERRIDE:-${DEVICE_SOURCE:-}}"
configure_device_source

TMP_OVERRIDE="$(mktemp)"
trap 'rm -f "${TMP_OVERRIDE}"' EXIT

echo "services:" > "${TMP_OVERRIDE}"

HAS_NPU=false
RENDER_GROUP_ID=""

resolve_render_group_id() {
  if getent group render >/dev/null 2>&1; then
    getent group render | cut -d: -f3
    return 0
  fi

  if [[ -e /dev/accel/accel0 ]]; then
    stat -c '%g' /dev/accel/accel0
    return 0
  fi

  if [[ -d /dev/accel ]]; then
    stat -c '%g' /dev/accel
    return 0
  fi

  return 1
}

enable_npu_override() {
  HAS_NPU=true

  if [[ -z "${RENDER_GROUP_ID}" ]]; then
    if ! RENDER_GROUP_ID="$(resolve_render_group_id)"; then
      echo "Unable to resolve the host render group for NPU access. Ensure the render group and /dev/accel devices are available." >&2
      exit 1
    fi
  fi
}

if [[ "${ECG_DEVICE:-}" == "NPU" ]]; then
  enable_npu_override
  cat >> "${TMP_OVERRIDE}" <<EOF
  ai-ecg:
    environment:
      - ZE_ENABLE_ALT_DRIVERS=libze_intel_npu.so
    devices:
      - "/dev/dri:/dev/dri"
      - "/dev/accel/accel0:/dev/accel/accel0"
    group_add:
      - "${RENDER_GROUP_ID}"
EOF
fi

if [[ "${POSE_3D_DEVICE:-}" == "NPU" ]]; then
  enable_npu_override
  cat >> "${TMP_OVERRIDE}" <<EOF
  3dpose-estimation:
    environment:
      - ZE_ENABLE_ALT_DRIVERS=libze_intel_npu.so
    devices:
      - "/dev/dri:/dev/dri"
      - "/dev/accel/accel0:/dev/accel/accel0"
    group_add:
      - "${RENDER_GROUP_ID}"
EOF
fi

if [[ "${RPPG_DEVICE:-}" == "NPU" ]]; then
  enable_npu_override
  cat >> "${TMP_OVERRIDE}" <<EOF
  rppg:
    environment:
      - ZE_ENABLE_ALT_DRIVERS=libze_intel_npu.so
    devices:
      - "/dev/dri:/dev/dri"
      - "/dev/accel/accel0:/dev/accel/accel0"
    group_add:
      - "${RENDER_GROUP_ID}"
EOF
fi

if [[ "${HAS_NPU}" == true ]]; then
  echo "Detected NPU devices in configs/device.env; using runtime override ${TMP_OVERRIDE}" >&2
  exec docker compose --env-file "${ROOT_DIR}/configs/device.env" -f "${ROOT_DIR}/docker-compose.yaml" -f "${TMP_OVERRIDE}" up "$@"
else
  echo "No NPU devices configured in configs/device.env; running without NPU override" >&2
  exec docker compose --env-file "${ROOT_DIR}/configs/device.env" -f "${ROOT_DIR}/docker-compose.yaml" up "$@"
fi

