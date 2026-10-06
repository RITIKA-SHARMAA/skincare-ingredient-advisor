"""Label image storage: signed Cloud Storage URLs in GCP, a local directory in development."""

import re
import uuid
from pathlib import Path
from typing import Protocol

from .config import Settings

EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MIME_BY_EXTENSION = {ext: mime for mime, ext in EXTENSIONS.items()}
OBJECT_NAME = re.compile(r"^labels/[0-9a-f]{32}\.(jpg|png|webp)$")


class StorageError(Exception):
    pass


class ObjectNotFound(StorageError):
    pass


class LabelStorage(Protocol):
    def upload_url(self, object_name: str, content_type: str) -> str: ...

    def read(self, object_name: str, max_bytes: int) -> bytes: ...


def new_object_name(content_type: str) -> str:
    return f"labels/{uuid.uuid4().hex}.{EXTENSIONS[content_type]}"


def validate_object_name(object_name: str) -> str:
    """Reject anything that is not a name this service generated (no path traversal)."""
    if not OBJECT_NAME.match(object_name):
        raise ObjectNotFound(object_name)
    return object_name


def mime_type_for(object_name: str) -> str:
    return MIME_BY_EXTENSION[object_name.rsplit(".", 1)[1]]


class LocalStorage:
    """Development stand-in: the 'signed URL' points back at this API's own PUT endpoint."""

    def __init__(self, root: str, public_base_url: str) -> None:
        self.root = Path(root)
        self.public_base_url = public_base_url.rstrip("/")

    def _path(self, object_name: str) -> Path:
        return self.root / validate_object_name(object_name)

    def upload_url(self, object_name: str, content_type: str) -> str:
        return f"{self.public_base_url}/labels/local/{object_name.removeprefix('labels/')}"

    def write(self, object_name: str, data: bytes) -> None:
        path = self._path(object_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, object_name: str, max_bytes: int) -> bytes:
        path = self._path(object_name)
        if not path.is_file():
            raise ObjectNotFound(object_name)
        if path.stat().st_size > max_bytes:
            raise StorageError("label image is too large")
        return path.read_bytes()


def build_storage(settings: Settings) -> LabelStorage:
    if settings.storage_backend == "gcs":
        from .gcp import GcsStorage

        return GcsStorage(settings.storage_bucket, settings.signed_url_minutes)
    return LocalStorage(settings.storage_root, settings.public_api_base_url)
