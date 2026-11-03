# Mock provider assets

Bundled, committed fixtures used when `VIDEO_PROVIDER=mock` (research.md A8).
Built by `backend/scripts/build_mock_assets.sh` — re-run it any time to
regenerate everything from scratch (idempotent, `-y` overwrites).

## Provenance

Built with plain `ffmpeg` from a local, non-public source directory
(`sample-media/` at the repo root — three short silent AI-generated video
clips `1.mp4`/`2.mp4`/`3.mp4`, and one narration sample `urdu_voice.wav`).
That source directory is **not** committed (`.gitignore`'d) — only the
small, derived files below are. If `sample-media/` is absent, the build
script falls back to synthesizing flat-color clips and sine-tone audio with
ffmpeg's `lavfi` sources instead (no downloads either way).

## Layout

```
clips/16x9/scene{1,2,3}.mp4   1280x720, 24fps, 5s, silent, h264/yuv420p
clips/9x16/scene{1,2,3}.mp4   720x1280, 24fps, 5s, silent, h264/yuv420p
narration/{voice}_{n}.mp3     placeholder narration, voice in {male,female},
                               n = scene count (1/2/3) -> ~4.5s/9.5s/14.5s,
                               each comfortably under its video's duration
                               (5s/10s/15s) so the mock pipeline exercises the
                               normal path without needing the atempo
                               speedup fallback (that path is covered by
                               test_video_job_state_machine.py instead)
voices/{voice}_preview.mp3    ~4s preview clip served by GET /voices
```

`mock_provider.pick_assets(aspect_ratio, scene_count, voice_id)` selects the
first `scene_count` clips from `clips/{16x9,9x16}/` and the matching
`narration/{voice_id}_{scene_count}.mp3` file.

The `female` voice is the same source narration pitch-shifted up
(`asetrate` + `atempo` to preserve tempo) purely to make the two mock voices
audibly distinguishable — it is **not** a real distinct voice. Real,
distinct male/female Urdu narration arrives with the GPU phase (OmniVoice,
see `gpu-worker/`).
