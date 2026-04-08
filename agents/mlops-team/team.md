# MLOps & Infrastructure Team

## Mission
Build and maintain infrastructure for training, deploying, and monitoring ML models at scale.

## Agents & Model Assignments
- **Infrastructure Engineer** (Sonnet): Docker, Kubernetes, cloud GPU setup
- **ML Pipeline Engineer** (Sonnet): Training pipelines, experiment tracking, model registry
- **Monitoring Engineer** (Haiku): Performance monitoring, data drift detection — mostly config

## Tech Stack
- Docker + Docker Compose (local dev)
- Kubernetes (production)
- MLflow / Weights & Biases (experiment tracking)
- DVC (data versioning)
- Hydra (experiment configuration)
- TorchServe / Triton (model serving)
- Prometheus + Grafana (monitoring)

## Code Location
- `infrastructure/docker/` — Dockerfiles and compose
- `infrastructure/k8s/` — Kubernetes manifests
- `infrastructure/monitoring/` — Monitoring config

## Key Pipelines
1. Data Pipeline: Raw CAE data → Parsed → Normalized → ML-ready
2. Training Pipeline: Config → Train → Evaluate → Register
3. Serving Pipeline: Model Registry → Serve → Monitor
