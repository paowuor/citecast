#!/usr/bin/env python
"""
Test script for the Citation Manager.
Generates citations for a processed document using sample claims.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.citation_manager import CitationManager, create_citations_for_document

def get_sample_claims_from_document(processed_doc_path: str, num_claims: int = 5) -> list:
    """
    Extract sample claims from a processed document.
    Uses the actual document content to generate realistic claims.
    """
    with open(processed_doc_path, 'r') as f:
        data = json.load(f)
    
    chunks = data['chunks']
    claims = []
    
    # Create claims from the first few chunks
    for i, chunk in enumerate(chunks[:num_claims]):
        text = chunk['text']
        # Take the first sentence or two as the claim
        sentences = text.split('. ')
        claim_text = '. '.join(sentences[:2]) + '.' if len(sentences) > 1 else text[:150]
        
        claims.append({
            "text": claim_text,
            "visual_prompt": f"Create a visual illustrating: {claim_text[:100]}",
            "audio_script": f"Voiceover: {claim_text}"
        })
    
    return claims

def main():
    """Test the citation manager on a processed document."""
    
    # Find processed document
    processed_data_dir = Path("processed_data")
    if not processed_data_dir.exists():
        print("❌ processed_data/ directory not found.")
        print("Please run test_document_processor.py first.")
        return
    
    json_files = list(processed_data_dir.glob("*_processed.json"))
    
    if not json_files:
        print("❌ No processed documents found in processed_data/.")
        print("Please run test_document_processor.py first.")
        return
    
    processed_doc_path = json_files[0]
    print(f"📄 Using processed document: {processed_doc_path}")
    
    # Get sample claims from the document
    claims_data = get_sample_claims_from_document(str(processed_doc_path))
    
    print(f"\n📝 Generated {len(claims_data)} sample claims:")
    for i, claim in enumerate(claims_data[:3]):
        print(f"  {i+1}. {claim['text'][:100]}...")
    
    # Generate citations
    print("\n🔍 Generating citations...")
    manifest = create_citations_for_document(
        str(processed_doc_path),
        claims_data,
        output_dir="citation_output",
        top_k=3
    )
    
    # Print results
    print("\n📊 Citation Results:")
    print(f"  - Total Claims: {manifest['total_claims']}")
    print(f"  - Total Citations: {manifest['statistics']['total_citations']}")
    print(f"  - Confidence Distribution: {manifest['statistics']['confidence_distribution']}")
    print(f"  - Coverage: {manifest['validation']['coverage']:.1%}")
    
    print("\n📑 Sample Citations:")
    for i, claim in enumerate(manifest['claims'][:3]):
        print(f"\n  Claim {i+1}: {claim['text'][:80]}...")
        for j, citation in enumerate(claim['citations'][:2]):
            print(f"    Citation {j+1}: Page {citation['page']} (confidence: {citation['confidence_level']})")
            print(f"      Preview: {citation['text_preview'][:80]}...")
    
    print(f"\n💾 Saved manifest to: citation_output/{manifest['document']['filename'].replace('.pdf', '_citations.json')}")
    print("\n✅ Citation generation complete!")

if __name__ == "__main__":
    main()