from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile

from src.backend.api.upload_limits import read_upload_limited
from src.backend.api.v1 import dd_laminate


@pytest.mark.asyncio
async def test_upload_limit_accepts_content_at_limit() -> None:
    upload = UploadFile(filename="curve.csv", file=BytesIO(b"1234"))

    content = await read_upload_limited(upload, max_bytes=4)

    assert content == b"1234"


@pytest.mark.asyncio
async def test_upload_limit_rejects_oversized_content() -> None:
    upload = UploadFile(filename="curve.csv", file=BytesIO(b"12345"))

    with pytest.raises(HTTPException) as exc_info:
        await read_upload_limited(upload, max_bytes=4)

    assert exc_info.value.status_code == 413
    assert "upload limit" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_curve_batch_accepts_more_than_300_files(monkeypatch) -> None:
    monkeypatch.setattr(
        dd_laminate,
        "_ensure_available",
        lambda _key, _registry: {"label": "Test curve model", "path": "unused.joblib"},
    )
    monkeypatch.setattr(dd_laminate, "_model_path", lambda _meta: Path("unused.joblib"))
    monkeypatch.setattr(
        dd_laminate,
        "_predict_curve_csv_path",
        lambda **_kwargs: {
            "predicted_type": 1,
            "probabilities": {"type1": 0.8, "type2": 0.1, "type3": 0.1},
        },
    )
    files = [
        UploadFile(
            filename=f"force_disp_Test_{index:03d}.csv",
            file=BytesIO(b"displacement,force\n0,0\n1,1\n"),
        )
        for index in range(1, 302)
    ]

    result = await dd_laminate.predict_from_curve_batch(
        files=files,
        metadata_file=None,
        theta1=30.0,
        theta2=-30.0,
        pt=1000.0,
        case="Case3",
        model="curve_classical",
    )

    assert result.total_files == 301
    assert result.ok_count == 301
    assert result.error_count == 0
