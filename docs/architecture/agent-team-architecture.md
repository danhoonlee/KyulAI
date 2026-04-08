# CAE-AI Agent Team Architecture
## General-Purpose CAE-AI Model for Composite Analysis

**Version**: 1.0
**Date**: 2026-04-08
**Goal**: Build AI models that predict real-world experimental results using CAE simulation data, bridging the sim-to-real gap in composite material analysis.

---

## 1. System Overview

### 1.1 Problem Statement

Composite material analysis relies on multiple CAE simulation tools (Moldex3D, AniForm, Digimat, Abaqus, Simutence, cadfil), each producing data in different formats and covering different physics domains. Experimental validation data is scarce and expensive to obtain. The goal is to develop AI models that:

1. Ingest heterogeneous simulation data from any supported CAE tool
2. Learn the systematic biases between simulation predictions and real-world behavior
3. Accurately predict experimental results using only simulation inputs
4. Quantify prediction uncertainty to know when the model is confident vs. uncertain

### 1.2 Core Technical Challenge: Sim-to-Real Transfer

This is fundamentally a **domain adaptation** problem. Simulation data (source domain) is abundant but imperfect. Experimental data (target domain) is scarce but ground-truth. Key approaches include:

- **Physics-Informed Neural Networks (PINNs)**: Embed conservation laws and boundary conditions as constraints
- **Neural Operators** (DeepONet, Fourier Neural Operator): Learn the mapping between input parameters and output fields
- **Multi-Fidelity Learning**: Combine data from simulations of varying fidelity levels
- **Domain Adaptation**: Unsupervised/semi-supervised methods to align simulation and experimental distributions
- **Transfer Learning**: Pre-train on simulation data, fine-tune on scarce experimental data
- **Graph Neural Networks**: Handle mesh-based simulation data natively
- **Bayesian Methods**: Uncertainty quantification for predictions with limited experimental validation

### 1.3 Supported CAE Tools & Data Domains

| Tool | Domain | Data Type | Typical Outputs |
|------|--------|-----------|-----------------|
| **Moldex3D** | SMC/RTM Molding | Flow, curing, fiber orientation | Pressure, temperature, fill time, fiber tensor |
| **AniForm** | Forming | Draping, deformation | Shear angles, thickness, wrinkle indicators |
| **Digimat** | Material Modeling | Micromechanics, homogenization | Effective properties, stress-strain curves |
| **Abaqus** | Structural FEA | Stress, failure, dynamics | Displacement, stress/strain fields, damage |
| **Simutence** | Multi-Process Sim | Coupled process chain | Process-induced deformations, residual stress |
| **cadfil** | Filament Winding | Winding paths, layup | Fiber paths, thickness distribution, angles |

---

## 2. Agent Team Architecture

### 2.1 Team Overview (8 Teams + Orchestrator)

```
                        +---------------------------+
                        |    ORCHESTRATOR AGENT      |
                        |   (Project Coordinator)    |
                        +---------------------------+
                                    |
          +-------------------------+-------------------------+
          |            |            |            |            |
    +-----+----+ +----+-----+ +---+------+ +---+------+ +---+------+
    | RESEARCH  | | AI/ML    | | DATA     | | DOMAIN   | | FRONTEND |
    | TEAM      | | TEAM     | | ENG TEAM | | VAL TEAM | | TEAM     |
    +----------+ +----------+ +----------+ +----------+ +----------+
                        |            |                       |
                  +-----+----+ +----+-----+           +-----+----+
                  | BACKEND  | | MLOps    |           | QA/TEST  |
                  | TEAM     | | TEAM     |           | TEAM     |
                  +----------+ +----------+           +----------+
```

---

### 2.1.1 Model Assignment Strategy

**Principle**: Use the most capable (expensive) model only where the task demands deep reasoning, novel synthesis, or safety-critical judgment. Use cheaper models everywhere else.

| Model | Cost | Use For |
|-------|------|---------|
| **Opus** | $$$ | Architecture decisions, novel methodology, cross-domain synthesis, physics-critical validation |
| **Sonnet** | $$ | Implementation, structured analysis, code generation, API design |
| **Haiku** | $ | Search, formatting, routine validation, boilerplate, simple parsing |

#### Full Agent-Model Map

| Team | Agent | Model | Rationale |
|------|-------|-------|-----------|
| **Orchestrator** | Project Coordinator | Sonnet | Routing is structured; doesn't need deep reasoning |
| **Research** | Paper Scout | Haiku | Keyword search and filtering — routine |
| **Research** | Paper Analyst | Sonnet | Structured extraction from papers |
| **Research** | Literature Synthesizer | **Opus** | Cross-paper insight synthesis requires deep reasoning |
| **Research** | Benchmark Tracker | Haiku | Tabular data collection — routine |
| **AI/ML** | ML Architect | **Opus** | Highest-stakes design decisions in the project |
| **AI/ML** | Model Developer | Sonnet | Implementation once architecture is decided |
| **AI/ML** | Hyperparameter Engineer | Haiku | Running sweeps and logging results |
| **AI/ML** | Evaluation Scientist | Sonnet | Structured analysis and metric computation |
| **Data Eng** | Parser Developer | Sonnet | Needs to understand file formats, write robust code |
| **Data Eng** | Schema Architect | **Opus** | Unified schema is foundational — must be right |
| **Data Eng** | Pipeline Engineer | Sonnet | ETL implementation is structured |
| **Data Eng** | Data Quality Agent | Haiku | Rule-based validation checks |
| **Domain Val** | Physics Validator | **Opus** | Safety-critical; must deeply understand physics |
| **Domain Val** | Uncertainty Quantifier | Sonnet | UQ method implementation is structured |
| **Domain Val** | Comparison Analyst | Sonnet | Structured comparison work |
| **Frontend** | Frontend Developer | Sonnet | Component implementation |
| **Frontend** | Visualization Engineer | Sonnet | 3D vis is complex but pattern-based |
| **Backend** | API Architect | Sonnet | API design follows established patterns |
| **Backend** | Backend Developer | Sonnet | Implementation |
| **Backend** | Database Engineer | Sonnet | Schema design and optimization |
| **Backend** | Integration Engineer | Sonnet | CAE tool connectors |
| **MLOps** | Infrastructure Engineer | Sonnet | Docker/K8s configuration |
| **MLOps** | ML Pipeline Engineer | Sonnet | Pipeline design and implementation |
| **MLOps** | Monitoring Engineer | Haiku | Mostly config and dashboards |
| **QA** | Test Engineer | Haiku | Writing tests is pattern-based |
| **QA** | ML Test Specialist | Sonnet | ML tests require deeper understanding |

