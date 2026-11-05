# ruff: noqa: E501  (Urdu sample strings)
#!/usr/bin/env python3
"""Measure real OmniVoice words-per-second to calibrate WORDS_PER_5S_MAX.

Run on a GPU pod with the volume attached and the worker deps installed:
    cd /app && python scripts/calibrate_words.py --voice male
    python scripts/calibrate_words.py --voice female --samples my_samples.json

--samples: JSON list of Urdu strings. Defaults to the built-in samples below
(~10-45 words; REPLACE/extend with scripts representative of real student
content - more and longer samples give a better estimate).

Output: per-sample words, seconds, words/sec, then the recommended
WORDS_PER_5S_MAX = floor(p25_wps * 5 * 1.10), i.e. using the 10% atempo
speed-up budget (FR-017). Copy that into
backend/app/services/llm_service.py.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SAMPLES = [
    "پاکستان جنوبی ایشیا کا ایک خوبصورت ملک ہے۔ یہاں پہاڑ، دریا اور صحرا سب کچھ موجود ہے۔",
    "سورج مشرق سے نکلتا ہے اور مغرب میں غروب ہوتا ہے۔ صبح کے وقت پرندے چہچہاتے ہیں اور ہر طرف تازگی پھیل جاتی ہے۔",
    "پانی زندگی کے لیے بہت ضروری ہے۔ ہمیں پانی کو ضائع نہیں کرنا چاہیے۔ صاف پانی ہر انسان کا حق ہے اور ہمیں اس کی حفاظت کرنی چاہیے۔",
    "علم حاصل کرنا ہر مسلمان مرد اور عورت پر فرض ہے۔ جو لوگ محنت سے پڑھتے ہیں وہ زندگی میں کامیاب ہوتے ہیں۔ استاد قوم کے معمار ہوتے ہیں۔",
    "ایک دفعہ کا ذکر ہے کہ ایک جنگل میں ایک شیر رہتا تھا۔ وہ بہت طاقتور تھا لیکن ایک چھوٹے سے چوہے نے اس کی جان بچائی۔ اس دن شیر نے سیکھا کہ کوئی بھی چھوٹا نہیں ہوتا۔",
]


def count_words(text: str) -> int:
    return len(text.split())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", choices=["male", "female"], default="male")
    ap.add_argument("--samples", help="JSON file: list of Urdu strings")
    ap.add_argument("--max-speedup", type=float, default=1.10)
    args = ap.parse_args()

    samples = json.loads(Path(args.samples).read_text("utf-8")) if args.samples else SAMPLES

    from tts_omnivoice.infer import synthesize  # noqa: PLC0415 (GPU-only import)

    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, text in enumerate(samples):
            n = count_words(text)
            result = synthesize(text, args.voice, str(Path(tmp) / f"s{i}.wav"))
            wps = n / result.duration_seconds
            rows.append((n, result.duration_seconds, wps))
            print(f"sample {i}: {n:3d} words  {result.duration_seconds:6.2f}s  {wps:5.2f} words/s")

    wps_all = [r[2] for r in rows]
    mean, lo = statistics.mean(wps_all), min(wps_all)
    p25 = statistics.quantiles(wps_all, n=4)[0] if len(wps_all) >= 4 else lo
    print(f"\nvoice={args.voice} samples={len(rows)}")
    print(f"words/s  mean={mean:.2f}  min={lo:.2f}  p25={p25:.2f}")
    # Conservative: use the slowest-speaking quartile so narration rarely overruns a scene.
    # A speaker faster than assumed only leaves silence; a slower one overruns the scene.
    safe = p25
    per5 = math.floor(safe * 5)
    per5_with_budget = math.floor(safe * 5 * args.max_speedup)
    print(f"words per 5s scene (no speed-up):       {per5}")
    print(f"words per 5s scene (with {args.max_speedup:.2f}x atempo):   {per5_with_budget}")
    print(
        f"\nRecommended WORDS_PER_5S_MAX = {per5_with_budget}  (current estimate in llm_service.py: 15)"
    )
    print("Run for both voices and use the smaller value.")


if __name__ == "__main__":
    main()
