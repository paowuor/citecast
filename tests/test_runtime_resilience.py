from app.core.document_processor import DocumentProcessor
from app.core.citation_manager import CitationManager
from app.core.pipeline import CiteCastPipeline


def test_document_processor_initializes_without_optional_dependencies():
    processor = DocumentProcessor()

    assert processor.embedding_model is not None
    assert processor.text_splitter is not None


def test_citation_manager_initializes_without_optional_dependencies():
    manager = CitationManager()

    assert manager.embedding_model is not None


def test_pipeline_initializes_without_genblaze_sdk():
    pipeline = CiteCastPipeline(b2_bucket="demo-bucket")

    assert pipeline.b2_bucket == "demo-bucket"
    assert pipeline.active_jobs == {}
