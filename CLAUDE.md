# KyulAI - CAE-AI Platform

## Project Overview
General-purpose CAE-AI model for composite analysis. Predicts real-world experimental results using simulation data from multiple CAE tools (Moldex3D, AniForm, Digimat, Abaqus, Simutence, cadfil).

## Core Challenge
Sim-to-real transfer learning: abundant simulation data, scarce experimental data. The AI must learn to bridge the gap between simulation predictions and real-world behavior.

## Architecture
See `docs/architecture/agent-team-architecture.md` for the full system design.

## Agent Teams
- **Research Team**: Paper search, analysis, methodology recommendations
- **AI/ML Team**: Model architecture, training, evaluation
- **Data Engineering Team**: CAE tool parsers, data pipelines, unified schema
- **Domain Validation Team**: Physics validation, uncertainty quantification
- **Frontend Team**: Next.js web UI, 3D visualization
- **Backend Team**: FastAPI, PostgreSQL, task queues
- **MLOps Team**: Docker, experiment tracking, model serving
- **QA Team**: Testing across all components

## Tech Stack
- **ML**: PyTorch, torch-geometric, neuraloperator, deepxde
- **Backend**: FastAPI, SQLAlchemy, Celery + Redis, PostgreSQL
- **Frontend**: Next.js, TypeScript, VTK.js, Three.js
- **Data**: HDF5, meshio, pyvista, DVC
- **Infrastructure**: Docker, MLflow/W&B, MinIO

## Conventions
- Python: Use type hints, Pydantic models for data validation
- Follow PEP 8, max line length 100
- All ML experiments must be tracked in MLflow/W&B
- All data must pass through the unified schema before ML consumption
- Physics validation is mandatory before any model is considered "ready"
- Tests required for all parsers and data transformations

## Directory Layout
```
src/data/       — CAE parsers, schemas, pipelines
src/ml/         — Models, training, evaluation
src/validation/ — Physics checks, UQ
src/backend/    — FastAPI API
src/frontend/   — Next.js app
agents/         — Agent team definitions
research/       — Paper analysis outputs
```
