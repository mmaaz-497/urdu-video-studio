"""OmniVoice Urdu narration synthesis (research.md A5).

Usage API (from the mlwithabdullah/omnivoice-urdu-6000 model card):
    model = OmniVoice.from_pretrained(path, device_map="cuda:0")
    audio = model.generate(text=..., ref_audio=..., ref_text=...)
    sf.write("out.wav", audio[0], 24000)

NOTE: package dir is named `omnivoice` (per T086) but the pip package is also
`omnivoice`. The Dockerfile places this directory at /app/tts_omnivoice and
handler.py imports it as `tts_omnivoice.infer`, avoiding a name clash.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

SAMPLE_RATE = 24000
VOLUME_ROOT = Path(os.environ.get("VOLUME_ROOT", "/runpod-volume"))
MODEL_DIR = VOLUME_ROOT / "models" / "omnivoice-urdu-6000"
VOICES_DIR = VOLUME_ROOT / "voices"
VALID_VOICES = ("male", "female")

_model = None


@dataclass
class Narration:
    wav_path: str
    duration_seconds: float  # measured from the generated samples, not estimated


def _load_model():
    global _model
    if _model is None:
        from omnivoice import OmniVoice  # pip package, imported lazily (GPU-only dep)

        _model = OmniVoice.from_pretrained(str(MODEL_DIR), device_map="cuda:0")
    return _model


def release_model() -> None:
    """Free GPU memory so ComfyUI has headroom (call between TTS and video)."""
    global _model
    _model = None
    try:
        import gc

        import torch

        gc.collect()
        torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001 - best-effort cleanup
        pass


def synthesize(text: str, voice_id: str, out_path: str) -> Narration:
    """Single-pass Urdu narration for `text` using voices/<voice_id>.wav as the reference."""
    import numpy as np
    import soundfile as sf

    if voice_id not in VALID_VOICES:
        raise ValueError(f"Unknown voice_id {voice_id!r}")
    ref_audio = VOICES_DIR / f"{voice_id}.wav"
    if not ref_audio.exists():
        raise FileNotFoundError(f"Reference voice missing on volume: {ref_audio}")
    ref_text_file = VOICES_DIR / f"{voice_id}.txt"

    kwargs = {"text": text, "ref_audio": str(ref_audio)}
    if ref_text_file.exists():
        kwargs["ref_text"] = ref_text_file.read_text(encoding="utf-8").strip()

    audio = _load_model().generate(**kwargs)
    samples = np.asarray(audio[0]).squeeze()
    if hasattr(audio[0], "detach"):  # torch tensor
        samples = audio[0].detach().cpu().float().numpy().squeeze()
    sf.write(out_path, samples, SAMPLE_RATE)
    return Narration(wav_path=out_path, duration_seconds=len(samples) / SAMPLE_RATE)
