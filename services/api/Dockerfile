FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN useradd --create-home --uid 10001 ufme && mkdir -p /data/uploads && chown ufme /data/uploads
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
COPY alembic.ini pyproject.toml ./
USER ufme
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=6 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').status==200 else 1)"
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

# Test image: dev tools + tests, run against the compose Postgres.
FROM runtime AS test
USER root
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt
COPY pytest.ini ./
COPY tests ./tests
COPY benchmarks ./benchmarks
RUN chown -R ufme /app
USER ufme
CMD ["sh", "-c", "ruff check . && ruff format --check . && mypy app && pytest -p no:cacheprovider --cov=app --cov-report=term --cov-fail-under=80 && python -m app.engines.benchmark --dataset medium --matcher baseline --check benchmarks/floor_medium_baseline.json && python -m app.engines.benchmark --dataset medium --matcher engine --check benchmarks/floor_medium_engine.json"]
