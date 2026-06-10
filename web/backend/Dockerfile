# Build context is the repo root (training-analyzer/) so the analyzer scripts
# are copied straight in — single source of truth, no vendored duplicates.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    SCRIPTS_DIR=/opt/scripts \
    MPLCONFIGDIR=/tmp/mpl

WORKDIR /app

# Backend deps + analyzer runtime deps.
COPY web/backend/requirements.txt /app/requirements.txt
COPY requirements.txt /opt/scripts-requirements.txt
RUN pip install -r /app/requirements.txt -r /opt/scripts-requirements.txt

# Analyzer scripts and the API.
COPY fetch_training_data.py plot_training.py /opt/scripts/
COPY web/backend/app /app/app

# Run as an unprivileged user; /tmp is the only writable spot it needs.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app /opt/scripts
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
