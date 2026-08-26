"""StorageService — MinIO / S3 object storage abstraction.

Phase 1 stub: method signatures and docstrings are complete; the
MinIO SDK calls are marked with TODO. The interface is intentionally
stable so route handlers and Celery tasks can depend on it now.
"""

from pathlib import PurePosixPath

from src.backend.config import get_settings

_settings = get_settings()


class StorageService:
    """Wraps MinIO (S3-compatible) object storage operations.

    One instance per request (or task) — lightweight, no connection pooling
    needed since MinIO SDK manages connections internally.
    """

    def __init__(self) -> None:
        # TODO: instantiate minio.Minio client
        # self._client = Minio(
        #     _settings.minio_endpoint,
        #     access_key=_settings.minio_access_key,
        #     secret_key=_settings.minio_secret_key,
        #     secure=_settings.minio_secure,
        # )
        self._dataset_bucket = _settings.minio_bucket_datasets
        self._model_bucket = _settings.minio_bucket_models
        self._results_bucket = _settings.minio_bucket_results

    # ── Datasets ──────────────────────────────────────────────────────────────

    def dataset_object_key(self, dataset_id: str, filename: str) -> str:
        return str(PurePosixPath("datasets") / dataset_id / filename)

    async def upload_dataset(self, dataset_id: str, filename: str, data: bytes) -> tuple[str, int]:
        """Upload a CAE file. Returns (object_key, size_bytes).

        TODO: implement with Minio.put_object / presigned URL flow.
        """
        raise NotImplementedError("StorageService.upload_dataset not yet implemented")

    async def download_dataset(self, object_key: str) -> bytes:
        """Download a CAE file by object key.

        TODO: implement with Minio.get_object.
        """
        raise NotImplementedError("StorageService.download_dataset not yet implemented")

    async def generate_upload_url(
        self, dataset_id: str, filename: str, expires_s: int = 3600
    ) -> str:
        """Generate a presigned PUT URL for direct browser-to-MinIO upload.

        TODO: implement with Minio.presigned_put_object.
        """
        raise NotImplementedError("StorageService.generate_upload_url not yet implemented")

    # ── Model weights ─────────────────────────────────────────────────────────

    def model_weights_key(self, model_id: str, version: str) -> str:
        return str(PurePosixPath("models") / model_id / f"{version}.pt")

    async def upload_model_weights(
        self, model_id: str, version: str, data: bytes
    ) -> tuple[str, int]:
        """Upload model checkpoint. Returns (object_key, size_bytes).

        TODO: implement with Minio.put_object.
        """
        raise NotImplementedError("StorageService.upload_model_weights not yet implemented")

    async def download_model_weights(self, object_key: str) -> bytes:
        """Download model checkpoint for inference.

        TODO: implement with Minio.get_object.
        """
        raise NotImplementedError("StorageService.download_model_weights not yet implemented")

    # ── Prediction results ────────────────────────────────────────────────────

    def prediction_result_key(self, prediction_id: str) -> str:
        return str(PurePosixPath("predictions") / f"{prediction_id}.h5")

    async def upload_prediction_result(self, prediction_id: str, data: bytes) -> str:
        """Upload prediction output HDF5 file. Returns object_key.

        TODO: implement with Minio.put_object.
        """
        raise NotImplementedError("StorageService.upload_prediction_result not yet implemented")

    async def generate_result_download_url(self, object_key: str, expires_s: int = 3600) -> str:
        """Generate a presigned GET URL for prediction result download.

        TODO: implement with Minio.presigned_get_object.
        """
        raise NotImplementedError("StorageService.generate_result_download_url not yet implemented")

    # ── Bucket management ─────────────────────────────────────────────────────

    async def ensure_buckets_exist(self) -> None:
        """Create required buckets if they don't exist. Called at app startup.

        TODO: implement with Minio.bucket_exists / Minio.make_bucket.
        """
        raise NotImplementedError("StorageService.ensure_buckets_exist not yet implemented")
