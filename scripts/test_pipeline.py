#!/usr/bin/env python
"""
Test script for the CiteCast pipeline.
Runs the full pipeline on a sample document.
"""

import os
import sys
import json
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.pipeline import CiteCastPipeline
from app.utils.config import Config

def main():
    """Test the full pipeline."""
    
    # Find a sample PDF
    test_data_dir = Path("test_data")
    if not test_data_dir.exists():
        print("❌ test_data/ directory not found.")
        print("Please place a sample PDF in test_data/")
        return
    
    pdf_files = list(test_data_dir.glob("*.pdf"))
    if not pdf_files:
        print("❌ No PDF files found in test_data/")
        return
    
    pdf_path = str(pdf_files[0])
    print(f"📄 Using document: {pdf_path}")
    
    # Initialize the pipeline
    print("\n🚀 Initializing CiteCast Pipeline...")
    pipeline = CiteCastPipeline()
    
    # Test different audiences
    audiences = ["executive", "engineer", "student"]
    
    for audience in audiences:
        print(f"\n📝 Processing for audience: {audience}")
        
        # Create a job
        job_id = pipeline.create_job(pdf_path, audience=audience, num_scenes=3)
        print(f"  Job ID: {job_id}")
        
        # Run the pipeline
        try:
            start_time = time.time()
            result = pipeline.run_pipeline(job_id)
            elapsed = time.time() - start_time
            
            print(f"\n✅ Pipeline completed in {elapsed:.2f}s")
            print(f"  Total Scenes: {result['total_scenes']}")
            print(f"  Total Citations: {result['total_citations']}")
            print(f"  Manifest URL: {result['manifest_url']}")
            
            # Get detailed status
            status = pipeline.get_job_status(job_id)
            if status:
                print(f"  Status: {status['status']}")
                
        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            status = pipeline.get_job_status(job_id)
            if status:
                print(f"  Error: {status.get('error', 'Unknown error')}")
    
    print("\n🎉 Pipeline tests complete!")

if __name__ == "__main__":
    main()