**Cost Distribution**: ~5 Opus agents (19%), ~15 Sonnet agents (56%), ~6 Haiku agents (22%)
Only the most critical decision-makers use Opus — this saves ~60-70% vs. running everything on Opus.

---

### 2.2 Team 1: Research & Paper Analysis Team

**Mission**: Continuously discover, analyze, and synthesize relevant research to inform AI methodology decisions.

#### Agents

| Agent | Model | Role | Primary Tools |
|-------|-------|------|---------------|
| **Paper Scout** | Haiku | Searches arxiv, Google Scholar, Semantic Scholar, IEEE for relevant papers | WebSearch, WebFetch |
| **Paper Analyst** | Sonnet | Deep-reads papers, extracts methodology details, implementation specifics, results | Read, WebFetch, Write |
| **Literature Synthesizer** | **Opus** | Cross-references findings, identifies consensus approaches, gaps, and contradictions | Read, Write |
| **Benchmark Tracker** | Haiku | Tracks SOTA results on relevant benchmarks | WebSearch, Read, Write |

#### Key Research Domains to Monitor
- Physics-Informed Machine Learning (PINNs, physics-constrained architectures)
- Neural Operators (FNO, DeepONet, GNOT)
- Sim-to-Real Transfer Learning (domain adaptation, domain randomization)
- Graph Neural Networks for mesh-based simulation
- Multi-Fidelity Modeling (co-kriging, deep multi-fidelity)
- Composite material failure prediction with ML
- Uncertainty Quantification in ML predictions
- Few-Shot Learning for scarce data regimes

#### Outputs
- `research/papers/` — Annotated paper summaries with methodology extractions
- `research/syntheses/` — Cross-paper analysis documents
- `research/recommendations/` — Prioritized methodology recommendations for the AI/ML team
- `research/benchmarks/` — SOTA tracking tables

#### Workflow
```
1. Paper Scout → searches by domain keywords weekly
2. Paper Analyst → deep-reads top candidates, extracts:
   - Problem formulation
   - Model architecture
   - Training strategy
   - Dataset characteristics
   - Reported metrics
   - Limitations noted
3. Literature Synthesizer → produces synthesis reports:
   - "Best approaches for sim-to-real with <100 experimental samples"
   - "Comparison of neural operator architectures for CFD-like data"
   - "Physics constraints that improve composite failure prediction"
4. Benchmark Tracker → maintains leaderboards by task type
```

---

### 2.3 Team 2: AI/ML Development Team

**Mission**: Design, implement, train, and evaluate AI models based on research findings and domain requirements.

#### Agents

| Agent | Model | Role | Primary Tools |
|-------|-------|------|---------------|
| **ML Architect** | **Opus** | Designs model architectures; selects loss functions, training strategies | Read, Write, Bash |
| **Model Developer** | Sonnet | Implements models in PyTorch; writes training loops, data loaders | Read, Write, Edit, Bash |
| **Hyperparameter Engineer** | Haiku | Manages training runs, hyperparameter sweeps (Optuna/Ray Tune) | Bash, Read, Write |
| **Evaluation Scientist** | Sonnet | Designs evaluation protocols, runs benchmarks, comparison reports | Read, Write, Bash |

#### Model Architecture Strategy (Phased)

**Phase 1 — Baseline Models**
- Standard surrogate models (MLP, CNN on structured grids)
- Transfer learning: pre-train on simulation, fine-tune on experimental
- Establish baseline metrics

**Phase 2 — Physics-Informed Models**
- PINNs with composite-specific physics constraints
- Neural Operators (FNO for regular grids, DeepONet for irregular domains)
- Graph Neural Networks for unstructured meshes

**Phase 3 — Sim-to-Real Specialized**
- Domain adversarial training (DANN-style)
- Multi-fidelity fusion networks
- Bayesian neural networks for uncertainty quantification
- Few-shot adaptation modules for new experimental datasets

**Phase 4 — Novel Methodology Development**
- Hybrid architectures combining best elements from Phase 2-3
- Custom physics-informed domain adaptation
- Potentially publishable novel approaches

