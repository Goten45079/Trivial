# LLM Lens

LLM Lens is a production-oriented FastAPI dashboard for LLM API observability and cost tracking. Teams can ingest real model-call telemetry, inspect spend and reliability trends, configure budget alerts, and identify concrete optimization opportunities.

## Production features

- FastAPI backend serving the dashboard and JSON APIs.
- SQLite persistence for call telemetry and budget thresholds by default.
- Single-call and batch ingestion endpoints for real LLM traffic.
- Optional API-key protection for write endpoints with `LLM_LENS_API_KEY`.
- Interactive dashboard with model/environment filters, usage/cost/latency/error metrics, logs, and recommendations.
- Docker image and Kubernetes Deployment/Service manifests with health probes and resource limits.

## Project structure

```text
app/main.py              FastAPI application, schemas, auth, and API routes
app/settings.py          Environment-based runtime configuration
app/store.py             SQLite persistence layer and seed telemetry
index.html               Dashboard HTML shell
src/main.js              Browser client that consumes FastAPI APIs
src/styles.css           Responsive dashboard styling
Dockerfile               Production container image definition
k8s/deployment.yaml      Kubernetes Deployment
k8s/service.yaml         Kubernetes Service
scripts/validate.mjs     Lightweight validation used by npm run build
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `LLM Lens` | Name returned by health checks. |
| `APP_ENV` | `production` | Runtime environment label. |
| `DATABASE_PATH` | `data/llm_lens.db` | SQLite database location. Mount this path to persist data in containers. |
| `CORS_ORIGINS` | `*` | Comma-separated allowed browser origins. Restrict this in production. |
| `LLM_LENS_API_KEY` | empty | Optional API key required for ingestion and budget updates when set. |

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open <http://localhost:8000>.

## Validate the app

```bash
npm run build
python3 -m py_compile app/main.py app/settings.py app/store.py
```

## Ingest real model telemetry

Instrument your application after each provider call and POST the observed token usage, latency, model, status, and endpoint to LLM Lens.

```bash
curl -X POST http://localhost:8000/api/calls \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-secret' \
  -d '{
    "model": "gpt-4.1-mini",
    "env": "Production",
    "prompt": 1240,
    "completion": 380,
    "latency": 742,
    "status": "success",
    "endpoint": "/chat/respond",
    "metadata": {"team": "support", "customerTier": "enterprise"}
  }'
```

For high-volume systems, batch calls:

```bash
curl -X POST http://localhost:8000/api/calls/batch \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-secret' \
  -d '[{"model":"gpt-4.1-mini","env":"Production","prompt":500,"completion":120,"latency":430,"status":"success","endpoint":"/classify"}]'
```

If `LLM_LENS_API_KEY` is unset, write endpoints are open for local development. Set it before deploying to shared environments.

## Recommended application instrumentation pattern

1. Capture the start time before calling your LLM provider.
2. Call the provider from your application as usual.
3. Read prompt and completion token counts from the provider response usage metadata.
4. POST a telemetry record to `/api/calls` with status `success`.
5. If the provider call fails, POST a telemetry record with status `error`, zero tokens if usage is unavailable, and the measured latency.

This keeps LLM Lens provider-neutral and avoids putting model API keys inside the dashboard service.

## API endpoints

- `GET /api/health` returns service health for load balancers and Kubernetes probes.
- `GET /api/observability?model=All&env=All&limit=500` returns filtered calls, model rates, discovered models/environments, and aggregate metrics.
- `POST /api/calls` ingests one real call telemetry record.
- `POST /api/calls/batch` ingests multiple telemetry records.
- `GET /api/budget` returns active budget and alert thresholds.
- `PUT /api/budget` updates spend, warning, error-rate, and latency thresholds.
- `GET /api/optimizations` returns data-aware token-efficiency and reliability recommendations.

## Build and run with Docker

```bash
docker build -t llm-lens:latest .
docker run --rm \
  -p 8000:8000 \
  -e LLM_LENS_API_KEY=dev-secret \
  -e DATABASE_PATH=/app/data/llm_lens.db \
  -v llm-lens-data:/app/data \
  llm-lens:latest
```

Open <http://localhost:8000> after the container starts.

## Deploy to Kubernetes

1. Build and push an image to your registry:

   ```bash
   docker build -t ghcr.io/your-org/llm-lens:latest .
   docker push ghcr.io/your-org/llm-lens:latest
   ```

2. Create an API-key secret for write endpoints:

   ```bash
   kubectl create secret generic llm-lens-secrets \
     --from-literal=LLM_LENS_API_KEY='replace-me'
   ```

3. Update `k8s/deployment.yaml` so the image points to your pushed image.

4. Apply the manifests:

   ```bash
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   ```

5. Port-forward for a smoke test:

   ```bash
   kubectl port-forward service/llm-lens 8000:80
   ```

6. Open <http://localhost:8000>.

## Production hardening checklist

- Mount persistent storage for `DATABASE_PATH`, or replace SQLite with Postgres for multi-replica writes.
- Restrict `CORS_ORIGINS` to company domains.
- Set `LLM_LENS_API_KEY` or put the service behind your identity-aware proxy/API gateway.
- Avoid sending raw prompts or completions unless your security team approves; use metadata tags instead.
- Send team, feature, customer tier, and route labels in `metadata` for better chargeback reporting.
- Add alerts from `/api/observability` to your existing incident tooling if thresholds are breached.
