# SDC Bridge

An IEEE 11073 SDC consumer. It discovers every SDC provider (bed) whose location facility is `SDC_FACILITY`. This includes the beds of the SDC Gateway and any other provider that uses the same MDC or vendor codes. The bridge subscribes to each provider's episodic metric and waveform reports and drops providers that disappear. It passes the data to the existing MMPM services:

- **Device metrics from every bed.** These are sent to the aggregator over gRPC `StreamVitals` (:50051) with the OpenICE metric names (`MDC_ECG_HEART_RATE`, `MDC_PULS_OXIM_SAT_O2`, `MDC_ECG_LEAD_II`, ...).
  - The device IDs are `<bed>-ecg`, `<bed>-spo2`, `<bed>-temp`, `<bed>-co2` and `<bed>-ibp`.
  - Each vital carries the metadata `bed_id` and `primary`.
  - Metrics are sent only after `POST /start`, which is the same control contract as `dds-bridge`.
  - Waveforms are grouped into 1 s windows.
- **rPPG metrics (primary bed only).** These are sent as device `rppg-001`, using the same metric names the rPPG service uses.
- **AI-ECG results (primary bed only).** `GET /predict_stream_next` returns `{file, signal, result, inference_ms, length, timestamp}`, so the aggregator's AI-ECG poller can use it unchanged.

The primary bed is the provider whose EPR is `SDC_PROVIDER_EPR`, which is `bed-01` of the gateway. The bed ID is taken from the provider's location (`bed=`). Mapping is by `CodedValue` (coding system + code), not by handle (see `sdc_bridge/mapping.py`).

## API (:8092)

| Method | Path | Response |
|---|---|---|
| POST | `/start` / `/stop` | `{"status": "started"}` / `{"status": "stopped"}` |
| GET | `/beds` | `{"enabled", "beds": [{bed_id, epr, location, primary, type, ai, video_url, connected}]}` |
| GET | `/status` | `{"enabled", "connected", "provider", "beds"}` |
| GET | `/predict_stream_next` | Latest AI-ECG result, or 503 if there isn't one yet |
| GET | `/health` | Liveness |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SDC_BIND_IP` | IP of the interface with the default route | Interface used for WS-Discovery |
| `SDC_FACILITY` | `MMPM` | Only providers in this facility are used. Leave it empty to accept every SDC device found |
| `SDC_PROVIDER_EPR` | Gateway `bed-01` EPR | Primary bed (rPPG, AI-ECG and the single-patient workload view) |
| `SDC_PROVIDER_XADDR` | unset | Connect directly to this one address as the primary bed and skip discovery |
| `SDC_SSL_DIR` | unset (no TLS) | Folder containing `userkey.pem`, `usercert.pem` and `cacert.pem` |
| `GRPC_HOST` / `GRPC_PORT` | `localhost` / `50051` | Aggregator address |
| `CONTROL_PORT` | `8092` | Port for the HTTP API |
| `WAVE_FORWARD_MS` | `1000` | Length of the waveform window sent to the aggregator |
