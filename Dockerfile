# Moonlight — server + PTY interactive-claude worker + pipeline tools in one image.
FROM python:3.12-slim

# Pipeline tools: poppler (pdftoppm/pdfinfo), curl; node for the claude CLI.
RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI (interactive). Auth is provided by mounting the host's
# ~/.claude config at runtime (see docker-compose.yml) — NOT baked into the image.
RUN npm install -g @anthropic-ai/claude-code || true

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/
# Runtime data (papers/, jobs/) lives on a mounted volume; create mount points.
RUN mkdir -p /data/papers /data/jobs

ENV MOONLIGHT_DATA=/data \
    DASHBOARD_PORT=8090 \
    PYTHONUNBUFFERED=1

EXPOSE 8090

# Start both the dashboard and the worker (worker drives interactive claude in a PTY).
COPY scripts/docker-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
CMD ["/usr/local/bin/entrypoint.sh"]
