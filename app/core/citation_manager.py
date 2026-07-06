import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import re

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app.utils.logging import get_logger
from app.core.document_processor import TextChunk

logger = get_logger(__name__)


@dataclass
class Citation:
    """A single citation linking a claim to a source chunk."""
    chunk_id: str
    text: str
    page: int
    char_start: int
    char_end: int
    similarity_score: float
    confidence_level: str  # "high", "medium", "low"
    section_title: Optional[str] = None
    text_preview: str = ""


@dataclass
class ClaimWithCitations:
    """A generated claim with its supporting citations."""
    claim_id: str
    text: str
    visual_prompt: str
    audio_script: str
    citations: List[Citation]
    scene_number: int
    timestamp_start: float
    timestamp_end: float


class CitationManager:
    """
    Manages citation tracking between generated content and source documents.
    Uses RAG to find the most relevant source chunks for each claim.
    """
    
    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the Citation Manager.
        
        Args:
            embedding_model_name: Name of the sentence transformer model
        """
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.citation_cache = {}
        logger.info(f"Initialized CitationManager with model: {embedding_model_name}")
    
    def load_document_chunks(self, processed_doc_path: str) -> List[TextChunk]:
        """
        Load processed document chunks from a JSON file.
        
        Args:
            processed_doc_path: Path to the processed document JSON
            
        Returns:
            List of TextChunk objects
        """
        with open(processed_doc_path, 'r') as f:
            data = json.load(f)
        
        chunks = []
        for chunk_data in data['chunks']:
            chunk = TextChunk(
                chunk_id=chunk_data['chunk_id'],
                text=chunk_data['text'],
                page=chunk_data['page'],
                char_start=chunk_data['char_start'],
                char_end=chunk_data['char_end'],
                section_title=chunk_data.get('section_title'),
                embedding=chunk_data.get('embedding')
            )
            chunks.append(chunk)
        
        logger.info(f"Loaded {len(chunks)} chunks from {processed_doc_path}")
        return chunks
    
    def load_document_from_b2(self, b2_client, b2_path: str) -> List[TextChunk]:
        """
        Load document chunks directly from B2 storage.
        
        Args:
            b2_client: B2StorageClient instance
            b2_path: Path to the processed document in B2
            
        Returns:
            List of TextChunk objects
        """
        data = b2_client.download_json(b2_path)
        
        chunks = []
        for chunk_data in data['chunks']:
            chunk = TextChunk(
                chunk_id=chunk_data['chunk_id'],
                text=chunk_data['text'],
                page=chunk_data['page'],
                char_start=chunk_data['char_start'],
                char_end=chunk_data['char_end'],
                section_title=chunk_data.get('section_title'),
                embedding=chunk_data.get('embedding')
            )
            chunks.append(chunk)
        
        logger.info(f"Loaded {len(chunks)} chunks from B2: {b2_path}")
        return chunks
    
    def find_relevant_chunks(
        self, 
        claim: str, 
        chunks: List[TextChunk], 
        top_k: int = 3,
        similarity_threshold: float = 0.3
    ) -> List[Tuple[TextChunk, float]]:
        """
        Find the most relevant chunks for a given claim using cosine similarity.
        
        Args:
            claim: The claim text to search for
            chunks: List of document chunks with embeddings
            top_k: Number of top chunks to return
            similarity_threshold: Minimum similarity score to include
            
        Returns:
            List of (chunk, similarity_score) tuples sorted by score descending
        """
        if not chunks:
            logger.warning("No chunks provided for similarity search")
            return []
        
        # Generate embedding for the claim
        claim_embedding = self.embedding_model.encode([claim])[0]
        
        # Get all chunk embeddings
        chunk_embeddings = np.array([chunk.embedding for chunk in chunks if chunk.embedding is not None])
        chunk_indices = [i for i, chunk in enumerate(chunks) if chunk.embedding is not None]
        
        if len(chunk_embeddings) == 0:
            logger.warning("No chunks have embeddings")
            return []
        
        # Compute cosine similarities
        similarities = cosine_similarity([claim_embedding], chunk_embeddings)[0]
        
        # Get top-k indices
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            similarity = similarities[idx]
            if similarity >= similarity_threshold:
                chunk_idx = chunk_indices[idx]
                results.append((chunks[chunk_idx], float(similarity)))
        
        logger.info(f"Found {len(results)} relevant chunks for claim: '{claim[:50]}...'")
        return results
    
    def generate_citations(
        self, 
        claim: str, 
        chunks: List[TextChunk],
        top_k: int = 3,
        include_low_confidence: bool = False
    ) -> List[Citation]:
        """
        Generate citations for a claim by finding the most relevant chunks.
        
        Args:
            claim: The claim text
            chunks: List of document chunks
            top_k: Number of citations to generate
            include_low_confidence: Whether to include low confidence matches
            
        Returns:
            List of Citation objects
        """
        relevant_chunks = self.find_relevant_chunks(claim, chunks, top_k=top_k * 2)
        
        citations = []
        for chunk, score in relevant_chunks[:top_k]:
            # Determine confidence level
            if score >= 0.7:
                confidence = "high"
            elif score >= 0.5:
                confidence = "medium"
            else:
                confidence = "low"
                if not include_low_confidence:
                    continue
            
            citation = Citation(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                page=chunk.page,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                similarity_score=score,
                confidence_level=confidence,
                section_title=chunk.section_title,
                text_preview=chunk.text[:200] + ("..." if len(chunk.text) > 200 else "")
            )
            citations.append(citation)
        
        logger.info(f"Generated {len(citations)} citations for claim: '{claim[:50]}...'")
        return citations
    
    def generate_citations_batch(
        self,
        claims: List[Dict[str, Any]],
        chunks: List[TextChunk],
        top_k: int = 3
    ) -> List[ClaimWithCitations]:
        """
        Generate citations for multiple claims in batch.
        
        Args:
            claims: List of claim dictionaries with 'text', 'visual_prompt', 'audio_script'
            chunks: List of document chunks
            top_k: Number of citations per claim
            
        Returns:
            List of ClaimWithCitations objects
        """
        results = []
        
        for i, claim_data in enumerate(claims):
            claim_text = claim_data.get('text', '')
            
            citations = self.generate_citations(claim_text, chunks, top_k=top_k)
            
            claim_with_citations = ClaimWithCitations(
                claim_id=f"claim_{i:04d}",
                text=claim_text,
                visual_prompt=claim_data.get('visual_prompt', ''),
                audio_script=claim_data.get('audio_script', ''),
                citations=citations,
                scene_number=i,
                timestamp_start=i * 3.0,  # Assume 3 seconds per scene
                timestamp_end=(i + 1) * 3.0
            )
            results.append(claim_with_citations)
        
        logger.info(f"Generated citations for {len(results)} claims")
        return results
    
    def validate_citations(self, citations: List[Citation]) -> Dict[str, Any]:
        """
        Validate citations and return statistics.
        
        Args:
            citations: List of Citation objects
            
        Returns:
            Dict with validation statistics
        """
        if not citations:
            return {
                "total_citations": 0,
                "confidence_distribution": {},
                "unique_pages": [],
                "coverage_score": 0.0
            }
        
        # Count confidence levels
        confidence_counts = defaultdict(int)
        unique_pages = set()
        
        for citation in citations:
            confidence_counts[citation.confidence_level] += 1
            unique_pages.add(citation.page)
        
        # Calculate coverage score (percentage of claims with at least one citation)
        # This is handled at the claim level, not citation level
        
        return {
            "total_citations": len(citations),
            "confidence_distribution": dict(confidence_counts),
            "unique_pages": sorted(list(unique_pages)),
            "average_similarity": np.mean([c.similarity_score for c in citations])
        }
    
    def create_citation_manifest(
        self,
        claims: List[ClaimWithCitations],
        document_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a complete citation manifest for the entire document.
        
        Args:
            claims: List of ClaimWithCitations objects
            document_metadata: Document metadata from the processor
            
        Returns:
            Complete manifest dictionary
        """
        manifest = {
            "document": document_metadata,
            "total_claims": len(claims),
            "claims": [],
            "statistics": {
                "total_citations": 0,
                "citations_per_claim": [],
                "confidence_distribution": defaultdict(int)
            }
        }
        
        for claim in claims:
            claim_dict = {
                "claim_id": claim.claim_id,
                "text": claim.text,
                "visual_prompt": claim.visual_prompt,
                "audio_script": claim.audio_script,
                "scene_number": claim.scene_number,
                "timestamp_start": claim.timestamp_start,
                "timestamp_end": claim.timestamp_end,
                "citations": [asdict(c) for c in claim.citations]
            }
            manifest["claims"].append(claim_dict)
            
            # Update statistics
            manifest["statistics"]["total_citations"] += len(claim.citations)
            manifest["statistics"]["citations_per_claim"].append(len(claim.citations))
            
            for citation in claim.citations:
                manifest["statistics"]["confidence_distribution"][citation.confidence_level] += 1
        
        # Convert defaultdict to dict
        manifest["statistics"]["confidence_distribution"] = dict(
            manifest["statistics"]["confidence_distribution"]
        )
        
        # Add validation summary
        manifest["validation"] = {
            "is_valid": all(len(claim.citations) > 0 for claim in claims),
            "coverage": sum(1 for claim in claims if len(claim.citations) > 0) / len(claims)
        }
        
        logger.info(f"Created citation manifest with {manifest['statistics']['total_citations']} total citations")
        return manifest
    
    def save_manifest(self, manifest: Dict[str, Any], output_path: str):
        """Save the citation manifest to a JSON file."""
        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"Saved citation manifest to: {output_path}")
    
    def load_manifest(self, file_path: str) -> Dict[str, Any]:
        """Load a citation manifest from a JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        logger.info(f"Loaded citation manifest from: {file_path}")
        return data
    
    # Add these methods to the CitationManager class

def find_relevant_chunks_with_context(
    self, 
    claim: str, 
    chunks: List[TextChunk], 
    top_k: int = 3,
    context_window: int = 1
) -> List[Tuple[TextChunk, float, List[TextChunk]]]:
    """
    Find relevant chunks and include surrounding context chunks.
    
    Args:
        claim: The claim text
        chunks: List of document chunks
        top_k: Number of top chunks to return
        context_window: Number of chunks before/after to include as context
        
    Returns:
        List of (chunk, score, [context_chunks]) tuples
    """
    relevant = self.find_relevant_chunks(claim, chunks, top_k=top_k)
    
    results = []
    for chunk, score in relevant:
        # Get the index of this chunk
        try:
            idx = chunks.index(chunk)
        except ValueError:
            results.append((chunk, score, []))
            continue
        
        # Get surrounding chunks
        start_idx = max(0, idx - context_window)
        end_idx = min(len(chunks), idx + context_window + 1)
        context_chunks = chunks[start_idx:end_idx]
        
        results.append((chunk, score, context_chunks))
    
    return results

def generate_citations_with_context(
    self, 
    claim: str, 
    chunks: List[TextChunk],
    top_k: int = 3,
    context_window: int = 1
) -> Tuple[List[Citation], Dict[str, Any]]:
    """
    Generate citations with contextual information.
    
    Returns:
        Tuple of (citations, context_data)
    """
    relevant_with_context = self.find_relevant_chunks_with_context(
        claim, chunks, top_k=top_k, context_window=context_window
    )
    
    citations = []
    context_data = {}
    
    for chunk, score, context_chunks in relevant_with_context[:top_k]:
        citation = Citation(
            chunk_id=chunk.chunk_id,
            text=chunk.text,
            page=chunk.page,
            char_start=chunk.char_start,
            char_end=chunk.char_end,
            similarity_score=score,
            confidence_level="high" if score >= 0.7 else "medium" if score >= 0.5 else "low",
            section_title=chunk.section_title,
            text_preview=chunk.text[:200] + ("..." if len(chunk.text) > 200 else "")
        )
        citations.append(citation)
        
        # Store context for this chunk
        context_data[chunk.chunk_id] = {
            "context_chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "text_preview": c.text[:100] + ("..." if len(c.text) > 100 else ""),
                    "page": c.page
                }
                for c in context_chunks
            ]
        }
    
    return citations, context_data

def merge_citations_from_multiple_claims(
    self,
    claims: List[ClaimWithCitations],
    deduplicate: bool = True
) -> Dict[str, Any]:
    """
    Merge citations from multiple claims, with optional deduplication.
    
    Args:
        claims: List of ClaimWithCitations objects
        deduplicate: Whether to remove duplicate chunk references
        
    Returns:
        Dictionary with merged citation data
    """
    merged = {
        "unique_chunks": set(),
        "chunk_frequency": defaultdict(int),
        "page_distribution": defaultdict(int),
        "confidence_distribution": defaultdict(int)
    }
    
    for claim in claims:
        for citation in claim.citations:
            chunk_id = citation.chunk_id
            
            if deduplicate:
                merged["unique_chunks"].add(chunk_id)
            
            merged["chunk_frequency"][chunk_id] += 1
            merged["page_distribution"][citation.page] += 1
            merged["confidence_distribution"][citation.confidence_level] += 1
    
    return {
        "total_unique_chunks": len(merged["unique_chunks"]),
        "most_cited_chunks": sorted(
            merged["chunk_frequency"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10],
        "page_distribution": dict(merged["page_distribution"]),
        "confidence_distribution": dict(merged["confidence_distribution"]),
        "total_citations": sum(merged["chunk_frequency"].values())
    }

# Utility function for quick testing
def create_citations_for_document(
    processed_doc_path: str,
    claims_data: List[Dict[str, str]],
    output_dir: str = "citation_output",
    top_k: int = 3
) -> Dict[str, Any]:
    """
    Quick utility to generate citations for a processed document.
    
    Args:
        processed_doc_path: Path to the processed document JSON
        claims_data: List of claim dictionaries with 'text', 'visual_prompt', 'audio_script'
        output_dir: Directory to save the manifest
        top_k: Number of citations per claim
        
    Returns:
        The complete citation manifest
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # Load document chunks
    manager = CitationManager()
    chunks = manager.load_document_chunks(processed_doc_path)
    
    # Generate citations
    claims_with_citations = manager.generate_citations_batch(claims_data, chunks, top_k=top_k)
    
    # Load document metadata
    with open(processed_doc_path, 'r') as f:
        doc_data = json.load(f)
    
    # Create manifest
    manifest = manager.create_citation_manifest(claims_with_citations, doc_data['metadata'])
    
    # Save manifest
    base_name = processed_doc_path.split('/')[-1].replace('_processed.json', '')
    output_path = os.path.join(output_dir, f"{base_name}_citations.json")
    manager.save_manifest(manifest, output_path)
    
    return manifest