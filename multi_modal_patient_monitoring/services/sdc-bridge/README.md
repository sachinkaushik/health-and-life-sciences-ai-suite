# SDC Bridge

An IEEE 11073 SDC consumer. It finds the SDC Gateway (or any provider that uses the same MDC/vendor codes), subscribes to its episodic metric and waveform reports, and passes the data to the existing MMPM services:

- **Device metrics.** These are sent to the aggregator over gRPC `StreamVitals` (:50051) with the OpenICE metric names (`MDC_ECG_HEART_RATE`, `MDC_ECG_LEAD_II`, ...). They are sent only after `POST /start`, which is the same control contract as `dds-bridge`. Waveforms are grouped into 1 s windows.
- **rPPG metrics.** These are always sent as device `rppg-001`, using the same metric names the rPPG service uses.
- **AI-ECG results.** `GET /predict_stream_next` returns `{file, signal, result, inference_ms, length, timestamp}`, so the aggregator's AI-ECG poller can use it unchanged.

Mapping is by `CodedValue` (coding system + code), not by handle (see `sdc_bridge/mapping.py`).

## API (:8092)

| Method | Path | Response |
|---|---|---|
| POST | `/start` / `/stop` | `{"status": "started"}` / `{"status": "stopped"}` |
| GET | `/status` | `{"enabled", "connected", "provider"}` |
| GET | `/predict_stream_next` | Latest AI-ECG result, or 503 if there isn't one yet |
| GET | `/health` | Liveness |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SDC_BIND_IP` | IP of the interface with the default route | Interface used for WS-Discovery |
| `SDC_PROVIDER_EPR` | Gateway EPR | Provider to connect to. Leave it empty to accept the first SDC device found |
| `SDC_PROVIDER_XADDR` | unset | Connect directly to this address and skip discovery |
| `SDC_SSL_DIR` | unset (no TLS) | Folder containing `userkey.pem`, `usercert.pem` and `cacert.pem` |
| `GRPC_HOST` / `GRPC_PORT` | `localhost` / `50051` | Aggregator address |
| `CONTROL_PORT` | `8092` | Port for the HTTP API |
| `DEVICE_ID_PREFIX` | `sdc-monitor` | Device IDs are `<prefix>-ecg`, `<prefix>-co2` and `<prefix>-ibp` |
| `WAVE_FORWARD_MS` | `1000` | Length of the waveform window sent to the aggregator |
