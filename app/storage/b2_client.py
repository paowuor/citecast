from genblaze_core import ObjectStorageSink, KeyStrategy
from genblaze_s3 import S3StorageBackend
from app.utils.config import Config

def get_storage_sink():
    """Returns a configured Genblaze storage sink for Backblaze B2."""
    return ObjectStorageSink(
        S3StorageBackend.for_backblaze(Config.B2_BUCKET_NAME),
        key_strategy=KeyStrategy.HIERARCHICAL,
    )