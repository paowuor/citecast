"""
Genblaze configuration for CiteCast.
Provides configured provider instances and pipeline helpers.
"""

from genblaze_core import Pipeline, PipelineConfig, Step, Sinks, KeyStrategy
from genblaze_s3 import S3StorageBackend
from genblaze_gmicloud import GMIProvider
from genblaze_openai import OpenAIProvider

from app.utils.config import Config
from app.utils.logging import get_logger

logger = get_logger(__name__)


def get_providers(use_gmi: bool = True) -> dict:
    """
    Get configured provider instances.
    
    Args:
        use_gmi: Whether to use GMI Cloud (preferred) or fallback
    
    Returns:
        Dictionary of provider instances
    """
    providers = {}
    
    # GMI Cloud providers (preferred for hackathon)
    if use_gmi and Config.GMI_API_KEY:
        providers.update({
            "gmi_text": GMIProvider(
                model="gmi-cloud/llama-3-70b",
                api_key=Config.GMI_API_KEY
            ),
            "gmi_image": GMIProvider(
                model="gmi-cloud/seedream-v1",
                api_key=Config.GMI_API_KEY
            ),
            "gmi_audio": GMIProvider(
                model="gmi-cloud/elevenlabs-v2",
                api_key=Config.GMI_API_KEY
            )
        })
        logger.info("Configured GMI Cloud providers")
    
    # Fallback to OpenAI
    if Config.OPENAI_API_KEY:
        providers.update({
            "openai": OpenAIProvider(
                model="gpt-4-turbo-preview",
                api_key=Config.OPENAI_API_KEY
            )
        })
        logger.info("Configured OpenAI provider")
    
    return providers


def get_storage_sink(bucket: str = None) -> Sinks.ObjectStorageSink:
    """
    Get a configured storage sink for Backblaze B2.
    """
    bucket = bucket or Config.B2_BUCKET_NAME
    
    return Sinks.ObjectStorageSink(
        backend=S3StorageBackend.for_backblaze(bucket),
        key_strategy=KeyStrategy.HIERARCHICAL
    )


def create_pipeline_config() -> PipelineConfig:
    """
    Create a configured pipeline config.
    """
    return PipelineConfig(
        name="citecast_pipeline",
        retry_on_failure=True,
        max_retries=3,
        parallel_execution=True,
        max_parallel_steps=10,
        timeout_seconds=300
    )