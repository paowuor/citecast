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
        try:
            from genblaze_gmicloud import GMIProvider
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
        except ImportError as e:
            logger.warning(f"GMI Cloud providers not available: {e}")
    
    # Fallback to OpenAI
    if Config.OPENAI_API_KEY:
        try:
            from genblaze_openai import OpenAIProvider
            providers.update({
                "openai": OpenAIProvider(
                    model="gpt-4-turbo-preview",
                    api_key=Config.OPENAI_API_KEY
                )
            })
            logger.info("Configured OpenAI provider")
        except ImportError as e:
            logger.warning(f"OpenAI provider not available: {e}")
    
    # Fallback to Google Gemini
    if Config.GEMINI_API_KEY:
        try:
            from genblaze_google import GeminiProvider
            providers.update({
                "gemini": GeminiProvider(
                    model="gemini-1.5-pro",
                    api_key=Config.GEMINI_API_KEY
                )
            })
            logger.info("Configured Gemini provider")
        except ImportError as e:
            logger.warning(f"Gemini provider not available: {e}")
    
    return providers


def get_storage_sink(bucket: str = None) -> Sinks.ObjectStorageSink:
    """
    Get a configured storage sink for Backblaze B2.
    """
    bucket = bucket or Config.B2_BUCKET_NAME
    
    if not bucket:
        logger.error("No B2 bucket configured")
        raise ValueError("B2 bucket name is required")
    
    try:
        backend = S3StorageBackend.for_backblaze(bucket)
        return Sinks.ObjectStorageSink(
            backend=backend,
            key_strategy=KeyStrategy.HIERARCHICAL
        )
    except Exception as e:
        logger.error(f"Failed to create storage sink: {e}")
        raise


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


def get_available_providers() -> list:
    """
    Get a list of available providers for the user interface.
    """
    available = []
    
    if Config.GMI_API_KEY:
        available.extend([
            {"id": "gmi_text", "name": "GMI Cloud - Llama 3", "type": "text"},
            {"id": "gmi_image", "name": "GMI Cloud - Seedream", "type": "image"},
            {"id": "gmi_audio", "name": "GMI Cloud - ElevenLabs", "type": "audio"}
        ])
    
    if Config.OPENAI_API_KEY:
        available.append({"id": "openai", "name": "OpenAI - GPT-4", "type": "text"})
    
    if Config.GEMINI_API_KEY:
        available.append({"id": "gemini", "name": "Google - Gemini 1.5", "type": "text"})
    
    return available