# Medical Scribe: architecture proposal for review

Related: [changes summary](changes-summary.md), [containerization plan](containerization-plan.md), [OEP audio-analyzer plan](oep-audio-analyzer-and-dlstreamer-plan.md).

## 1. Proposals at a glance

| # | Proposal | Why | Status |
|---|---|---|---|
| 1 | Containerize the app (`make up`) | Same deployment as the other HLS suite apps. Today the Demo Studio frontend starts every service itself as a native process. | Done: 5 containers running on Arrow Lake |
| 2 | Use OEP **audio-analyzer** for speech to text | Reuse the Open Edge Platform microservice instead of the Demo Studio OVMS / Qwen3-ASR worker | Done: default backend is `oep` |
| 3 | Use **performance-tools** for hardware metrics | Same metrics as `multi_modal_patient_monitoring`: CPU, GPU, NPU, memory, power from one upstream collector | Proposed |
| 4 | UI: from "Edge AI Demo Studio" to a **Medical Scribe** app | The exported UI is a generic studio (services, samples, start/stop). Clinicians only need consultations; the demo needs hardware metrics. | Step 1 done (`APP_MODE=medical-scribe`) |

## 2. Containerization

- One multi-stage `docker/Dockerfile` builds three images:

  | Image | Contains |
  |---|---|
  | `medical-scribe-workers` | diarization, multiserve (OVMS), database |
  | `medical-scribe-stt` | audio-analyzer and its wrapper |
  | `medical-scribe-ui` | Next.js frontend |

- `docker/docker-compose.yaml` runs five services:

  | Service | Port |
  |---|---|
  | ui | 8080 |
  | speech-to-text | 8190 |
  | diarization | 8191 |
  | text-generation | 8192 |
  | medical-scribe-database | 8193 |

- `Makefile`: `make setup`, `make build`, `make up`, `make down`, `make status`, `make logs`.
- Host networking: the browser's live-mode WebSockets go straight to the speech-to-text and diarization ports.
- All containers:
  - run as a non-root user;
  - get the GPU (`/dev/dri`) and NPU (`/dev/accel`), with the `render`/`video` groups;
  - have proxy settings and a healthcheck;
  - share bind-mounted `models/`, `data/` and `logs/` with the native run.
- Frontend change kept small: `EXTERNAL_SERVICES` env. The app uses the containers on fixed ports and never spawns or stops them. No database schema change.
- `deployment.json` creates and configures the four services, and is applied on every start.
- Native `./setup.sh` / `./start.sh` still works; Windows stays native.

## 3. Speech to text: audio-analyzer

- `stt` image = upstream audio-analyzer (pinned `edge-ai-libraries` tag `2026.2.1`, unchanged) + the `oep` worker as a thin wrapper.
- Whisper `large-v3-turbo`, int8, OpenVINO on GPU (CPU and NPU supported).
- Diarization stays on the separate pyannote worker, because it does doctor voice enrolment.

## 4. Performance metrics: performance-tools

Reference: `multi_modal_patient_monitoring/docker-compose.yaml`.

- **The reference pattern:**
  - Service `metrics-collector`, using image `intel/retail-benchmark:${TAG}` (published from `intel-retail/performance-tools`; tag `2026.3.0-rc1`).
  - HTTP API on `:9000`: `GET /metrics` (time series), `/platform-info`, `/memory`, `/workload-devices`.
  - Collects CPU, GPU (qmassa), NPU, memory and power. Raw logs go to `./metrics` (qmassa JSON, NPU CSV).
  - Runs with `privileged: true`, `pid: host`, host network, and mounts `/sys`, `/proc`, `/dev/dri`.
  - The UI polls every 3 s (`MetricsPoller`) and charts it (`ResourceUtilizationAccordion`).
- **Proposed for Medical Scribe:**
  - Add the same `metrics-collector` service to `docker/docker-compose.yaml`.
  - The UI **System** page reads from it, through the UI server, instead of the in-app collector.
  - This fixes a current gap: the in-app collector needs `qmassa`, which is not in the UI image, so GPU usage is missing in containers.
  - Add **app-level** metrics per encounter, which performance-tools does not have:
    - speech-to-text speed vs. real time (RTF);
    - diarization time;
    - LLM time to first token and tokens/s;
    - end-to-end time from audio to SOAP note.

## 5. UI: Medical Scribe app

- **Done (step 1):**
  - `APP_MODE=medical-scribe` (read at run time; one image serves both modes). `studio` keeps the original UI.
  - Branding "Medical Scribe".
  - Sidebar: Today, Consultations, System. Hidden: Samples, Services, Settings, search, Start/Stop/Configure.
  - **Today** page:
    - Start consultation, Open last encounter;
    - counts for today, awaiting a note, total, doctor voices;
    - recent encounters;
    - AI pipeline status.
  - **Consultations**: doctor profiles, encounters, transcript, SOAP note. A read-only "Getting the AI ready" panel replaces service controls.
