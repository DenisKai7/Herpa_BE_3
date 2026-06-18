FROM python:3.11-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
RUN pip install --no-cache-dir uv
COPY pyproject.toml README.md ./
COPY app ./app
RUN uv pip install --system --target /install .

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/opt/app/.local/bin:$PATH
RUN addgroup --system herpa && adduser --system --ingroup herpa --home /opt/app herpa
WORKDIR /opt/app
COPY --from=builder /install /usr/local/lib/python3.11/site-packages
COPY app ./app
COPY data_pipeline ./data_pipeline
COPY scripts ./scripts
COPY database ./database
RUN chown -R herpa:herpa /opt/app
USER herpa
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
