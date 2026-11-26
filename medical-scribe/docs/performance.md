# Medical Scribe Performance

Measurements below were collected on an Intel Core Ultra 7 265K. The old pipeline figures are historical runs recorded before its diarization service was removed; they could not be rerun. The new-pipeline figures are fresh measurements through the Medical Scribe API using the same sample recordings. Times are workload- and host-specific, not service-level guarantees.

## Original vs Current Pipeline

The old pipeline ran transcription and diarization concurrently in separate services. Its transcript was ready when the slower of the two completed. The current pipeline performs whole-file diarization as part of audio-analyzer's transcription request, so the API reports one combined speech-to-text time rather than separate transcription and diarization durations.

| Metric | Gastritis, original | Gastritis, current | Leg pain, original | Leg pain, current |
|---|---:|---:|---:|---:|
| Audio length | 133.5 s | 133.5 s | 133.5 s | 133.5 s |
| Transcription duration | 15.57 s | Included below | 18.00 s | Included below |
| Diarization duration | 221.21 s | Included below | 207.11 s | Included below |
| **Transcript with speakers ready** | **about 221 s** | **28.54 s** | **about 207 s** | **28.50 s** |
| Combined real-time factor | 1.66 | 0.21 | 1.55 | 0.21 |
| SOAP note: first words | 3.0 s | 2.40 s | 3.41 s | 2.85 s |
| SOAP note: generation speed | 14.8 tokens/s | 17.4 tokens/s | 14.6 tokens/s | 17.3 tokens/s |
| SOAP note: total duration | 22.8 s | 12.18 s | 23.72 s | 11.85 s |
| **Approximate upload-to-note time** | **244 s** | **40.72 s** | **231 s** | **40.35 s** |

The original transcript-ready and upload-to-note times are estimates: old transcription and diarization ran in parallel, and diarization was the slower stage. Current upload-to-note time is the combined transcription/diarization duration plus note-generation duration. These figures exclude upload/network time and do not include any user review.

The headline improvement is diarization: the original CPU diarization took around 1.55–1.66 times the audio duration, while current combined transcription and GPU diarization takes about 0.21 times the audio duration. Standalone transcription was faster in the original runs (15.57–18.00 s); the current path's benefit is that speaker identification is integrated and no longer dominates the wait.

## Current Pipeline: Five Sample Recordings

Current speech-to-text timing includes both transcription and whole-file speaker diarization. SOAP timings are measured after the transcript is ready. The model was Qwen3-4B int4 on GPU. No doctor voice profile was enrolled for this benchmark, so speakers are named Speaker 1 and Speaker 2.

| Recording | Audio length | Transcript with speakers | RTF | Note first words | Note speed | Note total |
|---|---:|---:|---:|---:|---:|---:|
| Gastritis | 133.50 s | 28.54 s | 0.214 | 2.40 s | 17.4 tokens/s | 12.18 s |
| Leg pain | 133.50 s | 28.50 s | 0.214 | 2.85 s | 17.3 tokens/s | 11.85 s |
| Chest pain | 139.50 s | 29.55 s | 0.212 | 2.31 s | 17.2 tokens/s | 14.72 s |
| English/Malay | 72.81 s | 15.34 s | 0.211 | 1.64 s | 17.6 tokens/s | 10.64 s |
| Chinese flu | 169.53 s | 35.74 s | 0.211 | 2.54 s | 17.3 tokens/s | 13.20 s |

All five completed and produced two speaker labels. These runs measure latency, not transcription or clinical accuracy.

## Speaker-Label Evaluation

A separate labelled-segment evaluation found 57 of 58 segments correctly assigned with whole-file diarization and an enrolled Doctor voice profile, versus 45 of 58 with audio-analyzer's per-chunk mode. This is a small evaluation set and should not be read as a general accuracy claim. The five latency runs above did not use an enrolled doctor and were not scored for speaker-label correctness.

## Notes on Interpretation

- The original and current LLMs differ: Qwen3.5-4B int4 was used in the original runs; Qwen3-4B int4 is used now. New notes were shorter (156–213 tokens in the five current runs, versus about 297 tokens in one historical run), so compare time-to-first-word and token throughput as well as total note time.
- The original service exposed a separate diarization duration; current audio-analyzer reports a combined speech-to-text duration. Do not compare the old transcription-only duration directly with the new combined duration.
- The original diarization service and its implementation are no longer available in this app for a repeatable, controlled A/B test. The historical comparison is observational, not a simultaneous benchmark.
- Hardware, model, input, device, warm-up state and concurrent system load can change results.
