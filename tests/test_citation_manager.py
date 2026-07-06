import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from app.core.citation_manager import (
    CitationManager, 
    Citation, 
    ClaimWithCitations,
    create_citations_for_document
)
from app.core.document_processor import TextChunk


class TestCitationManager:
    """Unit tests for the Citation Manager."""
    
    @pytest.fixture
    def citation_manager(self):
        return CitationManager()
    
    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunks for testing."""
        return [
            TextChunk(
                chunk_id="chunk_0000",
                text="The global economy grew by 3.2% in 2024.",
                page=1,
                char_start=0,
                char_end=45,
                section_title="Economic Overview"
            ),
            TextChunk(
                chunk_id="chunk_0001",
                text="Solar energy adoption increased by 32%.",
                page=2,
                char_start=46,
                char_end=85,
                section_title="Renewable Energy"
            ),
            TextChunk(
                chunk_id="chunk_0002",
                text="AI market is projected to reach $1.8 trillion.",
                page=3,
                char_start=86,
                char_end=128,
                section_title="Technology"
            )
        ]
    
    def test_find_relevant_chunks(self, citation_manager, sample_chunks):
        """Test finding relevant chunks for a claim."""
        # Generate embeddings for chunks
        citation_manager.generate_embeddings(sample_chunks)
        
        # Test claim that matches chunk 0
        claim = "The global economy experienced 3.2% growth."
        results = citation_manager.find_relevant_chunks(claim, sample_chunks, top_k=1)
        
        assert len(results) > 0
        assert results[0][0].chunk_id == "chunk_0000"
        assert results[0][1] >= 0.5  # Should have decent similarity
    
    def test_generate_citations(self, citation_manager, sample_chunks):
        """Test generating citations for a claim."""
        # Generate embeddings for chunks
        citation_manager.generate_embeddings(sample_chunks)
        
        claim = "Solar energy increased by 32% last year."
        citations = citation_manager.generate_citations(claim, sample_chunks, top_k=2)
        
        assert len(citations) > 0
        assert all(isinstance(c, Citation) for c in citations)
        assert all(c.confidence_level in ["high", "medium", "low"] for c in citations)
    
    def test_generate_citations_batch(self, citation_manager, sample_chunks):
        """Test generating citations for multiple claims."""
        # Generate embeddings for chunks
        citation_manager.generate_embeddings(sample_chunks)
        
        claims_data = [
            {"text": "The global economy grew in 2024.", "visual_prompt": "Bar chart showing growth", "audio_script": "Voiceover about growth"},
            {"text": "Solar energy adoption is increasing.", "visual_prompt": "Solar panels graphic", "audio_script": "Voiceover about solar"}
        ]
        
        results = citation_manager.generate_citations_batch(claims_data, sample_chunks, top_k=2)
        
        assert len(results) == 2
        assert all(isinstance(r, ClaimWithCitations) for r in results)
        assert all(len(r.citations) > 0 for r in results)
    
    def test_validate_citations(self, citation_manager):
        """Test citation validation."""
        citations = [
            Citation("chunk_0000", "Test text", 1, 0, 10, 0.8, "high"),
            Citation("chunk_0001", "More text", 2, 11, 20, 0.6, "medium")
        ]
        
        stats = citation_manager.validate_citations(citations)
        
        assert stats["total_citations"] == 2
        assert stats["confidence_distribution"]["high"] == 1
        assert stats["confidence_distribution"]["medium"] == 1
        assert stats["unique_pages"] == [1, 2]
    
    def test_create_citation_manifest(self, citation_manager, sample_chunks):
        """Test creating a complete citation manifest."""
        # Generate embeddings for chunks
        citation_manager.generate_embeddings(sample_chunks)
        
        claims_data = [
            {"text": "The global economy grew.", "visual_prompt": "Economic growth", "audio_script": "Economy voiceover"}
        ]
        
        claims_with_citations = citation_manager.generate_citations_batch(
            claims_data, sample_chunks, top_k=2
        )
        
        metadata = {
            "filename": "test_document.pdf",
            "total_pages": 3,
            "total_chunks": 3
        }
        
        manifest = citation_manager.create_citation_manifest(claims_with_citations, metadata)
        
        assert manifest["total_claims"] == 1
        assert manifest["statistics"]["total_citations"] > 0
        assert "validation" in manifest
        assert manifest["validation"]["is_valid"] == True