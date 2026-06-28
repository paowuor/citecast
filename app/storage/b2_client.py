import json
import io
from typing import Optional, Dict, Any

from genblaze_core import ObjectStorageSink, KeyStrategy
from genblaze_s3 import S3StorageBackend

from app.utils.config import Config
from app.utils.logging import get_logger

logger = get_logger(__name__)


class B2StorageClient:
    """Manages interactions with Backblaze B2 storage."""
    
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or Config.B2_BUCKET_NAME
        self.sink = ObjectStorageSink(
            S3StorageBackend.for_backblaze(self.bucket_name),
            key_strategy=KeyStrategy.HIERARCHICAL,
        )
        logger.info(f"Initialized B2StorageClient with bucket: {self.bucket_name}")
    
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