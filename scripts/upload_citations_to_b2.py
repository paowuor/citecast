#!/usr/bin/env python
"""
Upload citation manifests to B2 storage.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.storage.b2_client import B2StorageClient

def main():
    """Upload citation manifests to B2."""
    
    citation_dir = Path("citation_output")
    if not citation_dir.exists():
        print("❌ citation_output/ directory not found.")
        print("Please run test_citation_manager.py first.")
        return
    
    json_files = list(citation_dir.glob("*_citations.json"))
    
    if not json_files:
        print("❌ No citation manifests found in citation_output/")
        return
    
    client = B2StorageClient()
    
    for json_path in json_files:
        print(f"📤 Uploading: {json_path}")
        
        remote_path = f"citation-manifests/{json_path.name}"
        
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        client.upload_json(data, remote_path)
        print(f"✅ Uploaded to: {remote_path}")

if __name__ == "__main__":
    main()