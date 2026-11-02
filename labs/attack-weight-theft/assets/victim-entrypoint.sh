#!/bin/sh
# Seed the victim from the host's public qwen2.5:0.5b, then create the fictional fine-tune.
# The weight blob stays the public GGUF. The private bytes are the SYSTEM and LICENSE lines.
set -eu

HOST_MAN=/host-models/manifests/registry.ollama.ai/library/qwen2.5/0.5b
DEST_MAN=/root/.ollama/models/manifests/registry.ollama.ai/library/qwen2.5/0.5b

if [ ! -f "$DEST_MAN" ]; then
  if [ ! -f "$HOST_MAN" ]; then
    echo "[!!] missing $HOST_MAN" >&2
    echo "[!!] on the host run: ollama pull qwen2.5:0.5b" >&2
    exit 1
  fi
  echo "[seed] copying qwen2.5:0.5b from the host store"
  mkdir -p "$(dirname "$DEST_MAN")" /root/.ollama/models/blobs
  cp "$HOST_MAN" "$DEST_MAN"
  grep -o 'sha256:[a-f0-9][a-f0-9]*' "$HOST_MAN" | while read -r digest; do
    hex=${digest#sha256:}
    src="/host-models/blobs/sha256-$hex"
    dst="/root/.ollama/models/blobs/sha256-$hex"
    if [ ! -f "$dst" ]; then
      cp "$src" "$dst"
      echo "[seed] blob $hex"
    fi
  done
else
  echo "[seed] qwen2.5:0.5b already in the volume"
fi

ollama serve &
pid=$!
i=0
while [ "$i" -lt 90 ]; do
  if ollama list >/dev/null 2>&1; then
    break
  fi
  i=$((i + 1))
  sleep 1
done
if ! ollama list >/dev/null 2>&1; then
  echo "[!!] ollama did not start" >&2
  kill "$pid" 2>/dev/null || true
  exit 1
fi
if ! ollama show lantern-ft >/dev/null 2>&1; then
  echo "[seed] creating lantern-ft"
  ollama create lantern-ft -f /models/Modelfile.ft || {
    kill "$pid" 2>/dev/null || true
    exit 1
  }
else
  echo "[seed] lantern-ft already present"
fi
wait "$pid"