#### Core ML Components
```
src/ml/
├── models/
│   ├── surrogates/          # MLP, CNN baseline surrogates
│   ├── pinns/               # Physics-informed neural networks
│   ├── neural_operators/    # FNO, DeepONet implementations
│   ├── gnns/                # Graph neural networks for meshes
│   ├── domain_adaptation/   # DANN, MMD-based adaptation
│   ├── multi_fidelity/      # Multi-fidelity fusion models
│   └── uncertainty/         # Bayesian NN, ensemble, MC dropout
├── training/
│   ├── trainers.py          # Training loop abstractions
│   ├── losses.py            # Physics-informed + data-driven losses
│   ├── schedulers.py        # LR scheduling strategies
│   └── callbacks.py         # Early stopping, checkpointing
├── evaluation/
│   ├── metrics.py           # RMSE, MAE, R², physics violation metrics
│   ├── benchmarks.py        # Standardized benchmark suite
│   └── visualization.py     # Prediction vs ground truth plots
└── configs/
    └── experiments/         # Hydra/YAML experiment configs
```

---

### 2.4 Team 3: Data Engineering Team (RECOMMENDED — NEW)

**Mission**: Build robust data pipelines that ingest, normalize, and unify data from all CAE tools into a common representation.

> **Why this team is critical**: This is the foundation everything else depends on. Each CAE tool outputs data in different formats (VTK, CSV, proprietary binary, HDF5, ODB). Without a unified data layer, the ML team cannot train cross-tool models.

#### Agents

| Agent | Model | Role | Primary Tools |
|-------|-------|------|---------------|
| **Parser Developer** | Sonnet | Builds format-specific parsers for each CAE tool's output | Read, Write, Edit, Bash |
| **Schema Architect** | **Opus** | Designs the unified data schema that all tools map into | Read, Write |
| **Pipeline Engineer** | Sonnet | Builds ETL pipelines: raw data → parsed → normalized → ML-ready | Read, Write, Edit, Bash |
| **Data Quality Agent** | Haiku | Validates data integrity, detects anomalies, handles missing values | Read, Write, Bash |

#### Unified Data Schema Design

```
UnifiedCAERecord:
├── metadata
│   ├── source_tool: str          # "moldex3d", "abaqus", etc.
│   ├── simulation_type: str      # "structural", "flow", "thermal", "forming"
│   ├── material_system: str      # "CFRP", "GFRP", "SMC", etc.
│   ├── process_parameters: dict  # Tool-agnostic process params
│   └── timestamp: datetime
├── geometry
│   ├── mesh_type: str            # "structured", "unstructured", "point_cloud"
│   ├── nodes: array              # (N, 3) coordinates
│   ├── elements: array           # Connectivity
│   └── boundary_conditions: dict
├── input_fields
│   ├── material_properties: dict # Elastic, thermal, rheological props
│   ├── loading_conditions: dict  # Forces, pressures, temperatures
│   └── process_conditions: dict  # Injection params, cure cycles, etc.
├── output_fields
│   ├── scalar_fields: dict       # {field_name: (N,) array}
│   ├── vector_fields: dict       # {field_name: (N, 3) array}
│   ├── tensor_fields: dict       # {field_name: (N, 3, 3) array}
│   └── time_series: dict         # {field_name: (T, N) array}
└── experimental_reference (nullable)
    ├── source: str               # Lab, institution
    ├── measurements: dict        # Measured quantities
    ├── uncertainty: dict         # Measurement uncertainties
    └── conditions: dict          # Actual test conditions
```

#### Tool-Specific Parsers
```
src/data/parsers/
├── base.py              # Abstract parser interface
├── moldex3d_parser.py   # Moldex3D result files (.xml, .bin)
├── aniform_parser.py    # AniForm output files
├── digimat_parser.py    # Digimat result files (.daf)
├── abaqus_parser.py     # Abaqus ODB/HDF5 files
├── simutence_parser.py  # Simutence output formats
├── cadfil_parser.py     # cadfil winding data
└── experimental/
    ├── csv_parser.py    # Generic CSV experimental data
    ├── dic_parser.py    # Digital Image Correlation data
    └── test_machine.py  # Universal testing machine data
```

#### Data Pipeline Architecture
```
Raw Data (tool-specific)
    │
    ▼
[Parser Layer] — Tool-specific parsers extract data
    │
    ▼
[Normalization Layer] — Unit conversion, coordinate transforms, field mapping
    │
    ▼
[Unified Schema] — All data in common representation
    │
    ▼
[Feature Engineering] — Derived features, dimensionality reduction
    │
    ▼
[ML-Ready Dataset] — Train/val/test splits, data loaders
    │
    ▼
[Dataset Registry] — Versioned datasets with metadata (DVC or similar)
```

---

### 2.5 Team 4: Domain Validation Team (RECOMMENDED — NEW)

**Mission**: Ensure all AI predictions are physically meaningful and quantify prediction uncertainty.

> **Why this team is critical**: An AI model that predicts composite failure at 10x the actual strength is dangerous. Domain validation ensures predictions respect physical laws and known material behavior bounds.

#### Agents

| Agent | Model | Role | Primary Tools |
|-------|-------|------|---------------|
| **Physics Validator** | **Opus** | Checks predictions against conservation laws, constitutive relations, known bounds | Read, Write, Bash |
| **Uncertainty Quantifier** | Sonnet | Implements and evaluates UQ methods; calibrates confidence intervals | Read, Write, Bash |
| **Comparison Analyst** | Sonnet | Systematic comparison of model predictions vs. simulation vs. experiment | Read, Write, Bash |

#### Validation Checks

1. **Physical Consistency**
   - Conservation of mass/energy/momentum in predicted fields
   - Positive-definiteness of predicted stiffness tensors
   - Stress-strain predictions within material failure envelope
   - Fiber orientation tensors: eigenvalues ∈ [0,1], trace = 1

