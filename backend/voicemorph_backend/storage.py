"""Object storage abstraction: local filesystem (dev) or S3/MinIO (production).

Models and job artifacts are addressed by key (e.g. ``voices/<id>/model.pth``,
``jobs/<id>/output.mp4``). The API and workers share the same storage so a
worker can persist a result and the API can serve it.
"""

from __future__ import annotations

import abc
import shutil
from pathlib import Path

from voicemorph_backend.settings import Settings


class Storage(abc.ABC):
    @abc.abstractmethod
    def put_file(self, key: str, path: Path) -> None: ...

    @abc.abstractmethod
    def get_file(self, key: str, dest: Path) -> Path: ...

    @abc.abstractmethod
    def exists(self, key: str) -> bool: ...

    @abc.abstractmethod
    def local_path(self, key: str) -> Path:
        """A concrete local path for ``key`` (downloading from S3 if needed)."""


class LocalStorage(Storage):
    """Filesystem-backed storage rooted at ``root``."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _p(self, key: str) -> Path:
        p = self.root / key
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def put_file(self, key: str, path: Path) -> None:
        dest = self._p(key)
        if Path(path).resolve() != dest.resolve():
            shutil.copyfile(path, dest)

    def get_file(self, key: str, dest: Path) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self._p(key), dest)
        return dest

    def exists(self, key: str) -> bool:
        return self._p(key).exists()

    def local_path(self, key: str) -> Path:
        return self._p(key)


class S3Storage(Storage):
    """S3/MinIO-backed storage via boto3.

    Files are cached locally under ``cache_root`` so the engine (which works on
    local paths) always has a concrete file to read.
    """

    def __init__(self, settings: Settings, cache_root: Path):
        import boto3

        self.bucket = settings.s3_bucket
        self.cache_root = Path(cache_root)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except Exception:
            self._client.create_bucket(Bucket=self.bucket)

    def put_file(self, key: str, path: Path) -> None:
        self._client.upload_file(str(path), self.bucket, key)

    def get_file(self, key: str, dest: Path) -> Path:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        self._client.download_file(self.bucket, key, str(dest))
        return dest

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def local_path(self, key: str) -> Path:
        cached = self.cache_root / key
        if not cached.exists():
            self.get_file(key, cached)
        return cached


def build_storage(settings: Settings) -> Storage:
    if settings.storage_backend == "s3":
        return S3Storage(settings, cache_root=settings.storage_root / "cache")
    return LocalStorage(settings.storage_root / "objects")
