# How it works

![Medical Scribe high-level architecture](_assets/architecture.png)

## Services and responsibilities

| Service | Owns | Talks to |
|---|---|---|
| **gateway** (nginx) | The single entry point: `/` → ui, `/api` → scribe-aggregator (HTTP, server-sent events, WebSocket) | ui, scribe-aggregator |
| **ui** (Next.js) | Screens only: Today, Consultations, System | `/api` only |
| **scribe-aggregator** (FastAPI) | The Medical Scribe workflow: encounters API, transcription pipeline, speaker labels, live sessions, SOAP note generation, per-stage timings, metrics proxy | all services below |
| **encounter-store** (FastAPI + SQLite) | Encounters and doctor profiles. No other service reads its database | — |
| **speech-to-text** | OEP audio-analyzer (`intel/audio-analyzer:medical-scribe`): Whisper on OpenVINO GenAI; pyannote `speaker-diarization-community-1` over the whole recording with the doctor's voice profile; voice embeddings for enrolment. `services/speech-to-text/entrypoint.sh` (mounted) maps `configs/model-config.yaml` to its `AUDIO_ANALYZER__*` settings and adds the browser audio formats | — |
| **text-generation** | OpenVINO Model Server 2026.4.1 serving the model in `configs/model-config.yaml` with the OpenAI chat API; model pulled and loaded at start | — |
| **metrics-collector** | performance-tools (`intel/retail-benchmark`): CPU, GPU, NPU, memory, power | host `/sys`, `/proc` |

Compared with the Demo Studio sample, the workflow logic (pipeline, alignment, prompt) moved from
the browser to `scribe-aggregator`. The UI no longer starts, stops or configures services, and each
service is configured from the environment and ready on its own.

## Upload flow

```mermaid
sequenceDiagram
  participant UI
  participant A as scribe-aggregator
  participant S as speech-to-text
  participant E as encounter-store
  UI->>A: POST /api/encounters/{id}/audio
  A-->>UI: 202 processing
  A->>S: POST /v1/audio/transcriptions (verbose_json, diarization_mode=file, doctor speaker profile)
  A->>A: merge consecutive segments of one speaker
  A->>E: PATCH encounter (transcript, timings, status=transcribed)
  UI->>A: GET /api/encounters/{id} (poll)
```

- audio-analyzer transcribes the recording in chunks and, in parallel, diarizes the whole
  recording once (`num_speakers` from `configs/model-config.yaml`), so a speaker keeps one label
  throughout. Each segment carries its speaker.
- With an enrolled doctor, the request carries the doctor's voice embedding as a speaker profile;
  the voice that matches it (cosine similarity ≥ `speaker_match_threshold`) is **Doctor** and the
  other **Patient**. Without one, or if the doctor is not recognised, speakers are labelled
  *Speaker 1*, *Speaker 2* in speaking order.
- Enrolment (`POST /api/doctors/{id}/voice`) sends the sample to audio-analyzer's
  `/v1/audio/speaker-embedding`; only the embedding is stored.

## Live flow

- The browser captures the microphone, downsamples it to 16 kHz 16-bit mono, and streams it to `WS /api/live/{id}`.
- The aggregator:
  - relays the audio to audio-analyzer's OpenAI Realtime-style `/v1/realtime`;
  - sends each transcribed utterance back as `{"type": "utterance", "text"}`;
  - keeps the audio.
- On **Stop** (or if the browser disconnects), the recording goes through the upload flow, which adds the speaker labels.

## SOAP note

- `POST /api/encounters/{id}/note` sends the labelled transcript (`Speaker: text` lines) and the prompt `prompts.soap` in `configs/model-config.yaml` to the LLM.
- Request settings: thinking disabled, `</think>` as a stop word.
- The note streams back as server-sent events (`delta`, then `done` or `error`), and is saved with its timings once complete.

## Performance metrics

| Source | Metrics |
|---|---|
| metrics-collector (performance-tools) | CPU %, GPU %, NPU %, memory, package power, platform info; shown live on the System page |
| scribe-aggregator, per encounter | audio length; speech-to-text time (including speakers) and real-time factor (RTF); note time to first words, tokens/s, total time |

Measured on Core Ultra 7 265K (Whisper large-v3-turbo int8 on GPU, pyannote on GPU, Qwen3.5-4B int4
on GPU), 133 s consultation:

| Stage | Time |
|---|---|
| Speech to text with speakers | about 29 s (RTF 0.22); pyannote on the CPU: about 54 s |
| SOAP note | first words 3.0 s, 14.8 tokens/s, 22.8 s total |

## API

All under `/api` on the gateway; interactive docs at `/api/docs`.

| Method | Path | |
|---|---|---|
| GET | `/api/status` | Readiness of each AI service |
| GET | `/api/config` | Models and devices in use |
| GET / POST | `/api/doctors` | List / add doctors |
| DELETE | `/api/doctors/{id}` | Remove a doctor |
| POST | `/api/doctors/{id}/voice` | Enrol the voice (multipart `file`, ≥ 3 s of speech) |
| GET / POST | `/api/encounters` | List / create (`name`, `doctor_id`, `language`) |
| GET / PATCH / DELETE | `/api/encounters/{id}` | Read; edit `name`, `note`, `reviewed`; delete |
| POST | `/api/encounters/{id}/audio` | Upload a recording (multipart `file`); starts the pipeline |
| POST | `/api/encounters/{id}/note` | Generate the SOAP note (server-sent events) |
| WS | `/api/live/{id}` | Live consultation (binary PCM frames, then `{"type":"stop"}`) |
| GET | `/api/metrics` | Hardware metrics from metrics-collector |

Encounter `status`: `new` → `recording` → `processing` → `transcribed` (or `error`).

## Data and models

| Host folder | Contents |
|---|---|
| `data/encounter-store/` | `encounters.db`: encounters, transcripts, notes, doctor voice embeddings (clinical data) |
| `models/stt` | Whisper source and OpenVINO export, pyannote pipeline (audio-analyzer) |
| `models/text-generation` | The LLM (OpenVINO IR) |
| `logs/`, `metrics/` | Service logs, raw metrics-collector output |

## Design decisions

| Decision | Why |
|---|---|
| Workflow in a backend service (`scribe-aggregator`) | Any client can get a note; processing survives a closed browser; prompt and logic change without a UI rebuild |
| One gateway, internal bridge network | One place for TLS and authentication later; internal ports are not exposed |
| One image per service | Independent builds and upgrades; each pins its own dependencies |
| LLM model from `.env`, loaded at start | The service is ready on its own; no UI step loads the model |
| OVMS release archive on our base image instead of `openvino/model_server:2026.4.1-gpu` | That image's GPU driver (26.18) makes Qwen3.5-4B int4 produce garbage text on Arrow Lake; the base pins the validated 26.05 |
| audio-analyzer for speech to text and speakers | One service for both; whole-file diarization with the doctor's speaker profile labels 57 of 58 test segments correctly, against 45 with its per-chunk kiosk mode. Built from edge-ai-libraries (`feature/audio-analyzer-speaker-profiles`) until released |
