#!/usr/bin/env python
"""
Upload a sample PDF to B2 for testing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.b2_client import B2StorageClient

def main():
    """Upload a sample PDF to B2."""
    
    # Look for PDF in test_data
    test_data_dir = Path("test_data")
    test_data_dir.mkdir(exist_ok=True)
    
    pdf_files = list(test_data_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No PDF files found in test_data/")
        return
    
    pdf_path = pdf_files[0]
    print(f"📤 Uploading: {pdf_path}")
    
    client = B2StorageClient()
    
    # Upload to B2 with a clean path
    remote_path = f"raw-documents/{pdf_path.name}"
    client.upload_file(str(pdf_path), remote_path, content_type="application/pdf")
    
    print(f"✅ Uploaded to: {remote_path}")

if __name__ == "__main__":
    main()