2. **Statistical Validation**
   - Prediction intervals calibrated against experimental scatter
   - Out-of-distribution detection for inputs unlike training data
   - Cross-validation with held-out experimental data

3. **Engineering Validation**
   - Predictions compared against analytical solutions (where available)
   - Sanity checks on predicted process windows
   - Failure mode predictions consistent with known composite failure mechanisms

---

### 2.6 Team 5: Frontend Team

**Mission**: Build an intuitive web interface for uploading data, configuring models, visualizing results, and managing experiments.

#### Agents

| Agent | Model | Role | Primary Tools |
|-------|-------|------|---------------|
| **Frontend Developer** | Sonnet | Implements React/Next.js components, state management, routing | Read, Write, Edit, Bash |
| **Visualization Engineer** | Sonnet | 3D mesh visualization, field plots, comparison overlays using Three.js/VTK.js | Read, Write, Edit, Bash |

#### Key UI Components

```
src/frontend/
├── app/                          # Next.js App Router
│   ├── dashboard/                # Overview: recent runs, model status
│   ├── data/
│   │   ├── upload/               # Upload simulation/experimental data
│   │   ├── browse/               # Browse datasets, filter by tool/material
│   │   └── quality/              # Data quality reports
│   ├── models/
│   │   ├── train/                # Configure & launch training runs
│   │   ├── compare/              # Side-by-side model comparison
│   │   └── predict/              # Run predictions on new data
│   ├── visualization/
│   │   ├── 3d-viewer/            # 3D mesh + field visualization
│   │   ├── sim-vs-exp/           # Simulation vs experimental overlay
│   │   └── uncertainty/          # Uncertainty visualization maps
│   ├── research/
│   │   └── papers/               # Research paper database & insights
│   └── settings/
├── components/
│   ├── viewers/                  # VTK.js / Three.js 3D viewers
│   ├── charts/                   # D3/Recharts plotting components
│   ├── forms/                    # Data upload, model config forms
│   └── common/                   # Shared UI components
└── lib/
    ├── api/                      # API client
    ├── hooks/                    # Custom React hooks
    └── utils/                    # Helpers
```

#### Visualization Requirements
- **3D Field Visualization**: Render simulation meshes with color-mapped fields (stress, temperature, fiber orientation)
- **Sim vs. Experiment Overlay**: Side-by-side or overlay comparison of predicted vs. measured fields
- **Uncertainty Maps**: Visualize prediction confidence as heatmaps on the geometry
- **Training Progress**: Real-time loss curves, metric tracking during model training
- **Data Explorer**: Interactive filtering and browsing of the unified dataset

---

### 2.7 Team 6: Backend Team

**Mission**: Build the API layer, business logic, database, and integrations that power the platform.

#### Agents

| Agent | Model | Role | Primary Tools |
|-------|-------|------|---------------|
| **API Architect** | Sonnet | Designs RESTful API endpoints, authentication, rate limiting | Read, Write |
| **Backend Developer** | Sonnet | Implements FastAPI services, business logic, file handling | Read, Write, Edit, Bash |
| **Database Engineer** | Sonnet | Designs PostgreSQL schema, manages migrations, optimizes queries | Read, Write, Edit, Bash |
| **Integration Engineer** | Sonnet | Builds connectors to CAE tools, file format handlers, cloud storage | Read, Write, Edit, Bash |

#### Backend Architecture

```
src/backend/
├── api/
│   ├── routes/
│   │   ├── data.py              # Upload, browse, manage datasets
│   │   ├── models.py            # Train, evaluate, predict endpoints
│   │   ├── experiments.py       # Experiment tracking & comparison
│   │   ├── visualization.py     # Data for 3D rendering
│   │   └── research.py          # Paper database endpoints
│   ├── middleware/
│   │   ├── auth.py              # Authentication (JWT/OAuth)
│   │   └── validation.py        # Request validation
│   └── main.py                  # FastAPI app entry
├── services/
│   ├── data_service.py          # Data ingestion orchestration
│   ├── training_service.py      # Model training orchestration
│   ├── prediction_service.py    # Inference service
│   └── experiment_service.py    # Experiment management
├── models/                      # SQLAlchemy/Pydantic models
│   ├── dataset.py
│   ├── experiment.py
│   ├── ml_model.py
│   └── user.py
├── db/
│   ├── migrations/              # Alembic migrations
│   └── session.py               # Database session management
└── workers/
    ├── training_worker.py       # Async training job runner
    ├── parsing_worker.py        # Async data parsing jobs
    └── celery_config.py         # Task queue configuration
```

#### API Design (Key Endpoints)

```
POST   /api/v1/data/upload              # Upload raw CAE/experimental data
GET    /api/v1/data/datasets             # List available datasets
GET    /api/v1/data/datasets/{id}        # Get dataset details
POST   /api/v1/data/datasets/{id}/parse  # Trigger parsing pipeline

POST   /api/v1/models/train              # Launch training run
GET    /api/v1/models/experiments        # List experiments
GET    /api/v1/models/experiments/{id}   # Get experiment details + metrics
POST   /api/v1/models/predict            # Run inference

GET    /api/v1/visualization/mesh/{id}   # Get mesh data for 3D rendering
GET    /api/v1/visualization/fields/{id} # Get field data for visualization

GET    /api/v1/research/papers           # Browse research papers
POST   /api/v1/research/search           # Search papers by topic
```

---

### 2.8 Team 7: MLOps & Infrastructure Team (RECOMMENDED — NEW)