- **Next:**
  - Encounter review: transcript and SOAP note side by side, click a sentence to see its source, mark reviewed, export.
  - Encounters table: search and filter by date, doctor, status.
  - System page with the performance-tools metrics and per-encounter timings (section 4).
  - Note templates per specialty; data-retention setting.

## 6. Gaps in the services we use directly, and what we can do

### audio-analyzer (OEP, upstream)

| Gap | Today (our workaround) | Proposal |
|---|---|---|
| No `/healthcheck` that waits for model export and warm-up | Wrapper adds it (503 until ready) | Contribute upstream |
| Rejects browser audio (WebM/Opus) | Wrapper converts uploads | Contribute upstream |
| Settings only through `AUDIO_ANALYZER__*` env, no CLI flags | Wrapper maps `--model/--device/--precision` | Keep in wrapper, or document upstream |
| Built-in diarization gives only anonymous `SPEAKER_xx`, no voice enrolment | Separate pyannote worker | Propose enrolment / speaker-embedding API upstream |
| Exports Whisper on first start (minutes, GBs) | Shared `models/` volume, 20 min start period | Pre-export step (`model-init` / `make download-models`) |
| Dependency pins (e.g. transformers) decide NPU support | Pinned tag `2026.2.1`; upstream compose already uses `2026.3.0-rc1` | Move to `2026.3`; re-validate GPU/NPU on every tag bump |
| Published `intel/audio-analyzer` image cannot be used as is, because of the gaps above | Built from the same pinned source | After upstreaming: `FROM intel/audio-analyzer:<tag>` plus a thin layer, or no layer |

### performance-tools (`intel/retail-benchmark`)

| Gap | Proposal |
|---|---|
| Hardware metrics only; no per-request or per-stage AI timings | App records per-encounter timings in the database worker; show them next to the hardware charts |
| Needs `privileged` and `pid: host` | Acceptable for demo/benchmark; keep it optional (compose profile `metrics`) for production-like deployments |
| Retail-named image used in the health suite; RC tag | Ask for a neutral image name / GA tag; pin it in `.env` |

### Speaker diarization (pyannote, Demo Studio worker)

| Gap | Proposal |
|---|---|
| Requires `HF_TOKEN` on every start, even when the gated model is already cached | Allow offline load from cache (`HF_HUB_OFFLINE`); token needed only for the first download |
| Runs on CPU in the container; Intel GPU (`xpu`) not validated there | Validate the `xpu` torch wheels in the image; make the device a `.env` setting (already `DIARIZATION_DEVICE`) |

### Text generation (multiserve + OVMS, Demo Studio engine)

| Gap | Proposal |
|---|---|
| Container is "healthy" before a model is loaded; the UI loads the model over HTTP after boot | Readiness check that includes the model; or load the model at container start from `.env` |
| Needs extra system libraries (`libxml2`) not in the release archive's docs | Fixed in the image; report upstream |
| Alternative: official `openvino/model_server` image | Possible later; the UI's model switching would then need a different path |

### Demo Studio frontend (export)

| Gap | Proposal |
|---|---|
| Can only use services it starts itself | Added `EXTERNAL_SERVICES`; propose upstream so re-exports keep it |
| Generic studio UI | Added `APP_MODE`; propose a "single app" mode upstream |
| Re-exporting overwrites our changes | Keep changes small and isolated; upstream them |
| Only probes ports in 8100–8199 | Containers use 8190–8193 |

### Build and infrastructure

| Gap | Proposal |
|---|---|
| Intel proxy sometimes intercepts GitHub release downloads (TLS) | Retries already in the build; optional corporate CA as a BuildKit secret; never disable TLS checks |
| Large images (torch + OpenVINO) | Separate CPU / GPU variants; share base layers |
| No published images yet | Push to the `intel/` registry with SBOM, third-party notices and scan (release phase) |

## 7. Decisions needed from the architect

1. Adopt `intel/retail-benchmark` (performance-tools) as the metrics source for this app, with the `privileged` / `pid: host` collector?
2. Keep our audio-analyzer wrapper image, or upstream the wrapper features and use the published `intel/audio-analyzer` image?
3. Upstream `EXTERNAL_SERVICES` and `APP_MODE` to Demo Studio, or keep them local in this export?
4. Diarization: stay on CPU, or invest in `xpu` in the container?
5. Text generation: keep multiserve (UI-driven model switching) or move to the official OVMS image?
