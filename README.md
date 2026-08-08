# LLM Lens

LLM Lens is a full-stack FastAPI dashboard for LLM API observability and cost tracking. It includes analytics for token usage, estimated spend, latency, error rates, budget alert configuration, request logs, and AI optimization recommendations.

## Features

- Interactive analytics dashboard with model and environment filters.
- FastAPI JSON endpoints for observability metrics, budget configuration, health checks, and optimization suggestions.
- Editable spend, warning, error-rate, and latency thresholds.
- Detailed API call logs with token counts, costs, latency, status, and endpoint names.
- Container-ready deployment using Docker and Kubernetes manifests.

## Project structure

```text
app/main.py              FastAPI application and API routes
index.html               Dashboard HTML shell
src/main.js              Browser client that consumes the FastAPI API
src/styles.css           Responsive dashboard styling
Dockerfile               Production container image definition
k8s/deployment.yaml      Kubernetes Deployment
k8s/service.yaml         Kubernetes Service
scripts/validate.mjs     Lightweight validation used by npm run build
```

## Run locally

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the FastAPI server:

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. Open the dashboard at <http://localhost:8000>.

## Validate the app

```bash
npm run build
python3 -m py_compile app/main.py
```

## API endpoints

- `GET /api/health` returns service health for probes.
- `GET /api/observability?model=All&env=All` returns filtered calls, model rates, environments, and aggregate metrics.
- `GET /api/budget` returns the active budget and alert thresholds.
- `PUT /api/budget` updates spend, warning, error-rate, and latency thresholds.
- `GET /api/optimizations` returns concrete token-efficiency and cost-reduction recommendations.

## Build and run with Docker

```bash
docker build -t llm-lens:latest .
docker run --rm -p 8000:8000 llm-lens:latest
```

Open <http://localhost:8000> after the container starts.

## Deploy to Kubernetes

1. Build and push an image to your registry:

   ```bash
   docker build -t ghcr.io/your-org/llm-lens:latest .
   docker push ghcr.io/your-org/llm-lens:latest
   ```

2. Update `k8s/deployment.yaml` so `spec.template.spec.containers[0].image` points to your pushed image.

3. Apply the manifests:

   ```bash
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   ```

4. Port-forward the service for a quick smoke test:

   ```bash
   kubectl port-forward service/llm-lens 8000:80
   ```

5. Open <http://localhost:8000>.

## Production notes

- Replace the in-memory sample data in `app/main.py` with your telemetry store or log pipeline.
- Persist budget configuration in a database or configuration service before running multiple replicas.
- Restrict CORS origins before exposing the API publicly.
- Add authentication for dashboards that contain customer prompts, request metadata, or spend data.