**Mission**: Build and maintain the infrastructure for training, deploying, and monitoring ML models at scale.

> **Why this team is critical**: Training physics-informed models on large simulation datasets requires GPU infrastructure, experiment tracking, model versioning, and reproducible pipelines. Without MLOps, the AI/ML team will waste time on infrastructure instead of modeling.

#### Agents

| Agent | Model | Role | Primary Tools |
|-------|-------|------|---------------|
| **Infrastructure Engineer** | Sonnet | Docker, Kubernetes, cloud GPU setup (AWS/GCP) | Read, Write, Bash |
| **ML Pipeline Engineer** | Sonnet | Training pipelines, experiment tracking (MLflow/W&B), model registry | Read, Write, Edit, Bash |
| **Monitoring Engineer** | Haiku | Model performance monitoring, data drift detection, alerting | Read, Write, Bash |

#### Infrastructure Stack

```
infrastructure/
├── docker/
│   ├── Dockerfile.api           # Backend API container
│   ├── Dockerfile.worker        # Training worker with CUDA
│   ├── Dockerfile.frontend      # Frontend container
│   └── docker-compose.yml       # Local development stack
├── k8s/
│   ├── deployments/             # Kubernetes deployments
│   ├── services/                # Service definitions
│   └── jobs/                    # Training job templates
├── terraform/                   # Cloud infrastructure as code
└── monitoring/
    ├── prometheus/              # Metrics collection
    ├── grafana/                 # Dashboards
    └── alerts/                  # Alert rules
```

#### ML Pipeline
```
[Data Versioning (DVC)] → [Experiment Config (Hydra)] → [Training (PyTorch)]
         │                        │                           │
         ▼                        ▼                           ▼
  [Dataset Registry]     [Config Registry]          [Experiment Tracking]
                                                    (MLflow / W&B)
                                                          │
                                                          ▼
                                                   [Model Registry]
                                                          │
                                                          ▼
                                                   [Model Serving]
                                                   (TorchServe/Triton)
```

---

### 2.9 Team 8: QA & Testing Team (RECOMMENDED — NEW)

**Mission**: Ensure platform reliability through comprehensive testing across all components.

#### Agents

| Agent | Model | Role | Primary Tools |
|-------|-------|------|---------------|
| **Test Engineer** | Haiku | Unit tests, integration tests, E2E tests | Read, Write, Edit, Bash |
| **ML Test Specialist** | Sonnet | Model validation tests, regression tests, data pipeline tests | Read, Write, Bash |

#### Testing Strategy
- **Unit Tests**: All parsers, data transformations, model components
- **Integration Tests**: API endpoints, data pipeline end-to-end, training pipeline
- **ML-Specific Tests**: Model determinism, gradient flow, physics constraint satisfaction
- **E2E Tests**: Full workflow from data upload to prediction visualization

---

## 3. Orchestrator Agent

**Mission**: Coordinate all teams, manage dependencies, resolve conflicts, and maintain project coherence.

### Responsibilities
1. **Task Routing**: Receives user requests and routes to appropriate team(s)
2. **Dependency Management**: Ensures teams work in correct order (e.g., Data Engineering before ML)
3. **Cross-Team Communication**: Facilitates information flow between teams
4. **Progress Tracking**: Maintains project status and reports to user
5. **Conflict Resolution**: Resolves technical disagreements between teams

### Orchestration Flow

```
User Request
    │
    ▼
[Orchestrator Agent]
    │
    ├─── Classify request type
    ├─── Identify required teams
    ├─── Check dependencies & prerequisites
    ├─── Dispatch tasks to teams (parallel where possible)
    ├─── Collect results
    ├─── Validate cross-team consistency
    └─── Report back to user
```

### Inter-Team Dependencies (Data Flow)

```
Research Team ──findings──▶ AI/ML Team
Data Eng Team ──data──▶ AI/ML Team
AI/ML Team ──models──▶ Domain Validation Team
AI/ML Team ──requirements──▶ MLOps Team
Backend Team ──APIs──▶ Frontend Team
Data Eng Team ──schemas──▶ Backend Team
MLOps Team ──infra──▶ AI/ML Team (training infrastructure)
Domain Validation ──feedback──▶ AI/ML Team (model improvements)
QA Team ──tests──▶ All Teams
```

### Inter-Team Communication Matrix

Defines which teams can directly communicate, what they exchange, and the communication channel.

**Communication Rule**: Teams may only communicate with teams listed in their row. All other cross-team requests must go through the **Orchestrator**.

| From → To | Research | AI/ML | Data Eng | Domain Val | Frontend | Backend | MLOps | QA |
|-----------|----------|-------|----------|------------|----------|---------|-------|----|
| **Research** | — | Direct | — | — | — | — | — | — |
| **AI/ML** | Direct | — | Direct | Direct | — | Request | Direct | — |
| **Data Eng** | — | Direct | — | — | — | Direct | — | — |
| **Domain Val** | Direct | Direct | — | — | — | — | — | — |
| **Frontend** | — | — | — | — | — | Direct | — | — |
| **Backend** | — | — | Direct | — | Direct | — | Direct | — |
| **MLOps** | — | Direct | — | — | — | Direct | — | — |
| **QA** | — | — | — | — | — | — | — | — |

**Legend**: `Direct` = can communicate without Orchestrator. `Request` = must go through Orchestrator. `—` = no direct channel.

### Communication Channels & Protocols

