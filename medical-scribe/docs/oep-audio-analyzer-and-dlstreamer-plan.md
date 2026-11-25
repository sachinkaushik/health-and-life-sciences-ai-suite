# Medical Scribe: OEP audio-analyzer and DL Streamer integration plan

This plan covers two changes to the Medical Scribe exported from Edge AI Demo Studio:

1. **Phase 1:** make the Open Edge Platform (OEP) **audio-analyzer** microservice the speech-to-text engine of the HLS Medical Scribe.
2. **Phase 2:** add **DL Streamer** as an optional speech-to-text backend for room microphones and network audio streams.
3. **Phase 3 (future):** use DL Streamer for video once a camera is in scope.

Design diagram: [`_assets/medical-scribe-oep-dlstreamer-design.drawio`](_assets/medical-scribe-oep-dlstreamer-design.drawio) (open in draw.io or the VS Code Draw.io extension).

## 1. Current state (as exported)

The app is a Next.js frontend that starts native Python workers. Nothing runs in containers. Each worker follows the same contract: `start.sh <args>` plus a `/healthcheck` route.

| Component | Where | Default port | Engine | Main routes |
|---|---|---|---|---|
| Frontend + sample page | `frontend/` | 8080 | Next.js, Payload CMS (SQLite) | Medical Scribe sample, Runtime Settings, service manager |
| Speech to Text | `workers/services/speech-to-text/{oep,ovms,meralion}` | 8023 | One of three backends (see below) | `POST /v1/audio/transcriptions`, live WebSocket |
| Diarization | `workers/services/diarization` | 8026 | pyannote `speaker-diarization-community-1` | `POST /v1/diarize`, `POST /v1/embedding` (doctor voice enrolment) |
| Text generation | `workers/engines/multiserve` | assigned by app | OVMS or llama.cpp; sample recommends `OpenVINO/Qwen3-8B-int8-ov` on GPU | OpenAI-compatible chat |
| Session store | `workers/services/medical-scribe-database` | 8027 | SQLite | `/v1/doctor-profiles`, `/v1/sessions` |

Ports are the worker README defaults; the app assigns the actual port per service instance.

**Sample flow** (`frontend/src/samples/medical-scribe/hooks/use-audio-processing.ts`):

1. The browser records audio (WebM/Opus) or the user uploads a file.
2. The audio goes to Speech to Text, which returns `verbose_json` with word timestamps.
3. The same audio goes to Diarization, which returns speaker turns. The doctor is matched by enrolled voice embedding.
4. The browser aligns the words with the speaker turns.
5. Text generation turns the aligned transcript into a SOAP note.
6. The session (transcript, speakers, SOAP note) is saved to the database.

**Speech-to-text backends.** The backend is selected under Speech to Text → Configure → Advanced settings and stored as `metadata.sttBackend`:

| Backend | What runs | Live mode | Word timestamps | Streaming responses |
|---|---|---|---|---|
| `oep` | OEP audio-analyzer, run natively. Whisper on OpenVINO GenAI, on CPU, GPU or NPU | `/v1/realtime` (OpenAI Realtime-style) | ✓ | SSE and NDJSON |
| `ovms` | Whisper or Qwen3-ASR on OpenVINO Model Server | `/v1/audio/stream` (Silero VAD) | ✓ | – |
| `meralion` | MERaLiON-3-3B-ASR on OpenVINO | `/v1/audio/stream` | – | – |

**How audio-analyzer gets in today:**

- `workers/upstream.json` pins `edge-ai-libraries` at tag `2026.2.1`.
- On every start, `workers/upstream-setup.sh fetch services/speech-to-text/oep` copies `microservices/audio-analyzer` into the worker's `thirdparty/` unchanged.
- The worker builds its own `.venv` from upstream's `requirements.txt`.
- `oep/main.py` runs upstream's FastAPI app. It maps `--model/--device/--precision` to `AUDIO_ANALYZER__MODELS__ASR__*` environment overrides.
- `model-download` (`common/downloader`) is pinned from the same tag.

**Decision:** the OEP audio-analyzer (`oep`) is the speech-to-text engine of the HLS Medical Scribe. The existing pyannote Diarization worker stays as is. The export defaulted to `ovms`, although `workers/services/speech-to-text/README.md` already said `oep`; the default is now `oep`.

## 2. Phase 1: OEP audio-analyzer as the speech-to-text engine

**Goal:** the HLS Medical Scribe uses audio-analyzer out of the box. The other backends stay available.

### Changes

| # | Change | File | Notes |
|---|---|---|---|
| 1 | Default backend `ovms` → `oep` (**done**) | `frontend/src/services/speech-to-text/config.ts` (`DEFAULT_STT_BACKEND`), `frontend/src/lib/instances/service-metadata.ts` (`sttBackend.default`) | Instances with a stored `sttBackend` keep it; the others start on `oep`. |
| 2 | Recommend `oep` + `openai/whisper-large-v3-turbo` on `GPU.0` for the sample | `frontend/src/samples/medical-scribe/data.ts` | Model and device are recommended already. Add a `backend` hint if the speech-to-text dependency supports it, as the text-generation dependency does. |
| 3 | Move the pin to the 2026.3 release when it is tagged | `workers/upstream.json` via `workers/upstream-setup.sh pin <tag>` | The next start re-fetches audio-analyzer and rebuilds its `.venv`. Re-run the validation below. |
| 4 | Keep the separate pyannote Diarization worker | – | audio-analyzer's own diarization (`AUDIO_ANALYZER__MODELS__ASR__DIARIZATION=true`) only gives anonymous `SPEAKER_xx` labels. It has no doctor voice enrolment, which the sample needs. Leave it off so pyannote is not loaded twice. |
| 5 | Document the setup | this file, top-level `README.md` | Hugging Face token (pyannote is gated), proxy, first-start export time. |

