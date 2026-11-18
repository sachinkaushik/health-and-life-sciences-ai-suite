# SDC Gateway

An IEEE 11073 SDC gateway (`sdc11073` 2.x) that publishes simulated MMPM beds on the network. Each bed is its own
SDC provider, with its own EPR and the location `fac=<SDC_FACILITY>;poc=<SDC_POINT_OF_CARE>;bed=bed-NN`.

There are two kinds of bed:

- **monitor**: a multiparameter patient monitor (MPM) with the `vmd.device` VMD only.
- **multimodal**: a monitor plus a room camera (`vmd.video`). The primary bed `bed-01` is always multimodal and also
  carries the live rPPG and AI-ECG workloads.

| VMD | Channel | Handles | Source | Beds |
|---|---|---|---|---|
| `vmd.device` | `ch.ecg` | `numeric.hr`, `numeric.rr`, `wave.ecg_ii` (250 Hz, mV) | Built-in simulator | all |
| | `ch.spo2` | `numeric.spo2`, `wave.pleth` (100 Hz) | Built-in simulator | all |
| | `ch.temp` | `numeric.temp` (Cel) | Built-in simulator | all |
| | `ch.co2` | `numeric.etco2`, `numeric.rr_co2`, `wave.co2` (20 Hz) | Built-in simulator | all |
| | `ch.ibp` | `numeric.nibp_sys`, `numeric.nibp_dia`, `numeric.nibp_map`, `wave.abp` (120 Hz) | Built-in simulator | all |
| `vmd.video` | `ch.video` | `string.video_stream_url` | `VIDEO_STREAM_URLS` | multimodal |
| `vmd.rppg` | `ch.rppg` | `numeric.rppg_hr`, `numeric.rppg_rr`, `numeric.rppg_hr_avg`, `numeric.rppg_rr_avg`, `wave.rppg`, `wave.rppg_resp` (30 Hz) | rPPG service over gRPC `StreamVitals` (:50061) | `bed-01` |
| `vmd.aiecg` | `ch.aiecg` | `wave.ai_rhythm_strip` (360 Hz), `string.ai_rhythm`, `string.ai_rhythm_source`, `numeric.ai_rhythm_latency` | Polls the AI-ECG service | `bed-01` |

The handles and UCUM units (coding system `urn:oid:1.2.840.10008.2.16.4`) follow the convention that SDC central
stations such as the SDC-Dashboard read. The pressure numerics use the arterial-line MDC codes. The waveforms are sent
as `RealTimeSampleArrayMetric` updates in 200 ms chunks, and the numerics update once per second. Each simulated bed
starts from different baselines.

## Device-management API

The API listens on `SDC_MGMT_HOST:SDC_MGMT_PORT` (default `127.0.0.1:8093`). It has no authentication, so keep it on
localhost or behind a trusted proxy.

| Method | Path | Description |
|---|---|---|
| `GET` | `/devices` | List the beds |
| `POST` | `/devices` | Add a bed. The body is `{"type": "monitor"}` or `{"type": "multimodal"}`. Returns 201, or 409 when `SDC_MAX_DEVICES` is reached |
| `DELETE` | `/devices/{bed_id}` | Remove a bed (WS-Discovery Bye). Returns 204, 404 for an unknown bed, or 409 for `bed-01` |
| `GET` | `/health` | Liveness |

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SDC_BIND_IP` | IP of the interface with the default route | Interface used for WS-Discovery and DPWS |
| `SDC_EPR` | `urn:uuid:6b3e0c1e-5f7a-4d2b-9c8e-1a2b3c4d5e01` | EPR of `bed-01`. Other beds get a stable UUIDv5 from the facility and bed ID |
| `SDC_SSL_DIR` | unset (no TLS) | Folder containing `userkey.pem`, `usercert.pem` and `cacert.pem` |
| `SDC_FACILITY` / `SDC_POINT_OF_CARE` | `MMPM` / `ICU` | Location context. Consumers filter on the facility |
| `SDC_EXTRA_DEVICES` | empty | Comma-separated beds to create at start-up, for example `monitor,monitor,multimodal` |
| `SDC_MAX_DEVICES` | `16` | Maximum number of beds, including `bed-01` |
| `VIDEO_STREAM_URLS` | `http://<bind-ip>:8085/video_feed` | Comma-separated camera URLs, given to multimodal beds in turn |
| `SDC_MGMT_HOST` / `SDC_MGMT_PORT` | `127.0.0.1` / `8093` | Device-management API |
| `SIM_ENABLED`, `RPPG_ENABLED`, `AI_ECG_ENABLED` | `true` | Turn each source on or off |
| `RPPG_GRPC_PORT` | `50061` | Port where rPPG data is received |
| `AI_ECG_URL` | `http://localhost:8000/predict_stream_next` | AI-ECG endpoint that is polled |
| `AI_ECG_POLL_SECONDS` | `1.0` | AI-ECG polling interval |
| `WAVE_CHUNK_MS` | `200` | Length of each simulator waveform chunk |

## Run locally

```bash
pip install -r requirements.txt
SDC_EXTRA_DEVICES=monitor,multimodal python -m sdc_gateway.main
curl -X POST localhost:8093/devices -H 'Content-Type: application/json' -d '{"type": "monitor"}'
```
