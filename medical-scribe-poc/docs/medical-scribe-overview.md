# Medical Scribe — Overview

## What it is

Medical Scribe is an AI assistant for doctors. It listens to a doctor-patient
consultation, writes down what was said, labels who said it (doctor or patient),
and drafts the clinical note in the standard **SOAP** format. Everything runs on
the local Intel PC; the conversation does not go to the cloud.

It is the first sample of the planned **Medical Terminals** category in HLS AI
Suite (Jira [ITEP-97800](https://jira.devtools.intel.com/browse/ITEP-97800)):
AI on the everyday PCs used next to the patient — carts, bedside terminals and
exam-room PCs.

## What it does (user view)

1. **Doctor profile (once):** the doctor records a short voice sample. The app
   stores a voice "fingerprint" (embedding) so it can tell the doctor apart from
   the patient later.
2. **New session:** pick the doctor and the language (English, Malay, Chinese, or
   a mix).
3. **Record** the consultation with live transcription, or **upload** an audio
   file.
4. **Process:** the app produces a transcript labelled by speaker, for example:
   - **Doctor:** "How long have you had the fever?"
   - **Patient:** "Three days, 38.5 at home."
5. **Generate SOAP note:** a language model writes the note and streams it to the
   screen.
6. **Sessions** are saved with their status (recording, processing, completed,
   error) and can be renamed, deleted or reprocessed. Interrupted sessions are
   recovered.

### SOAP note

| Section | Content |
|---|---|
| **S**ubjective | What the patient reports: symptoms, history, home readings |
| **O**bjective | What the clinician measured or examined during this visit |
| **A**ssessment | The doctor's stated impression or diagnosis |
| **P**lan | Tests, treatment, medicines, advice and follow-up the doctor gave |

The note-writing prompt (`frontend/src/samples/medical-scribe/lib/soap.ts`) sets
strict rules:
- use only what was said; anything not discussed is written as "Not discussed";
- home readings go in Subjective, never in Objective;
- numbers, units, drug names and doses are copied exactly; garbled values are
  listed under "Items to Verify";
- the transcript may be English, Malay, Chinese or mixed; the note is always in
  English.

## What is used

| Step | Service | Model (recommended) | Device |
|---|---|---|---|
| Speech to text | `speech-to-text` | `openai/whisper-large-v3-turbo` (Qwen3-ASR optional via OVMS) | GPU |
| Who said what | `diarization` | `pyannote/speaker-diarization-community-1` | Intel GPU (XPU) |
| Write the note | `text-generation` (multiserve engine) | `OpenVINO/Qwen3-8B-int8-ov` | GPU |
| Store sessions | `medical-scribe-database` | — (FastAPI + SQLite) | CPU |

Software stack:
- **Frontend:** Next.js / React (TypeScript), Payload CMS for users and settings.
- **Backend workers:** Python services managed by the frontend; OpenVINO,
  OpenVINO Model Server (OVMS) and llama.cpp (SYCL or Vulkan) for inference.
- **Tools downloaded by setup:** Node.js, FFmpeg, qmassa (GPU monitor).

Notes:
- The pyannote model is gated on Hugging Face: accept its terms and provide a
  Hugging Face token in the app.
- Models are downloaded at setup or first use; they are not part of this folder.

## How it works

```mermaid
flowchart LR
  M["Microphone or<br/>audio file"] --> STT["Speech to text<br/>Whisper large-v3-turbo"]
  M --> D["Diarization<br/>pyannote"]
  P["Doctor voice<br/>fingerprint"] --> D
  STT --> AL["Align words<br/>with speakers"]
  D --> AL
  AL --> T["Transcript<br/>Doctor / Patient"]
  T --> LLM["SOAP writer<br/>Qwen3-8B INT8 (OpenVINO)"]
  LLM --> N["SOAP note"]
  T --> DB[("medical-scribe-database<br/>SQLite")]
  N --> DB
```

1. **Record:** the browser records audio. In live mode the speech-to-text
   service transcribes as the doctor speaks, and those live results are reused
   later instead of transcribing again.
2. **Transcribe and diarize in parallel:** the audio goes to speech-to-text
   (text with word timings) and to diarization (speaker time segments).
   - With a doctor profile, diarization compares voices with the doctor's
     fingerprint and labels segments "Doctor" or "Patient".
   - Without a profile, it assumes two speakers.
3. **Align:** frontend code (`lib/alignment/`) matches each word to the speaker
   talking at that time, producing the labelled transcript.
4. **Generate the note:** the transcript and the SOAP prompt go to the
   text-generation service; the note streams back to the page.
5. **Save:** sessions, transcripts, notes and doctor profiles are stored by the
   `medical-scribe-database` service in SQLite.

## What we pulled from upstream

**Source:** `open-edge-platform/edge-developer-kit-reference-scripts`, branch
`main`, commit `7bdfd48`, folder `samples/ai/edge-ai-demo-studio`.

The sample page lives in
[`frontend/src/samples/medical-scribe`](https://github.com/open-edge-platform/edge-developer-kit-reference-scripts/tree/main/samples/ai/edge-ai-demo-studio/frontend/src/samples/medical-scribe),
but it cannot run alone: it is one sample inside **Edge AI Demo Studio** and
needs the studio shell and four backend services. We therefore used Demo
Studio's own export tool, which copies only what this sample needs:

```bash
cd samples/ai/edge-ai-demo-studio
thirdparty/node/bin/node scripts/export-bundle.mjs --samples=medical-scribe --out=<target>
```

```mermaid
flowchart LR
  subgraph DS["edge-ai-demo-studio (all samples and services)"]
    F["frontend/"]
    W["workers/"]
  end
  DS -->|"export-bundle.mjs<br/>--samples=medical-scribe"| B
  subgraph B["medical-scribe-poc (818 files, ~9 MB source)"]
    BF["frontend/: studio shell +<br/>medical-scribe page + 4 services"]
    BW["workers/: speech-to-text, diarization,<br/>medical-scribe-database, helper,<br/>engines/multiserve, common"]
    BS["setup / start scripts<br/>(Linux + Windows)"]
  end
```

| Folder | What it contains | Upstream location |
|---|---|---|
| `frontend/src/samples/medical-scribe/` | The Medical Scribe page: components, hooks, SOAP prompt, alignment | same path |
| `frontend/src/services/` | Client code for `speech-to-text`, `diarization`, `text-generation`, `medical-scribe-database` | same path (other services removed) |
| `frontend/` (rest) | Demo Studio shell: app, components, Payload CMS, settings | same path |
| `workers/services/speech-to-text/` | Speech-to-text service (Whisper; OEP and OVMS variants) | same path |
| `workers/services/diarization/` | Speaker diarization service (pyannote) | same path |
| `workers/services/medical-scribe-database/` | Session and doctor-profile store (FastAPI + SQLite) | same path |
| `workers/services/helper/` | Shared helper service used by the studio | same path |
| `workers/engines/multiserve/` | LLM serving engine for text generation (OpenVINO / llama.cpp) | same path |
| `workers/common/` | Shared worker code: audio input, model downloader, OVMS export | same path |
| `setup.sh`, `start.sh`, `setup_win.bat`, `start_win.bat`, `install_dependencies.sh` | Setup and start scripts | repo root |
| `EXPORT_MANIFEST.json` | Exported sample, services and workers | generated by the export |

Not included: the other Demo Studio samples and services, the Electron desktop
app, `docker/`, and tests.

Local additions after the export:
- `.gitignore` at the root (the export does not copy Demo Studio's root
  `.gitignore`); it excludes `logs/`, `thirdparty/`, virtual environments,
  `frontend/node_modules`, `frontend/.next`, `frontend/.env`,
  `frontend/db.sqlite` and models.
- `docs/` (this file).

## How to run

```bash
# optional system packages (needs sudo)
sudo apt install -y vulkan-tools libportaudio2

bash setup.sh --backend sycl   # Node, FFmpeg, Python envs, frontend build
bash start.sh                  # web UI
```

- The web UI port is set by `PORT` in `frontend/.env` (default 8080; copy
  `frontend/.env.example` to `frontend/.env` on a fresh clone). On our test
  machine 8080 is used by NICU Warmer, so we use `PORT=8090`.
- Backend services use ports from `INSTANCE_PORT_RANGE` (default 8100–8199).
- In the browser: create the admin user, start the four services with the
  recommended models, add the Hugging Face token for pyannote, then open
  **Samples → Medical Scribe**.

## Points to note

- **Patient data:** recordings, transcripts and notes are protected health
  information. The SQLite store has no encryption or retention settings in this
  sample; this must be defined before any real use.
- **Licenses:** confirm the licenses of all models (pyannote is gated on Hugging
  Face).
- **Not for clinical use:** reference implementation only.
- **Sync with upstream:** Demo Studio changes often; re-run the export and
  compare when updating.
