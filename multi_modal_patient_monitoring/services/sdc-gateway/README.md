# SDC Gateway

An IEEE 11073 SDC provider (`sdc11073` 2.x) that publishes one MMPM patient monitor on the network:

| VMD | Channel | Metrics | Source |
|---|---|---|---|
| `vmd.device` | `ch.ecg` | HR, RR, ECG leads I/II/III (250 Hz) | Built-in physiological simulator |
| | `ch.co2` | EtCO2, RR, capnogram (20 Hz) | Built-in physiological simulator |
| | `ch.ibp` | SYS, DIA, MEAN, arterial pressure (120 Hz) | Built-in physiological simulator |
| `vmd.rppg` | `ch.rppg` | HR, RR, averages, pulse and respiration waves (30 Hz) | rPPG service over gRPC `StreamVitals` (:50061) |
| `vmd.aiecg` | `ch.aiecg` | ECG strip (360 Hz), rhythm label, source file, latency | Polls the AI-ECG service |

The waveforms are sent as `RealTimeSampleArrayMetric` updates in 200 ms chunks. The numerics update once per second.

## Configuration

| Variable | Default | Description |
|---|---|---|
| `SDC_BIND_IP` | IP of the interface with the default route | Interface used for WS-Discovery and DPWS |
| `SDC_EPR` | `urn:uuid:6b3e0c1e-5f7a-4d2b-9c8e-1a2b3c4d5e01` | Endpoint reference that consumers filter on |
| `SDC_SSL_DIR` | unset (no TLS) | Folder containing `userkey.pem`, `usercert.pem` and `cacert.pem` |
| `SDC_FACILITY` / `SDC_POINT_OF_CARE` / `SDC_BED` | `MMPM` / `ICU` / `BED01` | Location context |
| `SIM_ENABLED`, `RPPG_ENABLED`, `AI_ECG_ENABLED` | `true` | Turn each source on or off |
| `RPPG_GRPC_PORT` | `50061` | Port where rPPG data is received |
| `AI_ECG_URL` | `http://localhost:8000/predict_stream_next` | AI-ECG endpoint that is polled |
| `AI_ECG_POLL_SECONDS` | `1.0` | AI-ECG polling interval |
| `WAVE_CHUNK_MS` | `200` | Length of each simulator waveform chunk |

## Run locally

```bash
pip install -r requirements.txt
python -m sdc_gateway.main
```
