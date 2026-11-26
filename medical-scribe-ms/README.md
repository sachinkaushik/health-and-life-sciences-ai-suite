# Medical Scribe

Record or upload a doctor–patient consultation and get a speaker-labelled transcript and a draft
SOAP note (Subjective, Objective, Assessment, Plan). All AI runs on the device, on Intel® Core™
Ultra CPU, GPU and NPU: no audio or text leaves the machine.

Part of the Health and Life Sciences AI Suite. It started as an Edge AI Demo Studio sample
(`../medical-scribe`) and is now a standalone suite app built from independent services.

## Architecture

![Medical Scribe high-level architecture](docs/user-guide/_assets/architecture.png)

Source: [architecture.svg](docs/user-guide/_assets/architecture.svg) (edit it, then re-render the PNG). The same as text:

```mermaid
flowchart LR
  B["Browser"] -->|":8080"| GW["gateway<br/>nginx"]
  GW -->|"/"| UI["ui<br/>Next.js (presentation)"]
  GW -->|"/api, /api/live (WS)"| AGG["scribe-aggregator<br/>Medical Scribe API"]
  AGG --> STT["speech-to-text<br/>OEP audio-analyzer · Whisper + speakers"]
  AGG --> LLM["text-generation<br/>OpenVINO Model Server"]
  AGG --> ES["encounter-store<br/>SQLite"]
  AGG -.->|":9000"| MC["metrics-collector<br/>performance-tools"]
```

| Service | Image | What it does |
|---|---|---|
| gateway | `intel/hl-ai-medical-scribe-gateway` | The only published port. UI at `/`, API at `/api` |
| ui | `intel/hl-ai-medical-scribe-ui` | Today, Consultations and System pages. Calls only `/api` |
| scribe-aggregator | `intel/hl-ai-medical-scribe-aggregator` | Encounters, doctors, the transcription pipeline, live sessions, SOAP note streaming, metrics |
| encounter-store | `intel/hl-ai-medical-scribe-encounter-store` | Encounters (transcript, note, timings) and doctor profiles (voice embedding) |
| speech-to-text | `intel/audio-analyzer:medical-scribe` (OEP, built from edge-ai-libraries, see below) | Whisper on OpenVINO, batch and live (`/v1/realtime`); pyannote speaker diarization over the whole recording, the enrolled doctor recognised by voice; doctor voice embeddings |
| text-generation | `intel/hl-ai-medical-scribe-text-generation` | OpenVINO Model Server writing the SOAP note; the model is set in `configs/model-config.yaml` and loaded at start |
| metrics-collector | `intel/retail-benchmark` | performance-tools: CPU, GPU, NPU, memory and power on `:9000` |

How it works in detail: [docs/user-guide/how-it-works.md](docs/user-guide/how-it-works.md).

## Requirements

- Ubuntu 24.04 on Intel® Core™ Ultra (validated on Arrow Lake, Core Ultra 7 265K), with the Intel GPU kernel driver; the NPU driver if you use the NPU.
- Docker with Compose v2.
- A Hugging Face token that has accepted the terms of
  [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1).
- About 25 GB of disk for images and 6 GB for models.

## Quick start

```bash
make setup                 # creates .env and the host folders
# edit .env: HF_TOKEN=hf_...
make build                 # base image + 5 service images
make up                    # starts everything and waits until healthy
```

Speech to text uses audio-analyzer with whole-file diarization and speaker profiles, which is not
published yet. Build it once from
[edge-ai-libraries](https://github.com/open-edge-platform/edge-ai-libraries) (branch
`feature/audio-analyzer-speaker-profiles`):

```bash
cd edge-ai-libraries/microservices/audio-analyzer
RELEASE_TAG=medical-scribe docker compose build audio-analyzer   # intel/audio-analyzer:medical-scribe
```

Open <http://127.0.0.1:8080>.

The first start downloads and converts the models (Whisper, pyannote, Qwen3.5-4B), which takes
several minutes. If the Demo Studio version already downloaded them, reuse them:

```bash
make import-models FROM=../medical-scribe/models
```

| Command | |
|---|---|
| `make status` | Container state and health |
| `make logs SERVICE=scribe-aggregator` | Follow one service's log |
| `make down` | Stop (models and data stay) |
| `make help` | All targets |

## Using it

