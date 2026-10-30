# syntax=docker/dockerfile:1
# atlas-app: the shared "Atlas Widgets" support-assistant fixture (compose profile rag-agent).
# Slim on purpose: FastAPI + httpx + chromadb (ONNX runtime), no torch. Model calls go to LAB_LLM_BASE_URL.
# Telemetry off: chromadb (ANONYMIZED_TELEMETRY) and onnxruntime 1.31's 1DS events (ORT_DISABLE_TELEMETRY).
FROM python:3.12-slim-bookworm

COPY requirements.txt /opt/atlas-app/requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r /opt/atlas-app/requirements.txt \
 && useradd -m -u 1000 app \
 && mkdir -p /data \
 && chown 1000:1000 /data

# The RAG embedder (all-MiniLM-L6-v2 as chromadb's ONNX export), baked in at build time with the sha256
# that chromadb 1.5.9 itself pins, so nothing is downloaded at run time (rag.py refuses to).
ARG EMBEDDER_URL=https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz
ARG EMBEDDER_SHA256=913d7300ceae3b2dbc2c50d1de4baacab4be7b9380491c27fab7418616a16ec3
RUN python - <<PY
import hashlib, tarfile, urllib.request, pathlib
d = pathlib.Path("/opt/atlas-app/models/all-MiniLM-L6-v2"); d.mkdir(parents=True)
f = d / "onnx.tar.gz"
urllib.request.urlretrieve("${EMBEDDER_URL}", f)
h = hashlib.sha256(f.read_bytes()).hexdigest()
assert h == "${EMBEDDER_SHA256}", f"embedder sha256 mismatch: {h}"
tarfile.open(f).extractall(d, filter="data"); f.unlink()
print("embedder", sorted(p.name for p in (d / "onnx").iterdir()))
PY

COPY atlas_app /opt/atlas-app/atlas_app
ENV PYTHONPATH=/opt/atlas-app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ATLAS_APP_DATA=/data \
    ATLAS_APP_LABS=/labs \
    ATLAS_APP_EMBEDDER=/opt/atlas-app/models/all-MiniLM-L6-v2 \
    ANONYMIZED_TELEMETRY=False \
    ORT_DISABLE_TELEMETRY=1
USER app
WORKDIR /opt/atlas-app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)"
CMD ["uvicorn", "atlas_app.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
