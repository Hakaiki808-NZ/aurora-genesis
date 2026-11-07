FROM public.ecr.aws/lambda/python:3.12

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    TOKENIZERS_PARALLELISM=false

# CPU-only libraries; no remote model loading at runtime.
RUN python -m pip install --disable-pip-version-check --no-cache-dir \
      torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install --disable-pip-version-check --no-cache-dir \
      transformers==4.51.3 peft==0.15.2 accelerate==1.6.0 \
      huggingface_hub==0.36.0 safetensors==0.5.3

COPY genesis/ /var/task/genesis/
COPY config/ /var/task/config/
COPY cloud/genesis-lora-inference/handler.py /var/task/handler.py
COPY .genesis-model/ /var/task/model/
COPY .genesis-adapter/ /var/task/adapter/
COPY .genesis-adapter-metrics.json /var/task/adapter-metrics.json

RUN python -m compileall -q /var/task/genesis/ /var/task/handler.py
CMD ["handler.lambda_handler"]
