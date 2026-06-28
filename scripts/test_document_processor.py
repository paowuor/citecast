#!/usr/bin/env python
"""
Test script for the Document Processor.
Place a sample PDF in the test_data directory and run this script.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.document_processor import DocumentProcessor, process_sample_document

def main():
    """Test the document processor on a sample PDF."""
    
    # Create test data directory
    test_data_dir = Path("test_data")
    test_data_dir.mkdir(exist_ok=True)
    
    # Check for sample PDF
    pdf_files = list(test_data_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in test_data/ directory.")
        print("Please place a sample PDF in test_data/ and try again.")
        print("\nExample:")
        print("  cp ~/Downloads/sample.pdf test_data/")
        return
    
    pdf_path = pdf_files[0]
    print(f"📄 Processing: {pdf_path}")
    
    # Process the document
    processor = DocumentProcessor()
    result = processor.process_document(str(pdf_path))
    
    # Print results
    print("\n📊 Processing Results:")
    print(f"  - Filename: {result['metadata']['filename']}")
    print(f"  - Pages: {result['metadata']['total_pages']}")
    print(f"  - Chunks: {result['metadata']['total_chunks']}")
    print(f"  - Characters: {result['metadata']['total_chars']}")
    
    print("\n📑 Sample Chunks:")
    for i, chunk in enumerate(result['chunks'][:5]):
        print(f"\n  Chunk {i+1} (Page {chunk['page']}):")
        print(f"  ID: {chunk['chunk_id']}")
        print(f"  Text: {chunk['text_preview']}...")
        print(f"  Section: {chunk.get('section_title', 'N/A')}")
        print(f"  Embedding dims: {len(chunk['embedding'])}")
    
    print(f"\n💾 Saved to: processed_data/{result['metadata']['filename'].replace('.pdf', '_processed.json')}")
    print("\n✅ Document processing complete!")

if __name__ == "__main__":
    main()