### Configuration reference (audio-analyzer)

| Setting | How | Default in the app |
|---|---|---|
| Model | `--model openai/whisper-*` → `AUDIO_ANALYZER__MODELS__ASR__NAME` | `openai/whisper-base` (sample recommends `whisper-large-v3-turbo`) |
| Device | `--device` → `AUDIO_ANALYZER__MODELS__ASR__DEVICE` | CPU / GPU / NPU |
| Precision | `--precision` → `AUDIO_ANALYZER__MODELS__ASR__WEIGHT_FORMAT` | `int8` (also `fp16`, `fp32`, `int4`) |
| Models on disk | `models/stt/openvino/<name>-<precision>`, shared HF cache `models/huggingface` | – |
| Other upstream options | any `AUDIO_ANALYZER__<SECTION>__<KEY>` environment variable | e.g. `AUDIO_ANALYZER__SENTIMENT__ENABLED=true` |

NPU note from the worker README: Whisper runs on the NPU with upstream's pins (transformers 4.53.3, OpenVINO 2026.1). Do not override transformers to 5.x.

### Validation

1. A fresh `./setup.sh --backend sycl` followed by `./start.sh` starts Speech to Text with backend `oep`. `GET /healthcheck` returns 200 with `upstream_tag` equal to the pin.
2. Upload a sample consultation. The transcript has word timestamps; the speakers are aligned; the doctor is matched; the SOAP note is generated and saved.
3. Live mode (`/v1/realtime`) transcribes per utterance and diarization runs in parallel.
4. Re-run steps 1–3 on GPU and on NPU (`whisper-tiny`/`base`), and on Windows (`setup_win.bat` / `start_win.bat`).
5. Record real-time factor and memory per device as the baseline for Phase 2.

## 3. Phase 2: DL Streamer speech-to-text backend (optional)

**Why:**

- The browser-only capture does not cover fixed exam-room microphones, network (RTSP) audio from room devices, or many rooms on one edge server.
- DL Streamer provides those sources plus multi-stream handling. It also aligns the scribe with the other suite apps' pipeline framework.

**Not a goal:** better accuracy or speed than Phase 1. `gvaaudiotranscribe` also runs Whisper on OpenVINO.

### Design

- **New worker** `workers/services/speech-to-text/dlstreamer/`, selected as `sttBackend = 'dlstreamer'`. It follows the same `start.sh --port --model --device --precision` and `/healthcheck` contract.
- **Thin FastAPI adapter.** It exposes the same `POST /v1/audio/transcriptions` as the other backends, so the frontend, the sample and the tests stay unchanged. It also exposes a source API for room streams, e.g. `POST /v1/sources` with `{ "uri": "rtsp://…" | "alsa://hw:1,0" }`.
- **Pipeline** (per request or per room source):

  ```text
  <source> ! decodebin3 ! audioresample ! audioconvert
    ! audio/x-raw,format=S16LE,channels=1,rate=16000
    ! gvaaudiotranscribe model=<whisper OpenVINO IR> device=GPU
    ! gvametaconvert format=json ! appsink
  ```

  `<source>` is `filesrc` (uploads), `appsrc` (browser live audio), `alsasrc device=hw:X,Y` (room microphone) or `urisourcebin uri=rtsp://…` (network audio).
- **Models.** Reuse the Phase 1 Whisper OpenVINO export under `models/stt/openvino/` if `gvaaudiotranscribe` accepts it, to avoid a second copy.
- **Diarization and SOAP flow are unchanged.** The adapter returns `verbose_json` so the browser's alignment step still works.

### Open questions (verify before building)

| Question | Why it matters |
|---|---|
| Does `gvaaudiotranscribe` produce word (or segment) timestamps? | Alignment with speaker turns needs word times. Without them, the adapter needs a forced aligner or segment-level alignment. |
| Which Whisper exports and devices does it support (CPU/GPU/NPU)? | Decides whether the Phase 1 model files can be shared. |
| How do we install DL Streamer natively on Ubuntu and Windows 11? | The app has no containers; DL Streamer is usually used as a Docker image in the suite. |
| How does live (streaming) mode fit? | `/v1/realtime` from Phase 1 would have to be re-implemented on `appsrc` with VAD. |
| How do we limit Demo Studio upstream drift? | The scribe is an export; propose the backend upstream to Demo Studio rather than keep a fork. |

## 4. Phase 3: video (future, when a camera is in scope)

Add a video branch next to the audio pipeline:

```text
camera ! decodebin3 ! gvadetect ! gvatrack ! gvagenai (VLM)
```

It would produce context events, e.g. "patient on the bed" or "device screen reading", that the SOAP prompt can cite. This is where DL Streamer adds the most value: one pipeline for decode, detection and VLM across many rooms. Plan it only once video is in the HLS 2027 requirements.

## 5. Risks

- **First-start time and disk.** audio-analyzer installs torch and OpenVINO into its own `.venv` and exports Whisper on first start (minutes, several GB).
- **Gated model.** The pyannote model needs a Hugging Face account that has accepted the model terms, plus a token in the app.
- **Proxy.** On the Intel network some proxy nodes intercept TLS; downloads may need retries.
- **Upstream tag bumps.** A new audio-analyzer tag can change pins (for example transformers), which affects NPU support. Re-run the Phase 1 validation on every pin change.
