# Get started

1. **Prepare the host** (Ubuntu 24.04, Intel Core Ultra):
   - the Intel GPU kernel driver (and the NPU driver for the NPU);
   - Docker with Compose v2;
   - your user in the `docker`, `render` and `video` groups.
2. **Hugging Face token:** accept the terms of
   [pyannote/speaker-diarization-community-1](https://huggingface.co/pyannote/speaker-diarization-community-1)
   and create a read token.
3. **Configure:**

   ```bash
   make setup          # creates .env, finds the render/video groups and the NPU
   ```

   Set `HF_TOKEN=hf_...` in `.env`. Behind a proxy, export `http_proxy` / `https_proxy` before
   building and starting. Models and devices (CPU / GPU / NPU) are in
   `configs/model-config.yaml`; after a change, run `make restart`.
4. **Download the models and start:**

   ```bash
   make download-models     # Whisper, pyannote, LLM from configs/model-config.yaml
   make up                  # published images
   make up REGISTRY=false   # or build the app images from source
   ```

   `make download-models` uses the OEP model-download service; without it, each service downloads its
   model on first start.
5. Open <http://127.0.0.1:8080>:
   1. add a doctor and enrol their voice;
   2. create an encounter;
   3. record or upload;
   4. generate the note.

## Troubleshooting

| Symptom | Check |
|---|---|
| `make up` stops with "HF_TOKEN is empty" | Set it in `.env` |
| A service stays unhealthy | `make status`, then `make logs SERVICE=<name>` |
| "Waiting for: …" on the Consultations page | That service is still starting (first start exports or downloads its model) |
| The note is garbled | The model may not work with the GPU driver in the OVMS image: use the default `OpenVINO/Qwen3-4B-int4-ov`, or try another `OVMS_TAG` in `.env` |
| System page: "metrics collector is not reachable" | `make logs SERVICE=metrics-collector`; it needs privileged mode and the host's `/sys` |
| Build fails with `curl: (60)` behind a corporate proxy | The proxy intercepted a download; run `make build` again |
