# syntax=docker/dockerfile:1
# atlas-app: the shared "Atlas Widgets" support-assistant fixture (compose profile rag-agent).
# Slim on purpose: FastAPI + httpx only, no torch. Model calls go to LAB_LLM_BASE_URL.
FROM python:3.12-slim-bookworm

COPY requirements.txt /opt/atlas-app/requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r /opt/atlas-app/requirements.txt \
 && useradd -m -u 1000 app \
 && mkdir -p /data \
 && chown 1000:1000 /data

COPY atlas_app /opt/atlas-app/atlas_app
ENV PYTHONPATH=/opt/atlas-app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ATLAS_APP_DATA=/data
USER app
WORKDIR /opt/atlas-app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"
CMD ["uvicorn", "atlas_app.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
