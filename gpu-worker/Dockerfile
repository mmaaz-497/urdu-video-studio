# BUILD CONTEXT MUST BE THE REPO ROOT (RunPod's GitHub builder only lets you set the
# Dockerfile path), so every COPY source below is prefixed with gpu-worker/.
# Local equivalent: docker build -f gpu-worker/Dockerfile -t urdu-gpu-worker .
# GPU worker image: ComfyUI + Python deps. Model weights are NOT baked in; they are
# read from the RunPod network volume mounted at /runpod-volume (see volume/LAYOUT.md).
#
# PINNED VERSIONS (researched 2026-11-05; see gpu-worker/volume/LAYOUT.md "Image versions"):
#  - ComfyUI v0.44.0. Its README says torch 2.7 is the bare minimum (comfy_kitchen registers
#    custom ops with `list[int]` args, which torch 2.5.1's infer_schema rejects -> the
#    startup crash) and recommends a recent torch + cu130 wheels. v0.44.0 contains the
#    nodes used by workflows/wan22_ti2v5b.json: Wan22ImageToVideoLatent
#    (comfy_extras/nodes_wan.py), CreateVideo and SaveVideo (comfy_extras/nodes_video.py).
#  - PyTorch 2.14.1 + CUDA 13.0 + cuDNN 9 (runtime variant, ~3.3 GB; no nvcc/devel tools).
#    CUDA 13.0 is deliberately NOT 13.2: a container built for 13.0 runs on any host
#    driver >= 13.0, including the RunPod hosts reporting CUDA 13.2, and matches the
#    cu130 wheels ComfyUI documents. 12.x images are not used: ComfyUI says cu130+ is
#    required on NVIDIA 20-series and newer.
#  - Disk: the container disk is ~5 GB free, so no devel image, no extra torch copy
#    (constraints.txt stops pip from replacing torch), --no-cache-dir everywhere.
FROM pytorch/pytorch:2.14.1-cuda13.0-cudnn9-runtime

ENV PYTHONUNBUFFERED=1 DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# ComfyUI pinned to a release tag (never master). Override with --build-arg COMFYUI_REF=...
# A shallow clone of just that tag keeps the layer small. torch is held at the base
# image's version via constraints.txt so ComfyUI/OmniVoice requirements can't swap it.
ARG COMFYUI_REF=v0.44.0
COPY gpu-worker/constraints.txt /tmp/constraints.txt
RUN git clone --depth 1 --branch ${COMFYUI_REF} https://github.com/comfyanonymous/ComfyUI.git /comfyui \
    && cd /comfyui && rm -rf .git \
    && pip install --no-cache-dir -c /tmp/constraints.txt -r requirements.txt

WORKDIR /app
COPY gpu-worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -c /tmp/constraints.txt -r requirements.txt

COPY gpu-worker/handler.py /app/handler.py
COPY gpu-worker/comfyui/extra_model_paths.yaml /app/extra_model_paths.yaml
COPY gpu-worker/workflows /app/workflows
# Installed under a different name than the pip package `omnivoice` to avoid a clash.
COPY gpu-worker/omnivoice /app/tts_omnivoice
COPY gpu-worker/scripts/calibrate_words.py /app/scripts/calibrate_words.py

ENV COMFYUI_DIR=/comfyui EXTRA_MODEL_PATHS=/app/extra_model_paths.yaml VOLUME_ROOT=/runpod-volume
CMD ["python", "-u", "/app/handler.py"]
