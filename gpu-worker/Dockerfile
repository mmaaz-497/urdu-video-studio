# GPU worker image: ComfyUI + Python deps. Model weights are NOT baked in; they are
# read from the RunPod network volume mounted at /runpod-volume (see volume/LAYOUT.md).
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

ENV PYTHONUNBUFFERED=1 DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends git ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# ComfyUI (pin a tag you have tested; Wan 2.2 TI2V nodes need a recent release).
ARG COMFYUI_REF=master
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /comfyui \
    && cd /comfyui && git checkout ${COMFYUI_REF} \
    && pip install --no-cache-dir -r requirements.txt

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY handler.py /app/handler.py
COPY comfyui/extra_model_paths.yaml /app/extra_model_paths.yaml
COPY workflows /app/workflows
# Installed under a different name than the pip package `omnivoice` to avoid a clash.
COPY omnivoice /app/tts_omnivoice
COPY scripts/calibrate_words.py /app/scripts/calibrate_words.py

ENV COMFYUI_DIR=/comfyui EXTRA_MODEL_PATHS=/app/extra_model_paths.yaml VOLUME_ROOT=/runpod-volume
CMD ["python", "-u", "/app/handler.py"]
