# RunPod network volume layout

Volume name: `urdu-video-models` · Size: 50 GB · Region: **EU-RO-1**
Mount point (Serverless and Pods): `/runpod-volume`

Weights live on the volume, **never** in the Docker image (T088). The image only
contains ComfyUI + Python deps; `comfyui/extra_model_paths.yaml` points ComfyUI at
the folders below.

```
/runpod-volume/
├── models/
│   ├── wan2.2-ti2v-5b/                    # ComfyUI model root for Wan 2.2
│   │   ├── diffusion_models/
│   │   │   └── wan2.2_ti2v_5B_fp16.safetensors        (~10 GB)
│   │   ├── text_encoders/
│   │   │   └── umt5_xxl_fp8_e4m3fn_scaled.safetensors (~6.7 GB)
│   │   └── vae/
│   │       └── wan2.2_vae.safetensors                 (~1.4 GB)
│   └── omnivoice-urdu-6000/               # full HF repo snapshot (OmniVoice Urdu)
└── voices/
    ├── male.wav        # reference voice, mono, ~5-15 s clean speech
    ├── male.txt        # exact transcript of male.wav (Urdu)
    ├── female.wav
    └── female.txt
```

## Notes

- Filenames under `diffusion_models/`, `text_encoders/`, `vae/` must match the names
  hard-coded in `workflows/wan22_ti2v5b.json`.
- `voices/*.txt` are an addition to the required `.wav` files: OmniVoice's
  `generate()` takes `ref_text` (transcript of the reference clip) alongside
  `ref_audio`. If a `.txt` is missing, `omnivoice/infer.py` omits `ref_text`.
- Voice ids used by the backend (`male`, `female`) map to `voices/<id>.wav`.
- `voices/*.wav` are **not** downloaded by `download_weights.sh`; upload your own
  recordings (see the script header).
- Keep the volume in EU-RO-1; Serverless endpoints must be deployed in the same
  region/data center to mount it.
