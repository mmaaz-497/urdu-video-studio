#!/usr/bin/env bash
# Builds backend/app/services/mock_provider/assets/ from local source clips, with
# ffmpeg (no network downloads). See assets/README.md for what each file is for.
#
# Usage: backend/scripts/build_mock_assets.sh [SOURCE_DIR]
#   SOURCE_DIR defaults to <repo-root>/sample-media/ and must contain
#   1.mp4, 2.mp4, 3.mp4 (short silent video clips) and urdu_voice.wav
#   (a single narration sample used as the base for all mock voice placeholders).
#
# If SOURCE_DIR (or the files in it) is absent, placeholder clips/tones are
# synthesized instead via ffmpeg's built-in test-pattern/sine sources — no
# downloads either way.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SOURCE_DIR="${1:-$REPO_ROOT/sample-media}"
ASSETS_DIR="$SCRIPT_DIR/../app/services/mock_provider/assets"

CLIPS_16x9="$ASSETS_DIR/clips/16x9"
CLIPS_9x16="$ASSETS_DIR/clips/9x16"
NARRATION_DIR="$ASSETS_DIR/narration"
VOICES_DIR="$ASSETS_DIR/voices"

mkdir -p "$CLIPS_16x9" "$CLIPS_9x16" "$NARRATION_DIR" "$VOICES_DIR"

CRF=30
PRESET=veryfast

have_source_clips=true
for n in 1 2 3; do
  [[ -f "$SOURCE_DIR/$n.mp4" ]] || have_source_clips=false
done
have_source_voice=true
[[ -f "$SOURCE_DIR/urdu_voice.wav" ]] || have_source_voice=false

echo "== Building scene clips =="
for n in 1 2 3; do
  if $have_source_clips; then
    src="$SOURCE_DIR/$n.mp4"
    echo "16x9 scene$n <- $src"
    ffmpeg -y -i "$src" -t 5 \
      -vf "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=24,setsar=1" \
      -c:v libx264 -preset "$PRESET" -crf "$CRF" -pix_fmt yuv420p -an -movflags +faststart \
      "$CLIPS_16x9/scene$n.mp4" -loglevel error

    echo "9x16 scene$n <- $src"
    ffmpeg -y -i "$src" -t 5 \
      -vf "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,fps=24,setsar=1" \
      -c:v libx264 -preset "$PRESET" -crf "$CRF" -pix_fmt yuv420p -an -movflags +faststart \
      "$CLIPS_9x16/scene$n.mp4" -loglevel error
  else
    hue=$((n * 60))
    echo "16x9 scene$n <- synthesized (no sample-media/)"
    ffmpeg -y -f lavfi -i "color=c=hsv(${hue},200,180):s=1280x720:d=5:r=24" \
      -c:v libx264 -preset "$PRESET" -crf "$CRF" -pix_fmt yuv420p -movflags +faststart \
      "$CLIPS_16x9/scene$n.mp4" -loglevel error

    echo "9x16 scene$n <- synthesized"
    ffmpeg -y -f lavfi -i "color=c=hsv(${hue},200,180):s=720x1280:d=5:r=24" \
      -c:v libx264 -preset "$PRESET" -crf "$CRF" -pix_fmt yuv420p -movflags +faststart \
      "$CLIPS_9x16/scene$n.mp4" -loglevel error
  fi
done

echo "== Building narration placeholders =="
# One file per (voice_id, scene_count) so each sits comfortably under its
# video's duration without needing the atempo speedup path in mock mode.
declare -A DURATIONS=( [1]=4.5 [2]=9.5 [3]=14.5 )

for scene_count in 1 2 3; do
  dur="${DURATIONS[$scene_count]}"
  if $have_source_voice; then
    src="$SOURCE_DIR/urdu_voice.wav"
    echo "male_$scene_count.mp3 (${dur}s) <- $src"
    ffmpeg -y -stream_loop -1 -i "$src" -t "$dur" -c:a libmp3lame -b:a 96k \
      "$NARRATION_DIR/male_$scene_count.mp3" -loglevel error

    echo "female_$scene_count.mp3 (${dur}s) <- $src, pitched up"
    ffmpeg -y -stream_loop -1 -i "$src" -t "$dur" \
      -af "asetrate=24000*1.18,aresample=24000,atempo=1/1.18" \
      -c:a libmp3lame -b:a 96k \
      "$NARRATION_DIR/female_$scene_count.mp3" -loglevel error
  else
    echo "male_$scene_count.mp3 (${dur}s) <- synthesized tone"
    ffmpeg -y -f lavfi -i "sine=frequency=220:duration=$dur" \
      -c:a libmp3lame -b:a 96k "$NARRATION_DIR/male_$scene_count.mp3" -loglevel error

    echo "female_$scene_count.mp3 (${dur}s) <- synthesized tone"
    ffmpeg -y -f lavfi -i "sine=frequency=330:duration=$dur" \
      -c:a libmp3lame -b:a 96k "$NARRATION_DIR/female_$scene_count.mp3" -loglevel error
  fi
done

echo "== Building voice preview samples =="
if $have_source_voice; then
  src="$SOURCE_DIR/urdu_voice.wav"
  ffmpeg -y -i "$src" -t 4 -c:a libmp3lame -b:a 96k "$VOICES_DIR/male_preview.mp3" -loglevel error
  ffmpeg -y -i "$src" -t 4 -af "asetrate=24000*1.18,aresample=24000,atempo=1/1.18" \
    -c:a libmp3lame -b:a 96k "$VOICES_DIR/female_preview.mp3" -loglevel error
else
  ffmpeg -y -f lavfi -i "sine=frequency=220:duration=4" -c:a libmp3lame -b:a 96k \
    "$VOICES_DIR/male_preview.mp3" -loglevel error
  ffmpeg -y -f lavfi -i "sine=frequency=330:duration=4" -c:a libmp3lame -b:a 96k \
    "$VOICES_DIR/female_preview.mp3" -loglevel error
fi

echo "== Done. Asset sizes: =="
find "$ASSETS_DIR" -type f \( -name "*.mp4" -o -name "*.mp3" \) -exec du -h {} \;
