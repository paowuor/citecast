import pytest
import json
from pathlib import Path

from app.core.document_processor import DocumentProcessor, TextChunk

class TestDocumentProcessor:
    """Unit tests for the Document Processor."""
    
    @pytest.fixture
    def processor(self):
        return DocumentProcessor()
    
    def test_chunk_creation(self, processor):
        """Test that chunks are created correctly."""
        text = "This is a test document. " * 100
        page_map = [{"page": 1, "start": 0, "end": len(text)}]
        
        chunks = processor.chunk_text(text, page_map)
        
        assert len(chunks) > 1
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)
        assert all(chunk.page == 1 for chunk in chunks)
        assert all(len(chunk.text) > 0 for chunk in chunks)
    
    def test_section_title_extraction(self, processor):
        """Test section title extraction from chunks."""
        chunk_text = "# Introduction\nThis is the introduction."
        title = processor._extract_section_title(chunk_text)
        assert title == "Introduction"
        
        chunk_text = "1. Background\nThis is the background."
        title = processor._extract_section_title(chunk_text)
        assert title == "1. Background"
    
    def test_embedding_generation(self, processor):
        """Test embedding generation."""
        from app.core.document_processor import TextChunk
        
        chunks = [
            TextChunk(
                chunk_id="test_1",
                text="This is a test sentence.",
                page=1,
                char_start=0,
                char_end=20
            )
        ]
        
        processed = processor.generate_embeddings(chunks)
        
        assert len(processed) == 1
        assert processed[0].embedding is not None
        assert len(processed[0].embedding) > 0