1. **Doctors** (Consultations page): add a doctor and enrol their voice (10 s). Their speech is then labelled *Doctor*, the other voice *Patient*.
2. **New encounter**: name, doctor, language (or auto-detect).
3. **Record** (live transcript while you speak) or **Upload** a recording. The transcript is labelled by speaker when processing ends.
4. **Generate note**: the SOAP note streams in. Edit it, copy it, mark it reviewed.
5. **System performance** (right-hand panel on every page, as in the patient-monitoring app):
   platform configuration, AI pipeline status, live CPU / GPU / NPU / memory / power charts, and the
   last encounter's AI timings. Collapse it with the arrow; **Details** opens the per-encounter timings table.

## Configuration

### Models and devices (`configs/model-config.yaml`)

Edit [configs/model-config.yaml](configs/model-config.yaml), then `make restart`. A new model is
downloaded (and converted where needed) on first start.

| Section | Keys (default) | |
|---|---|---|
| `speech-to-text` | `model` (`openai/whisper-large-v3-turbo`), `device` (`GPU`), `precision` (`int8`) | Device: `CPU`, `GPU`, `NPU` |
| `diarization` | `model` (`pyannote/speaker-diarization-community-1`), `device` (`GPU`), `num_speakers` (`2`), `speaker_match_threshold` (`0.5`) | Runs inside speech-to-text. Device: `CPU`, `GPU`, `NPU` |
| `text-generation` | `model` (`OpenVINO/Qwen3.5-4B-int4-ov`), `device` (`GPU`), `cache_size` (`0`) | Any Hugging Face OpenVINO LLM repository. Device: `CPU`, `GPU`, `NPU`, `AUTO` |
| `text-generation.generation` | `temperature` (`0.7`), `top_p` (`0.9`), `repetition_penalty` (`1.1`), `max_tokens` (`2048`) | Note generation |

The SOAP prompt is `prompts.soap` in the same file. It is read for every note, so prompt edits apply without a restart.

### Deployment (`.env`)

| Variable | Default | |
|---|---|---|
| `HF_TOKEN` | — | Required (speaker diarization) |
| `BIND_ADDRESS` / `UI_PORT` | `127.0.0.1` / `8080` | Where the UI is published |
| `TAG`, `REGISTRY` | `latest`, `intel/` | Image names |
| `AUDIO_ANALYZER_TAG` | `medical-scribe` | `intel/audio-analyzer` tag (speech to text and speakers) |

## API

The UI is a client of the same API that other systems (an EHR integration, batch jobs) can use.
Interactive docs: <http://127.0.0.1:8080/api/docs>. Details in
[docs/user-guide/how-it-works.md](docs/user-guide/how-it-works.md#api).

```bash
curl -X POST localhost:8080/api/encounters -H 'Content-Type: application/json' -d '{"name":"Visit 1","language":"en"}'
curl -X POST localhost:8080/api/encounters/<id>/audio -F file=@visit.wav     # starts the pipeline
curl localhost:8080/api/encounters/<id>                                       # poll: status, transcript
curl -N -X POST localhost:8080/api/encounters/<id>/note                       # SOAP note (server-sent events)
```

## Security

- The app has **no login**. It is published on `127.0.0.1` only. Before exposing it on a network,
  put a TLS reverse proxy with authentication in front of the gateway.
- Only the gateway publishes a port; every other service is on the internal `medical-scribe-ms` network.
- Services run as non-root users. `metrics-collector` runs privileged with the host PID namespace
  because it reads hardware counters (as in the other suite apps).
- Encounters, transcripts, notes and voice embeddings are clinical data. They are stored in
  `data/encounter-store/encounters.db`; protect and back up that folder accordingly.

## Known limitations

- Speakers are found in one pass over the whole recording (about 0.2× the audio length with `device: GPU` on a Core Ultra 7 265K, 0.4× on the CPU), in parallel with transcription. Voice profiles enrolled before this version came from the previous diarization service; if the doctor is not recognised, enrol the voice again.
- The live view shows the transcript only. Speaker labels appear when the recording has been processed.
- The GPU user-space driver in the base image is pinned to 26.05.37020.3, the version validated on the host. 26.18 (used by `openvino/model_server:2026.4.1-gpu`) makes Qwen3.5-4B int4 produce garbage text on Arrow Lake; audio-analyzer ships 26.18 and its Whisper and pyannote output is correct with it.
