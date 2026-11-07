"""Mock video provider used when VIDEO_PROVIDER=mock (research.md A8).

Packaged as `mock_provider/` (rather than a flat `mock_provider.py`) so the
bundled fixtures can live alongside it at `mock_provider/assets/`.
"""

from pathlib import Path

ASSETS_DIR = Path(__file__).parent / "assets"
CLIPS_DIR = ASSETS_DIR / "clips"
NARRATION_DIR = ASSETS_DIR / "narration"
VOICES_DIR = ASSETS_DIR / "voices"

_ASPECT_RATIO_DIRS = {"16:9": "16x9", "9:16": "9x16"}


def pick_assets(aspect_ratio: str, scene_count: int, voice_id: str) -> dict:
    """Returns bundled {"clips": [...], "narrations": [...]} file paths for one
    (aspect_ratio, scene_count, voice_id) combination: one clip and one narration file per
    scene (the 5 s sample is reused for every scene, like the real per-scene TTS output)."""
    ar_dir = _ASPECT_RATIO_DIRS[aspect_ratio]
    clips = [str(CLIPS_DIR / ar_dir / f"scene{i}.mp4") for i in range(1, scene_count + 1)]
    for clip in clips:
        if not Path(clip).exists():
            raise FileNotFoundError(f"Missing mock clip: {clip}")

    narration = NARRATION_DIR / f"{voice_id}_1.mp3"
    if not narration.exists():
        raise FileNotFoundError(f"Missing mock narration: {narration}")

    return {"clips": clips, "narrations": [str(narration)] * scene_count}