| Channel | From | To | What Gets Exchanged | Format |
|---------|------|----|---------------------|--------|
| **Research → AI/ML** | Literature Synthesizer | ML Architect | Methodology recommendations, paper findings, SOTA benchmarks | `research/recommendations/*.md` |
| **AI/ML → Data Eng** | ML Architect | Schema Architect, Pipeline Engineer | Data requirements, feature requests, format needs | GitHub Issues / `docs/requests/` |
| **Data Eng → AI/ML** | Pipeline Engineer | Model Developer | ML-ready datasets, schema updates, new parser availability | Dataset registry notifications |
| **AI/ML → Domain Val** | Evaluation Scientist | Physics Validator | Trained models + predictions for validation | Model artifacts + prediction files |
| **Domain Val → AI/ML** | Physics Validator | ML Architect | Validation results, physics violations, correction guidance | `validation/reports/*.md` |
| **Domain Val → Research** | Physics Validator | Literature Synthesizer | Requests for papers on specific physics constraints or failure modes | `research/requests/*.md` |
| **Data Eng → Backend** | Schema Architect | Database Engineer | Unified schema definitions, API data contracts | `src/data/schemas/` |
| **Backend → Frontend** | API Architect | Frontend Developer | API specs, endpoint changes, data models | OpenAPI spec (`docs/api/openapi.yaml`) |
| **Frontend → Backend** | Frontend Developer | API Architect | UI data requirements, new endpoint requests | GitHub Issues |
| **AI/ML → MLOps** | ML Architect | ML Pipeline Engineer | Training configs, resource requirements, deployment specs | `src/ml/configs/` |
| **MLOps → AI/ML** | ML Pipeline Engineer | Model Developer | Infrastructure updates, GPU availability, pipeline changes | `infrastructure/` configs |
| **MLOps → Backend** | Infrastructure Engineer | Backend Developer | Deployment configs, service mesh updates | `infrastructure/k8s/` |
| **Backend → Data Eng** | Integration Engineer | Parser Developer | Raw file handling requirements, storage paths | `src/backend/workers/` |
| **QA → Orchestrator** | Test Engineer | Orchestrator | Test failures, coverage reports — Orchestrator routes to responsible team | `tests/reports/` |

### Communication Rules

1. **QA never communicates directly with other teams** — all test failures and quality issues are reported to the Orchestrator, who routes them to the responsible team. This prevents QA from becoming a bottleneck or creating conflicting priorities.

2. **Frontend and AI/ML have no direct channel** — Frontend gets model results through Backend APIs. This enforces clean separation and prevents tight coupling between UI and ML internals.

3. **Research Team only talks to AI/ML and Domain Validation** — Research outputs feed methodology decisions (AI/ML) and respond to physics questions (Domain Val). They don't interact with implementation teams.

4. **Data Engineering is the gatekeeper for AI/ML data** — AI/ML never reads raw CAE files directly. All data must flow through Data Eng's parsers and unified schema.

5. **All cross-team architectural decisions go through Orchestrator** — If a communication would change the interface contract between teams (e.g., schema change, API change), the Orchestrator must approve it.

### Communication Flow Diagram

```
                              ┌──────────────┐
                              │ ORCHESTRATOR  │
                              │   (Sonnet)    │
                              └──────┬───────┘
                                     │ Routes QA issues,
                                     │ approves cross-team
                                     │ architecture changes
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
   ┌────▼─────┐    findings    ┌─────▼────┐   models    ┌────────▼───────┐
   │ RESEARCH │ ──────────────▶│  AI/ML   │ ──────────▶│ DOMAIN         │
   │          │◀───────────────│          │◀────────────│ VALIDATION     │
   └──────────┘  physics Q's   └────┬──┬──┘  feedback   └────────────────┘
                                    │  │
                          data reqs │  │ training configs
                                    │  │
                               ┌────▼──▼──┐
                    ┌──────────│ DATA ENG  │
                    │          └───────────┘
                    │ schemas
               ┌────▼────┐         APIs        ┌──────────┐
               │ BACKEND │ ◀──────────────────▶│ FRONTEND │
               └────┬────┘                      └──────────┘
                    │
                    │ deploy configs
               ┌────▼────┐
               │  MLOps  │◀───── training configs ──── AI/ML
               └─────────┘

   ┌─────────┐
   │   QA    │ ──── all reports go through Orchestrator ────▶ (routed to team)
   └─────────┘
```

---

## 4. Data Flow Architecture

### 4.1 End-to-End Data Flow

```
                    ┌─────────────────────────────────────────────┐
                    │              DATA SOURCES                    │
                    │                                              │
                    │  Moldex3D  AniForm  Digimat  Abaqus  ...    │
                    │  (SMC/RTM) (Form)   (Mat)    (FEA)          │
                    │     │        │        │        │             │
                    │  Experimental Data (DIC, UTM, DSC, ...)     │
                    └──────────────────┬──────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────────┐
                    │         DATA ENGINEERING LAYER               │
                    │                                              │
                    │  [Parsers] → [Normalization] → [Unified DB] │
                    │                                    │         │
                    │  [Feature Engineering] → [ML Datasets]      │
                    └──────────────────┬──────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────────┐
                    │           AI/ML LAYER                        │
                    │                                              │
                    │  [Training] → [Evaluation] → [Model Store]  │
                    │       │                           │          │
                    │  [Physics Validation] ◄───────────┘          │
                    └──────────────────┬──────────────────────────┘
                                       │
                    ┌──────────────────▼──────────────────────────┐
                    │         APPLICATION LAYER                    │
                    │                                              │
                    │  [Backend API] ◄──► [Frontend UI]           │
                    │       │                    │                 │
                    │  [Predictions] ──▶ [3D Visualization]       │
                    │  [Uncertainty] ──▶ [Confidence Maps]        │
                    └─────────────────────────────────────────────┘
```

