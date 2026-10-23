FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* && useradd --create-home --uid 10001 app
WORKDIR /app/pipeline
COPY pipeline/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=10001:10001 pipeline/ .
COPY _config/bookmakers.json /app/_config/bookmakers.json
RUN mkdir -p logs data models/model_store \
    && chown -R 10001:10001 logs data models/model_store
USER 10001
ENV APP_ENV=production PYTHONUNBUFFERED=1
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "5555"]
