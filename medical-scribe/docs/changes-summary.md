# Medical Scribe: summary of changes

Related: [containerization plan](containerization-plan.md), [OEP audio-analyzer and DL Streamer plan](oep-audio-analyzer-and-dlstreamer-plan.md).

## 1. Speech to text: OEP audio-analyzer

- Default speech-to-text backend changed from `ovms` to `oep` (OEP audio-analyzer):
  - `frontend/src/services/speech-to-text/config.ts`: `DEFAULT_STT_BACKEND = 'oep'`.
  - `frontend/src/lib/instances/service-metadata.ts`: `sttBackend.default: 'oep'`.
- Diarization still uses the existing pyannote worker.

## 2. Frontend: services run outside the app (`EXTERNAL_SERVICES`)

- New `frontend/src/lib/workers/external-services.ts`:
  - Reads env `EXTERNAL_SERVICES="<type>=<port>,..."`.
  - Accepts only ports in the instance port range (8100–8199); other entries are ignored with a warning.
- `instance-ports.ts`: an external service always gets its fixed port.
- `worker-lifecycle.ts`: the app never starts or stops an external service.
- `health/status.ts`, `health/poller.ts`: external services are marked active from their health check alone.
- `engines/multiserve/process-handler.ts`: waits for an already running multiserve instead of spawning one.
- `app-boot.ts`: external ports are left alone by the startup port cleanup.
- No database schema change.

## 3. Deployment preset (`deployment.json`)

- What it is: a Demo Studio preset file in the repo root, applied by the app every time it starts. It is the whole service setup: the services to create and start, with their model and device.
- New `deployment.json` with four services:
  - Medical Scribe Database (CPU).
  - Speech to Text: `openai/whisper-large-v3-turbo`, GPU, `oep` backend.
  - Speaker Diarization: `pyannote/speaker-diarization-community-1`, CPU.
  - Text Generation: `OpenVINO/Qwen3.5-4B-int4-ov`, AUTO, multiserve.
- Why it is needed:
  - The UI container starts with an empty database (`data/ui/db.sqlite`). Without the preset there are no service records, so the app never uses the containers on ports 8190–8193 and the Consultations page keeps waiting.
  - The multiserve container starts with no model. The app reads the text-generation model from this file and tells multiserve to load it; without it, no SOAP notes are written.
  - No manual setup: otherwise all four services must be added and configured in the UI after every fresh install.
  - The native `./start.sh` uses it too, so services start automatically there as well.
- It is applied on every start: existing services are updated to match it, and instances it does not list are removed. Model or device changes made in the UI are overwritten on the next start; change them in this file instead.

## 4. Containers

- New `docker/Dockerfile`, multi-stage:
  - `runtime`: Ubuntu 24.04, Intel GPU/NPU user-space drivers (same pins as upstream audio-analyzer), FFmpeg, `libxml2` (needed by OVMS), non-root `appuser` (uid 1000).
  - `workers`: uv, OVMS, shared venv with diarization, database and multiserve.
  - `stt`: OEP audio-analyzer in its own venv.
  - `ui`: Node, `npm ci`, `next build`.
- New `docker/docker-compose.yaml`, five services:

  | Service | Port |
  |---|---|
  | ui | 8080 |
  | speech-to-text | 8190 |
  | diarization | 8191 |
  | text-generation | 8192 |
  | medical-scribe-database | 8193 |

  - Host networking: the browser's live-mode WebSockets go straight to the speech-to-text and diarization ports.
  - Every container gets `/dev/dri`, the NPU, the `render`/`video` groups, proxy settings and a healthcheck.
  - `models/`, `data/` and `logs/` are bind-mounted and shared with the native run.
- New `docker/.env.example` (`make setup` copies it to the git-ignored `docker/.env`):
  - ports, devices and models;
  - `PAYLOAD_SECRET`;
  - `HF_TOKEN`, now marked required;
  - `APP_MODE`;
  - group ids.
- New `Makefile`: `setup`, `build`, `up`, `down`, `restart`, `logs`, `status`, `ps`.
  - `make up` stops with a clear message if `HF_TOKEN` is empty.
- New `.dockerignore`; `.gitignore` now ignores `docker/.env`.
- Build fixes:
  - Download loop fails on the first failed download.
  - Corrected the package name (`medical-scribe-database-worker`).
  - Recursive `chown` of `/opt/medical-scribe`.

## 5. UI: Medical Scribe mode (`APP_MODE=medical-scribe`)

- New `frontend/src/lib/branding.ts`: app name and description for each mode, read from env `APP_MODE` when the app runs (one image serves both modes).
- New `frontend/src/context/app-mode.tsx`: `useAppMode()`, `useBranding()`.
- `layout.tsx`: page title and description come from the mode.
- Branding: "Medical Scribe" replaces "Edge AI Demo Studio" in the sidebar, the mobile header and page titles.
- Sidebar (`app-pages.ts`, `sidebar-nav.tsx`):
  - **Scribe:** Today, Consultations.
  - **Monitor:** System.
  - Hidden: Samples, Services, Settings, and the sidebar list of individual services.
- Header: search, Ctrl+K command palette and settings button hidden.
- New **Today** page (`scribe-home.tsx`, `home-for-mode.tsx`):
  - header with "On-device · no cloud" and "AI ready" badges;
  - **Start consultation** and **Open last encounter** buttons;
  - counts: encounters today, awaiting a note, all encounters, doctor voices enrolled;
  - recent encounters with status (Note ready / Needs note / Processing / Failed);
  - read-only AI pipeline status (transcription, speaker identification, clinical note writer, encounter store).
- **Consultations** page (`sample-demo-content.tsx`):
  - Title "Consultations".
  - No back link, Services button, Logs button or service sheet.
  - New `services-waiting-panel.tsx` replaces the setup panel: read-only status while services start, no Start/Stop/Configure.
  - Doctor profiles, encounter list, transcript and SOAP note are unchanged.
- `APP_MODE=studio` (or unset) keeps the original Edge AI Demo Studio UI. The native `./start.sh` is unchanged.

## 6. Docs

- `docs/oep-audio-analyzer-and-dlstreamer-plan.md`, with its drawio design.
- `docs/containerization-plan.md`, with an "As built" section.
- This file.

## 7. Open items

- GPU usage on the System page in containers: `qmassa` is not in the UI image yet. CPU, memory and NPU readings work.
- Diarization on `xpu` inside a container.
- End-to-end sample run, and live mode in the browser.
- Encounter review screen (transcript and SOAP side by side, mark reviewed), and an Encounters table.