### 4.2 Sim-to-Real Training Pipeline

```
┌────────────────────────────────────────────────────────────────┐
│                                                                 │
│  STEP 1: Pre-train on abundant simulation data                  │
│  ┌──────────┐    ┌───────────┐    ┌──────────────────┐         │
│  │ Sim Data │───▶│ Pre-train │───▶│ Base Model       │         │
│  │ (large)  │    │ (all tools│    │ (learns physics) │         │
│  └──────────┘    └───────────┘    └────────┬─────────┘         │
│                                             │                   │
│  STEP 2: Domain adaptation                  │                   │
│  ┌──────────┐    ┌───────────┐    ┌────────▼─────────┐         │
│  │ Sim Data │───▶│ Domain    │───▶│ Adapted Model    │         │
│  │ + few    │    │ Adaptation│    │ (aligned domains)│         │
│  │ Exp Data │    └───────────┘    └────────┬─────────┘         │
│  └──────────┘                              │                   │
│                                             │                   │
│  STEP 3: Fine-tune on experimental data     │                   │
│  ┌──────────┐    ┌───────────┐    ┌────────▼─────────┐         │
│  │ Exp Data │───▶│ Fine-tune │───▶│ Final Model      │         │
│  │ (scarce) │    │ (careful) │    │ (sim-to-real)    │         │
│  └──────────┘    └───────────┘    └────────┬─────────┘         │
│                                             │                   │
│  STEP 4: Validate & quantify uncertainty    │                   │
│  ┌──────────┐    ┌───────────┐    ┌────────▼─────────┐         │
│  │ Held-out │───▶│ Validate  │───▶│ Calibrated Model │         │
│  │ Exp Data │    │ + UQ      │    │ + Uncertainty     │         │
│  └──────────┘    └───────────┘    └──────────────────┘         │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

---

## 5. Technology Stack

### 5.1 Core Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **ML Framework** | PyTorch | Best ecosystem for research-grade models, PINNs, neural operators |
| **ML Experiment Tracking** | MLflow or Weights & Biases | Experiment logging, model registry, artifact storage |
| **Data Versioning** | DVC (Data Version Control) | Version large simulation datasets alongside code |
| **Config Management** | Hydra | Composable experiment configurations |
| **Backend** | FastAPI (Python) | Async, fast, great typing support, same language as ML |
| **Task Queue** | Celery + Redis | Async training jobs, data parsing jobs |
| **Database** | PostgreSQL | Metadata, experiment records, user data |
| **Object Storage** | MinIO (local) / S3 (cloud) | Large simulation files, model artifacts |
| **Frontend** | Next.js + TypeScript | SSR, great DX, large ecosystem |
| **3D Visualization** | VTK.js + Three.js | Industry standard for scientific visualization |
| **Charts** | Recharts or Plotly | Interactive data visualization |
| **Containerization** | Docker + Docker Compose | Reproducible environments |
| **Orchestration** | Kubernetes (production) | Scalable deployment |
| **CI/CD** | GitHub Actions | Automated testing and deployment |

### 5.2 Key Python Libraries

```
# ML Core
torch >= 2.0
torch-geometric              # Graph neural networks
neuraloperator               # FNO, DeepONet (NVIDIA)
deepxde                      # PINNs framework

# Data
numpy, scipy
pandas
h5py                         # HDF5 for large arrays
meshio                       # Mesh I/O (VTK, Abaqus, etc.)
pyvista                      # 3D mesh processing

# ML Infrastructure
mlflow / wandb
optuna                       # Hyperparameter optimization
hydra-core                   # Configuration

# Backend
fastapi
sqlalchemy
alembic                      # Database migrations
celery[redis]
pydantic

