#!/usr/bin/env python3
"""Generate the two preset narrator voices with OmniVoice *Voice Design* (no real person
is cloned): a male and a female Urdu reference clip, saved to the network volume.

Run on a GPU pod with the volume attached and `pip install omnivoice soundfile` done
(see scripts/download_weights.sh for the pod setup; the Urdu fine-tune must already be on
the volume). From gpu-worker/:

    python scripts/make_voices.py                       # 3 candidates per gender
    # listen to /runpod-volume/voices/{male,female}_{1,2,3}.wav, then choose:
    python scripts/make_voices.py --pick male=2 female=1

What it does
  1. Tries Voice Design (generate(text=..., instruct=...)) on the Urdu fine-tune first.
     If that raises, or yields unusable audio, it falls back to the base k2-fsa/OmniVoice
     (downloaded into $HF_HOME, default /runpod-volume/.hf-cache, so it persists).
     Force a model with --design-model {finetune,base}. NOTE: a fine-tune could silently
     ignore `instruct` without erroring - if male/female candidates sound alike, use
     --design-model base.
  2. Saves candidates male_1..3.wav / female_1..3.wav (+ matching .txt with the exact
     spoken sentence) and prints the instruct prompt + seed used for each.
  3. Verifies every candidate works as a reference clip for the Urdu fine-tune: clones it
     on a second Urdu sentence and checks the output is non-silent and plausibly long.
     Verification clips are saved under voices/_verify/ for listening.
  4. Writes male.wav/.txt and female.wav/.txt: from --pick if given, otherwise candidate 1
     (only when the file doesn't exist yet, so a chosen voice is never overwritten;
     pass --force to overwrite).

Instruct prompts: OmniVoice only understands a fixed tag vocabulary (docs/voice-design.md
in k2-fsa/OmniVoice): gender (male|female), age (child|teenager|young adult|middle-aged|
elderly), pitch (very low|low|moderate|high|very high pitch), style (whisper). Accents
apply only to English and dialects only to Chinese. Free-form words such as "warm",
"teacher-like" or "steady pace" are NOT part of the vocabulary, so the candidates below
vary age/pitch instead. Language is inferred from the Urdu text.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

SAMPLE_RATE = 24000

# 10 words, neutral, clear: "Today the weather is very pleasant and the sky is quite clear."
REFERENCE_SENTENCE = "آج موسم بہت خوشگوار ہے اور آسمان بالکل صاف ہے۔"
# Different text, used only to check the clip works as a cloning reference.
VERIFY_SENTENCE = "ہم سب مل کر روز نئی چیزیں سیکھتے ہیں۔"

# Intent -> valid tags. male: mid-30s teacher-like; female: late-20s friendly narrator.
CANDIDATES: dict[str, list[str]] = {
    "male": [
        "male, middle-aged, moderate pitch",
        "male, young adult, low pitch",
        "male, young adult, moderate pitch",
    ],
    "female": [
        "female, young adult, moderate pitch",
        "female, young adult, high pitch",
        "female, middle-aged, moderate pitch",
    ],
}

BASE_MODEL = "k2-fsa/OmniVoice"
FINETUNE_REPO = "mlwithabdullah/omnivoice-urdu-6000"


def _to_numpy(wave):
    import numpy as np

    if hasattr(wave, "detach"):
        wave = wave.detach().cpu().float().numpy()
    return np.asarray(wave, dtype="float32").squeeze()


def _usable(samples, min_s: float = 1.0, max_s: float = 30.0) -> bool:
    import numpy as np

    if samples.ndim != 1 or not np.isfinite(samples).all():
        return False
    dur = len(samples) / SAMPLE_RATE
    rms = float(np.sqrt(np.mean(np.square(samples)))) if len(samples) else 0.0
    return min_s <= dur <= max_s and rms > 0.005


def _load(model_id: str):
    from omnivoice import OmniVoice

    return OmniVoice.from_pretrained(model_id, device_map="cuda:0")


def _release() -> None:
    import gc

    gc.collect()
    try:
        import torch

        torch.cuda.empty_cache()
    except Exception:  # noqa: BLE001
        pass


def _seed(n: int) -> None:
    try:
        import torch

        torch.manual_seed(n)
        torch.cuda.manual_seed_all(n)
    except Exception:  # noqa: BLE001
        pass


def _design(model, instruct: str, seed: int):
    _seed(seed)
    audio = model.generate(text=REFERENCE_SENTENCE, instruct=instruct)
    return _to_numpy(audio[0])


def design_all(model, label: str) -> dict | None:
    """Generate every candidate with `model`. Returns {(gender, n): (samples, instruct, seed)}
    or None if voice design failed / produced unusable audio on this model."""
    out = {}
    for g_idx, (gender, instructs) in enumerate(CANDIDATES.items()):
        for n, instruct in enumerate(instructs, start=1):
            seed = 1000 * (g_idx + 1) + n
            try:
                samples = _design(model, instruct, seed)
            except Exception as exc:  # noqa: BLE001 - e.g. unexpected kwarg / unsupported mode
                print(f"[{label}] voice design unavailable ({type(exc).__name__}: {exc})")
                return None
            if not _usable(samples):
                print(f"[{label}] unusable audio for {gender}_{n} ({instruct!r})")
                return None
            out[(gender, n)] = (samples, instruct, seed)
    return out


def verify_as_reference(finetune, ref_wav: Path, ref_txt: str, out_wav: Path) -> bool:
    import soundfile as sf

    try:
        audio = finetune.generate(text=VERIFY_SENTENCE, ref_audio=str(ref_wav), ref_text=ref_txt)
        samples = _to_numpy(audio[0])
    except Exception as exc:  # noqa: BLE001
        print(f"    verify error: {type(exc).__name__}: {exc}")
        return False
    ok = _usable(samples, min_s=0.8)
    if ok:
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(out_wav), samples, SAMPLE_RATE)
    return ok


def _copy_pick(voices: Path, gender: str, n: int) -> None:
    for ext in ("wav", "txt"):
        shutil.copyfile(voices / f"{gender}_{n}.{ext}", voices / f"{gender}.{ext}")
    print(f"  {gender}.wav <- {gender}_{n}.wav   ({CANDIDATES[gender][n - 1]})")


def _parse_picks(items: list[str]) -> dict[str, int]:
    picks = {}
    for item in items:
        gender, _, num = item.partition("=")
        if gender not in CANDIDATES or num not in {"1", "2", "3"}:
            sys.exit(f"Bad --pick {item!r}; use e.g. male=2 female=1")
        picks[gender] = int(num)
    return picks


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--volume", default=os.environ.get("VOLUME_ROOT", "/runpod-volume"))
    ap.add_argument("--design-model", choices=["auto", "finetune", "base"], default="auto")
    ap.add_argument("--pick", nargs="+", default=[], metavar="GENDER=N")
    ap.add_argument("--force", action="store_true", help="overwrite existing male/female.wav")
    args = ap.parse_args()

    volume = Path(args.volume)
    voices = volume / "voices"
    voices.mkdir(parents=True, exist_ok=True)
    picks = _parse_picks(args.pick)

    if picks and not any((voices / f"{g}_{n}.wav").exists() for g, n in picks.items()):
        sys.exit("No candidates found; run without --pick first.")
    if picks:
        for gender, n in picks.items():
            _copy_pick(voices, gender, n)
        print("Done. (Candidates were not regenerated.)")
        return

    os.environ.setdefault("HF_HOME", str(volume / ".hf-cache"))
    finetune_path = volume / "models" / "omnivoice-urdu-6000"
    finetune_id = str(finetune_path) if finetune_path.exists() else FINETUNE_REPO

    print(f"Reference sentence ({len(REFERENCE_SENTENCE.split())} words): {REFERENCE_SENTENCE}")
    finetune = _load(finetune_id)

    designed, used = None, None
    if args.design_model in ("auto", "finetune"):
        print("Trying voice design on the Urdu fine-tune ...")
        designed = design_all(finetune, "finetune")
        used = "finetune" if designed else None
    if designed is None and args.design_model in ("auto", "base"):
        print(f"Falling back to the base model {BASE_MODEL} for voice design ...")
        base = _load(BASE_MODEL)
        designed = design_all(base, "base")
        used = "base" if designed else None
        del base
        _release()
    if designed is None:
        sys.exit("Voice design failed on every model tried; see messages above.")
    print(f"\nVoice design model used: {used}\n")

    import soundfile as sf

    failures = 0
    for (gender, n), (samples, instruct, seed) in sorted(designed.items()):
        wav = voices / f"{gender}_{n}.wav"
        sf.write(str(wav), samples, SAMPLE_RATE)
        (voices / f"{gender}_{n}.txt").write_text(REFERENCE_SENTENCE + "\n", encoding="utf-8")
        ok = verify_as_reference(
            finetune, wav, REFERENCE_SENTENCE, voices / "_verify" / f"{gender}_{n}.wav"
        )
        failures += not ok
        print(
            f"{gender}_{n}: {len(samples) / SAMPLE_RATE:5.2f}s  seed={seed}  "
            f"instruct={instruct!r}  fine-tune reference check: {'OK' if ok else 'FAILED'}"
        )

    for gender in CANDIDATES:
        target = voices / f"{gender}.wav"
        if args.force or not target.exists():
            _copy_pick(voices, gender, 1)
        else:
            print(f"  {gender}.wav already exists - kept (use --pick or --force to replace)")

    print(
        f"\nListen to {voices}/ (candidates) and {voices}/_verify/ (cloned-from-candidate check)."
    )
    print("Choose with:  python scripts/make_voices.py --pick male=<1-3> female=<1-3>")
    if failures:
        print(
            f"WARNING: {failures} candidate(s) failed the fine-tune reference check - avoid them."
        )


if __name__ == "__main__":
    main()
