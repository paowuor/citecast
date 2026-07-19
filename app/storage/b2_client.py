import json
import io
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from genblaze_core import ObjectStorageSink, KeyStrategy
    from genblaze_s3 import S3StorageBackend
except ImportError:  # pragma: no cover - optional dependency fallback
    class KeyStrategy:
        HIERARCHICAL = "hierarchical"

    class S3StorageBackend:
        @staticmethod
        def for_backblaze(bucket_name: str):
            return bucket_name

    class ObjectStorageSink:
        def __init__(self, backend, key_strategy=None):
            self.backend = backend
            self.key_strategy = key_strategy
            self.base_dir = Path(__file__).resolve().parents[2] / ".b2_storage"
            self.base_dir.mkdir(exist_ok=True)

        def write(self, path: str, content: Any, content_type: Optional[str] = None):
            target = self.base_dir / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, str):
                target.write_text(content, encoding="utf-8")
            else:
                target.write_bytes(content)

        def read(self, path: str):
            target = self.base_dir / path
            if not target.exists():
                raise FileNotFoundError(path)
            return target.read_text(encoding="utf-8")

        def list(self, prefix: str = ""):
            if not prefix:
                return [p.relative_to(self.base_dir).as_posix() for p in self.base_dir.rglob("*") if p.is_file()]
            return [p.relative_to(self.base_dir).as_posix() for p in self.base_dir.rglob("*") if p.is_file() and str(p).startswith(str(self.base_dir / prefix))]


class LocalObjectStorageSink:
    """Simple local filesystem sink used when B2 is unavailable."""

    def __init__(self, bucket_name: str, key_strategy=None):
        self.bucket_name = bucket_name
        self.key_strategy = key_strategy
        self.base_dir = Path(__file__).resolve().parents[2] / ".b2_storage" / bucket_name
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write(self, path: str, content: Any, content_type: Optional[str] = None):
        target = self.base_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            target.write_text(content, encoding="utf-8")
        else:
            target.write_bytes(content)

    def read(self, path: str):
        target = self.base_dir / path
        if not target.exists():
            raise FileNotFoundError(path)
        return target.read_text(encoding="utf-8")

    def list(self, prefix: str = ""):
        if not prefix:
            return [p.relative_to(self.base_dir).as_posix() for p in self.base_dir.rglob("*") if p.is_file()]
        return [p.relative_to(self.base_dir).as_posix() for p in self.base_dir.rglob("*") if p.is_file() and str(p).startswith(str(self.base_dir / prefix))]

from app.utils.config import Config
from app.utils.logging import get_logger

logger = get_logger(__name__)


class B2StorageClient:
    """Manages interactions with Backblaze B2 storage."""
    
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or Config.B2_BUCKET_NAME or "local-bucket"
        self.sink = self._create_sink(self.bucket_name)
        logger.info(f"Initialized B2StorageClient with bucket: {self.bucket_name}")

    def _create_sink(self, bucket_name: str):
        credentials_available = bool(Config.B2_KEY_ID and Config.B2_APP_KEY)
        if not credentials_available:
            logger.info("B2 credentials not configured; using local filesystem storage")
            return LocalObjectStorageSink(bucket_name, key_strategy=KeyStrategy.HIERARCHICAL)

        try:
            backend = S3StorageBackend.for_backblaze(bucket_name)
            return ObjectStorageSink(backend, key_strategy=KeyStrategy.HIERARCHICAL)
        except Exception as exc:  # pragma: no cover - fallback for offline/dev environments
            logger.warning("Falling back to local filesystem storage because B2 initialization failed: %s", exc)
            return LocalObjectStorageSink(bucket_name, key_strategy=KeyStrategy.HIERARCHICAL)
    
    def upload_json(self, data: Dict[str, Any], path: str, content_type: str = "application/json"):
        """Upload JSON data to B2."""
        json_str = json.dumps(data, indent=2)
        self.sink.write(
            path=path,
            content=json_str,
            content_type=content_type
        )
        logger.info(f"Uploaded JSON to B2: {path}")
    
    def upload_file(self, file_path: str, path: str, content_type: Optional[str] = None):
        """Upload a local file to B2."""
        with open(file_path, 'rb') as f:
            content = f.read()
            self.sink.write(
                path=path,
                content=content,
                content_type=content_type
            )
        logger.info(f"Uploaded file to B2: {path}")
    
    def download_json(self, path: str) -> Dict[str, Any]:
        """Download and parse JSON from B2."""
        content = self.sink.read(path)
        data = json.loads(content)
        logger.info(f"Downloaded JSON from B2: {path}")
        return data
    
    def download_file(self, path: str, output_path: str):
        """Download a file from B2."""
        content = self.sink.read(path)
        with open(output_path, 'wb') as f:
            f.write(content)
        logger.info(f"Downloaded file from B2: {path} -> {output_path}")
    
    def list_files(self, prefix: str) -> list:
        """List files in B2 with a given prefix."""
        return list(self.sink.list(prefix=prefix))