# Scientific
scikit-learn
matplotlib
```

---

## 6. Project Directory Structure

```
KyulAI/
├── CLAUDE.md                           # Project instructions for all agents
├── README.md                           # Project overview
├── pyproject.toml                      # Python project config
│
├── docs/
│   ├── architecture/
│   │   └── agent-team-architecture.md  # This document
│   ├── api/                            # API documentation
│   └── guides/                         # User & developer guides
│
├── agents/                             # Agent team definitions
│   ├── orchestrator/
│   │   └── agent.md                    # Orchestrator agent definition
│   ├── research-team/
│   │   ├── team.md                     # Team definition
│   │   ├── paper-scout.md
│   │   ├── paper-analyst.md
│   │   └── literature-synthesizer.md
│   ├── ai-ml-team/
│   │   ├── team.md
│   │   ├── ml-architect.md
│   │   ├── model-developer.md
│   │   └── evaluation-scientist.md
│   ├── data-engineering-team/
│   │   ├── team.md
│   │   ├── parser-developer.md
│   │   ├── schema-architect.md
│   │   └── pipeline-engineer.md
│   ├── domain-validation-team/
│   │   ├── team.md
│   │   ├── physics-validator.md
│   │   └── uncertainty-quantifier.md
│   ├── frontend-team/
│   │   ├── team.md
│   │   ├── frontend-developer.md
│   │   └── visualization-engineer.md
│   ├── backend-team/
│   │   ├── team.md
│   │   ├── api-architect.md
│   │   └── backend-developer.md
│   ├── mlops-team/
│   │   ├── team.md
│   │   ├── infra-engineer.md
│   │   └── pipeline-engineer.md
│   └── qa-team/
│       ├── team.md
│       └── test-engineer.md
│
├── src/
│   ├── data/                           # Data Engineering
│   │   ├── parsers/                    # CAE tool parsers
│   │   ├── schemas/                    # Unified data schemas
│   │   ├── pipelines/                  # ETL pipelines
│   │   └── quality/                    # Data validation
│   │
│   ├── ml/                             # AI/ML Core
│   │   ├── models/                     # Model architectures
│   │   ├── training/                   # Training infrastructure
│   │   ├── evaluation/                 # Evaluation & metrics
│   │   └── configs/                    # Experiment configs
│   │
│   ├── validation/                     # Domain Validation
│   │   ├── physics/                    # Physics constraint checks
│   │   ├── uncertainty/                # UQ methods
│   │   └── comparison/                 # Sim vs exp analysis
│   │
│   ├── backend/                        # Backend API
│   │   ├── api/                        # FastAPI routes
│   │   ├── services/                   # Business logic
│   │   ├── models/                     # DB models
│   │   ├── db/                         # Database
│   │   └── workers/                    # Async workers
│   │
│   └── frontend/                       # Frontend App
│       ├── app/                        # Next.js pages
│       ├── components/                 # React components
│       └── lib/                        # Utilities
│
├── research/                           # Research Team outputs
│   ├── papers/                         # Paper summaries
│   ├── syntheses/                      # Cross-paper analysis
│   └── recommendations/               # Methodology recommendations
│
├── tests/                              # Test suite
│   ├── unit/
│   ├── integration/
│   └── ml/                             # ML-specific tests
│
├── infrastructure/                     # DevOps & MLOps
│   ├── docker/
│   ├── k8s/
│   └── monitoring/
│
├── data/                               # Local data (gitignored)
│   ├── raw/                            # Raw CAE outputs
│   ├── processed/                      # Parsed & normalized
│   ├── datasets/                       # ML-ready datasets
│   └── experimental/                   # Experimental data
│
└── models/                             # Trained model artifacts (gitignored)
    ├── checkpoints/
    └── registry/
```

---

## 7. Implementation Roadmap

### Phase 0: Foundation (Weeks 1-2)
- [ ] Set up project repository and directory structure
- [ ] Configure development environment (Docker, Python, Node.js)
- [ ] Set up CI/CD pipeline
- [ ] Write CLAUDE.md with project conventions
- [ ] Define agent team configurations

### Phase 1: Data Infrastructure (Weeks 3-6)
- [ ] Design and implement unified data schema
- [ ] Build parsers for 2-3 priority CAE tools (start with Abaqus + Moldex3D)
- [ ] Build basic ETL pipeline
- [ ] Set up PostgreSQL + MinIO for data storage
- [ ] Create data upload API endpoints
- [ ] Basic frontend: data upload + browse

### Phase 2: Baseline ML (Weeks 7-10)
- [ ] Research team: Literature review on sim-to-real for composites
- [ ] Implement baseline surrogate models (MLP, CNN)
- [ ] Set up experiment tracking (MLflow/W&B)
- [ ] Implement basic transfer learning pipeline
- [ ] Build evaluation framework with composite-relevant metrics
- [ ] Basic frontend: training dashboard

### Phase 3: Advanced Models (Weeks 11-16)
- [ ] Implement Physics-Informed Neural Networks
- [ ] Implement Neural Operators (FNO/DeepONet)
- [ ] Implement Graph Neural Networks for mesh data
- [ ] Domain adaptation methods (DANN, MMD)
- [ ] Multi-fidelity learning
- [ ] Domain validation: physics constraint checking
- [ ] Remaining CAE tool parsers

### Phase 4: Sim-to-Real Specialization (Weeks 17-22)
- [ ] Few-shot fine-tuning on experimental data
- [ ] Uncertainty quantification (Bayesian NN, ensembles)
- [ ] Calibrated confidence intervals
- [ ] Advanced visualization (3D fields, uncertainty maps)
- [ ] Comprehensive API for all model operations

### Phase 5: Production & Polish (Weeks 23-28)
- [ ] Kubernetes deployment
- [ ] Model serving optimization (TorchServe/Triton)
- [ ] Performance monitoring and drift detection
- [ ] Full test coverage
- [ ] Documentation
- [ ] Novel methodology development based on learnings

---

## 8. Key Design Decisions & Rationale

### 8.1 Why Python for Everything Backend + ML?
- Single language across ML and backend eliminates serialization overhead
- FastAPI is async and performant enough for this use case
- PyTorch ecosystem is Python-native

### 8.2 Why a Unified Data Schema?
- ML models need consistent input regardless of source tool
- Enables cross-tool transfer learning (model trained on Abaqus data can predict for Moldex3D)
- Simplifies the ML pipeline — data loaders don't need to know the source tool

### 8.3 Why Separate Data Engineering from Backend?
- Data engineering is a domain-specific challenge (parsing proprietary CAE formats)
- Backend team focuses on API/business logic
- Different skill sets and concerns

### 8.4 Why Domain Validation as a Separate Team?
- Physics validation is as important as ML accuracy
- A prediction that is statistically good but physically impossible is worthless
- Uncertainty quantification is a specialized discipline

### 8.5 Why Phase Sim-to-Real in Steps?
- Pre-train → Adapt → Fine-tune is proven more effective than end-to-end training
- Each phase can be validated independently
- If experimental data is very scarce, domain adaptation alone may suffice
