# DD Laminate iOS MVP API Contract

This document defines the first native iOS integration slice for the KyulAI DD Laminate
predictor. The iPhone app should call the server-side FastAPI endpoints and should not
embed the Python ML models or model artifacts.

## MVP server entrypoint

Use the DB-free DD Laminate app for the first iPhone MVP:

```bash
uvicorn src.backend.dd_laminate_app:app --host 0.0.0.0 --port 8000
```

Why this entrypoint:

- It exposes the DD Laminate API at `/api/v1/dd-laminate`.
- It avoids the main platform app startup path that requires PostgreSQL readiness.
- It matches the contract already used by the browser UI.

For a physical iPhone, do not use `localhost` as the app base URL. Use one of:

- the Mac's same-LAN IP, for quick local testing;
- an HTTPS tunnel, for demo/TestFlight-like testing;
- a deployed HTTPS host, for repeated pilot testing.

## Base URL

Swift clients should keep the base URL configurable, for example:

```text
http://<mac-lan-ip>:8000
https://<demo-tunnel-host>
https://<staging-api-host>
```

The endpoint paths below are relative to that base URL.

## Health and readiness checks

### `GET /health`

Expected successful response:

```json
{"status":"ok"}
```

### `GET /api/v1/dd-laminate/models`

Use this before enabling the prediction form. The MVP response model is available when the
`response_models` list contains `key: "response_surrogate"` with `available: true`.

## MVP prediction endpoint

### `POST /api/v1/dd-laminate/predict/response`

Use this endpoint for the first native iPhone prediction flow because it is JSON-only and returns
all values needed for the initial result screen.

Request:

```json
{
  "theta1": 30,
  "theta2": -30,
  "case": "Case2",
  "model": "response_surrogate"
}
```

Field constraints:

| Field | Type | Constraint |
| --- | --- | --- |
| `theta1` | number | `-90 <= theta1 <= 90` |
| `theta2` | number | `-90 <= theta2 <= 90` |
| `case` | string | `Case2`, `Case3`, or `Case4` |
| `model` | string | exactly `response_surrogate` for the iPhone MVP |

Response fields consumed by iOS:

| Field | Purpose |
| --- | --- |
| `predicted_type` | Type badge on result screen |
| `confidence` | Primary confidence value; may be null for models without probabilities |
| `probabilities` | Optional class probabilities |
| `model_key`, `model_label` | Result provenance |
| `input_mode` | Should be `response` for this MVP endpoint |
| `inputs` | Echoed input summary |
| `notes` | User-visible caution/warning strings |
| `predicted_pt` | Predicted Pt metric |
| `predicted_max_displacement` | Result metric |
| `predicted_max_force` | Result metric |
| `curve` | Force-displacement chart points: `{displacement, force}` |
| `metrics` | Model/evaluation metadata when available |

A stable request/response fixture is stored at:

```text
tests/fixtures/dd_laminate/predict_response_case2.json
```

Use it for Swift `Codable` decode tests and UI preview data.

## Native DTO notes

Swift clients can model the MVP request with `Codable`:

```swift
struct DDLaminateResponseRequest: Codable {
    let theta1: Double
    let theta2: Double
    let `case`: String
    let model: String
}
```

The response curve should be decoded as an ordered list and rendered directly as chart input.

## Error handling

The MVP should handle these cases:

- network offline or unreachable base URL;
- `/models` returns no available `response_surrogate` model;
- validation error, such as theta values outside `[-90, 90]`;
- server-side prediction error (`4xx`/`5xx`).

FastAPI validation errors currently return a JSON body with a `detail` field. The iOS app should
show a generic user-friendly message and keep the raw `detail` only for diagnostics/logging.

## Deferred endpoints

These endpoints exist but are not part of the first iPhone MVP:

- `POST /api/v1/dd-laminate/predict/theta` — useful as a lightweight follow-up screen.
- `POST /api/v1/dd-laminate/predict/curve` — defer because CSV file selection/upload adds mobile UX complexity.
