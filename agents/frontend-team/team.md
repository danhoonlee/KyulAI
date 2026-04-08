# Frontend Team

## Mission
Build an intuitive web interface for data management, model training, prediction, and 3D visualization.

## Agents & Model Assignments
- **Frontend Developer** (Sonnet): Implements Next.js pages and components
- **Visualization Engineer** (Sonnet): 3D mesh rendering, field visualization, uncertainty maps

## Key Pages
- `/dashboard` — Overview of datasets, models, recent experiments
- `/data/upload` — Upload simulation and experimental data
- `/data/browse` — Browse and filter datasets
- `/models/train` — Configure and launch training
- `/models/compare` — Side-by-side model comparison
- `/models/predict` — Run predictions on new data
- `/visualization/3d` — 3D mesh + field viewer
- `/visualization/sim-vs-exp` — Simulation vs experimental overlay

## Tech Stack
- Next.js + TypeScript
- VTK.js / Three.js for 3D
- Recharts / Plotly for charts
- TailwindCSS for styling

## Code Location
- `src/frontend/app/` — Next.js pages
- `src/frontend/components/` — React components
- `src/frontend/lib/` — API client, hooks, utilities
