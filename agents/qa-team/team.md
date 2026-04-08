# QA & Testing Team

## Mission
Ensure platform reliability through comprehensive testing across all components.

## Agents & Model Assignments
- **Test Engineer** (Haiku): Unit tests, integration tests, E2E tests — pattern-based
- **ML Test Specialist** (Sonnet): Model validation, regression tests, data pipeline tests

## Testing Strategy
- **Unit Tests**: All parsers, data transformations, model components
- **Integration Tests**: API endpoints, data pipeline E2E, training pipeline
- **ML-Specific Tests**: Model determinism, gradient flow, physics constraint satisfaction
- **E2E Tests**: Full workflow from data upload to prediction visualization

## Tools
- pytest (Python tests)
- Jest + React Testing Library (frontend)
- Playwright (E2E)

## Code Location
- `tests/unit/` — Unit tests
- `tests/integration/` — Integration tests
- `tests/ml/` — ML-specific tests

## Key Principle
Every CAE parser must have tests with sample data from the corresponding tool.
