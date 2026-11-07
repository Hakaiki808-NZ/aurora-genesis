FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin genesis \
    && mkdir -p /state && chown 10001:10001 /state
COPY genesis /app/genesis
COPY config /app/config
COPY examples /app/examples
USER 10001:10001
EXPOSE 8766
CMD ["uvicorn", "genesis.api:app", "--host", "0.0.0.0", "--port", "8766", "--workers", "1"]
