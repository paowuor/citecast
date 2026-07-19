"""
Unit tests for the Genblaze Pipeline.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.core.pipeline import CiteCastPipeline, PipelineJob


class TestCiteCastPipeline:
    """Test the CiteCast pipeline."""
    
    @pytest.fixture
    def pipeline(self):
        return CiteCastPipeline()
    
    def test_create_job(self, pipeline):
        """Test job creation."""
        job_id = pipeline.create_job(
            document_path="test_data/sample.pdf",
            audience="executive",
            num_scenes=5
        )
        
        assert job_id in pipeline.active_jobs
        job = pipeline.active_jobs[job_id]
        assert job.status == "pending"
        assert job.audience == "executive"
        assert job.document_path == "test_data/sample.pdf"
    
    def test_get_job_status(self, pipeline):
        """Test getting job status."""
        job_id = pipeline.create_job("test.pdf", "executive")
        status = pipeline.get_job_status(job_id)
        
        assert status is not None
        assert status["job_id"] == job_id
        assert status["status"] == "pending"
    
    @patch('app.core.pipeline.DocumentProcessor')
    @patch('app.core.pipeline.CitationManager')
    def test_run_pipeline_success(self, mock_citation, mock_doc, pipeline):
        """Test successful pipeline run."""
        # Setup mocks
        mock_doc.return_value.process_document.return_value = {
            "metadata": {"filename": "test.pdf", "total_pages": 5},
            "chunks": [
                {"chunk_id": "chunk_0000", "text": "Test chunk 1", "page": 1, "char_start": 0, "char_end": 50}
            ]
        }
        
        # Create job
        job_id = pipeline.create_job("test.pdf", "executive")
        
        # Mock pipeline run
        with patch.object(pipeline, '_generate_audience_summary') as mock_summary:
            mock_summary.return_value = {
                "claims": [
                    {"text": "Claim 1", "visual_prompt": "Image 1", "audio_script": "Audio 1"}
                ]
            }
            
            with patch.object(pipeline, '_generate_citations') as mock_citations:
                mock_citations.return_value = []
                
                with patch.object(pipeline, '_generate_media') as mock_media:
                    mock_media.return_value = {"scenes": [], "images": [], "audio": []}
                    
                    with patch.object(pipeline, '_build_final_manifest') as mock_manifest:
                        mock_manifest.return_value = {"scenes": []}
                        
                        result = pipeline.run_pipeline(job_id)
                        
                        assert result["job_id"] == job_id
                        assert result["status"] == "completed"