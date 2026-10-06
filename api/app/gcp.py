"""Cloud Storage implementation of LabelStorage.

On Cloud Run the service account has no private key, so V4 signing goes through the IAM
signBlob API using the runtime access token. The service account needs
roles/iam.serviceAccountTokenCreator on itself (see infra/main.tf).
"""

from datetime import timedelta

import google.auth
from google.auth.transport.requests import Request
from google.cloud import storage

from .storage import ObjectNotFound, StorageError, validate_object_name


class GcsStorage:
    def __init__(self, bucket: str, signed_url_minutes: int) -> None:
        self._credentials, project = google.auth.default()
        self._client = storage.Client(project=project, credentials=self._credentials)
        self._bucket = self._client.bucket(bucket)
        self._expiry = timedelta(minutes=signed_url_minutes)

    def upload_url(self, object_name: str, content_type: str) -> str:
        blob = self._bucket.blob(validate_object_name(object_name))
        self._credentials.refresh(Request())
        url: str = blob.generate_signed_url(
            version="v4",
            expiration=self._expiry,
            method="PUT",
            content_type=content_type,
            service_account_email=getattr(self._credentials, "service_account_email", None),
            access_token=self._credentials.token,
        )
        return url

    def read(self, object_name: str, max_bytes: int) -> bytes:
        blob = self._bucket.get_blob(validate_object_name(object_name))
        if blob is None:
            raise ObjectNotFound(object_name)
        if blob.size is not None and blob.size > max_bytes:
            raise StorageError("label image is too large")
        data: bytes = blob.download_as_bytes()
        return data
