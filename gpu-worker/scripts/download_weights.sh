#!/usr/bin/env bash
# One-time, idempotent, resumable weight download onto the RunPod network volume.
#
# HOW TO RUN (cheap pod with the volume attached)
#   1. RunPod console -> Pods -> Deploy. Choose region EU-RO-1 (same as the volume).
#      Pick the cheapest CPU pod (or the cheapest GPU, e.g. RTX A4000/3070) - no GPU
#      is needed for downloading. Under "Network Volume" select `urdu-video-models`;
#      it mounts at /runpod-volume. Any template with Python 3 works (e.g. runpod/base).
#   2. Open a web terminal / SSH into the pod, then:
#        pip install -U "huggingface_hub[cli]"        # provides `hf` / `huggingface-cli`
#        export HF_TOKEN=hf_xxx                       # optional; avoids rate limits
#        bash download_weights.sh                     # copy this file to the pod first
#      Override the mount point if needed:  VOLUME_ROOT=/workspace bash download_weights.sh
#   3. Upload reference voices yourself (not downloaded here), e.g. via scp/runpodctl:
#        /runpod-volume/voices/{male,female}.wav  and  {male,female}.txt (transcripts)
#   4. Re-run any time: files already present are skipped; interrupted downloads resume.
#   5. TERMINATE the pod afterwards (the volume keeps the data; the pod keeps billing).
set -euo pipefail

VOLUME_ROOT="${VOLUME_ROOT:-/runpod-volume}"
WAN_DIR="$VOLUME_ROOT/models/wan2.2-ti2v-5b"
OMNI_DIR="$VOLUME_ROOT/models/omnivoice-urdu-6000"
VOICES_DIR="$VOLUME_ROOT/voices"

if [ ! -d "$VOLUME_ROOT" ]; then
  echo "ERROR: $VOLUME_ROOT not found. Is the network volume attached to this pod?" >&2
  exit 1
fi

if command -v hf >/dev/null 2>&1; then
  HF=hf
elif command -v huggingface-cli >/dev/null 2>&1; then
  HF=huggingface-cli
else
  echo "ERROR: install the HF CLI first: pip install -U 'huggingface_hub[cli]'" >&2
  exit 1
fi

mkdir -p "$WAN_DIR/diffusion_models" "$WAN_DIR/text_encoders" "$WAN_DIR/vae" "$OMNI_DIR" "$VOICES_DIR"

human() { du -h "$1" 2>/dev/null | cut -f1; }

# fetch_file <repo> <path-in-repo> <dest-dir> <final-filename>
# `download` resumes partial files via the HF cache's .incomplete files.
fetch_file() {
  local repo="$1" src="$2" dest_dir="$3" name="$4"
  local dest="$dest_dir/$name"
  if [ -s "$dest" ]; then
    echo "SKIP  $name already present ($(human "$dest"))"
    return 0
  fi
  echo "GET   $repo :: $src"
  local tmp="$dest_dir/.hf-tmp"
  rm -rf "$tmp"
  # Keep the HF cache on the volume so partial downloads survive a pod restart.
  HF_HOME="$VOLUME_ROOT/.hf-cache" $HF download "$repo" "$src" --local-dir "$tmp"
  mv "$tmp/$src" "$dest"
  rm -rf "$tmp"
  echo "DONE  $name ($(human "$dest"))"
}

fetch_file Comfy-Org/Wan_2.2_ComfyUI_Repackaged \
  split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors \
  "$WAN_DIR/diffusion_models" wan2.2_ti2v_5B_fp16.safetensors

fetch_file Comfy-Org/Wan_2.1_ComfyUI_repackaged \
  split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors \
  "$WAN_DIR/text_encoders" umt5_xxl_fp8_e4m3fn_scaled.safetensors

fetch_file Comfy-Org/Wan_2.2_ComfyUI_Repackaged \
  split_files/vae/wan2.2_vae.safetensors \
  "$WAN_DIR/vae" wan2.2_vae.safetensors

# OmniVoice: full repo. `download --local-dir` skips complete files and resumes partial ones.
if [ -f "$OMNI_DIR/.download-complete" ]; then
  echo "SKIP  omnivoice-urdu-6000 already complete ($(human "$OMNI_DIR"))"
else
  echo "GET   mlwithabdullah/omnivoice-urdu-6000 (full repo)"
  HF_HOME="$VOLUME_ROOT/.hf-cache" $HF download mlwithabdullah/omnivoice-urdu-6000 --local-dir "$OMNI_DIR"
  touch "$OMNI_DIR/.download-complete"
  echo "DONE  omnivoice-urdu-6000 ($(human "$OMNI_DIR"))"
fi

echo
echo "=== Volume contents ==="
du -h --max-depth=3 "$VOLUME_ROOT/models" | sort -k2
echo
for v in male female; do
  [ -f "$VOICES_DIR/$v.wav" ] && echo "OK    voices/$v.wav" || echo "TODO  upload $VOICES_DIR/$v.wav (+ $v.txt transcript)"
done
df -h "$VOLUME_ROOT" | tail -1
