import hashlib
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

import pypdf
import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
import numpy as np
from sentence_transformers import SentenceTransformer

from app.utils.config import Config
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """Represents a single chunk of text from the source document."""
    chunk_id: str
    text: str
    page: int
    char_start: int
    char_end: int
    section_title: Optional[str] = None
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "page": self.page,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "section_title": self.section_title,
            "embedding": self.embedding,
            "text_preview": self.text[:200] + ("..." if len(self.text) > 200 else "")
        }


@dataclass
class DocumentMetadata:
    """Metadata extracted from the source document."""
    filename: str
    total_pages: int
    total_chars: int
    total_chunks: int
    processed_at: str
    file_hash: str
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[str] = None


class DocumentProcessor:
    """
    Handles PDF parsing, chunking, and embedding generation.
    Preserves position information for citation tracking.
    """
    
    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the document processor.
        
        Args:
            embedding_model_name: Name of the sentence transformer model to use.
                                 Default is a lightweight model good for RAG.
        """
        self.embedding_model = SentenceTransformer(embedding_model_name)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,           # ~2000 chars, good for embeddings
            chunk_overlap=50,         # Ensures context continuity
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )
        logger.info(f"Initialized DocumentProcessor with model: {embedding_model_name}")
    
    def parse_pdf(self, file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Parse a PDF file and extract text with page position tracking.
        
        Returns:
            Tuple of (full_text, page_map)
        """
        logger.info(f"Parsing PDF: {file_path}")
        full_text = ""
        page_map = []
        
        try:
            # Use pdfplumber for better text extraction accuracy
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text is None:
                        continue
                    
                    # Clean up whitespace
                    text = re.sub(r'\s+', ' ', text).strip()
                    
                    start_char = len(full_text)
                    full_text += text
                    end_char = len(full_text)
                    
                    page_map.append({
                        "page": i + 1,
                        "start": start_char,
                        "end": end_char,
                        "text_preview": text[:200]
                    })
            
            logger.info(f"Extracted {len(page_map)} pages, {len(full_text)} characters")
            return full_text, page_map
            
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            # Fallback to pypdf
            return self._parse_pdf_fallback(file_path)
    
    def _parse_pdf_fallback(self, file_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Fallback PDF parser using pypdf."""
        logger.warning("Using fallback PDF parser (pypdf)")
        full_text = ""
        page_map = []
        
        with open(file_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text is None:
                    continue
                
                text = re.sub(r'\s+', ' ', text).strip()
                start_char = len(full_text)
                full_text += text
                end_char = len(full_text)
                
                page_map.append({
                    "page": i + 1,
                    "start": start_char,
                    "end": end_char,
                    "text_preview": text[:200]
                })
        
        return full_text, page_map
    
    def chunk_text(self, text: str, page_map: List[Dict[str, Any]]) -> List[TextChunk]:
        """
        Split text into overlapping chunks and map each chunk to source pages.
        
        Args:
            text: Full text of the document
            page_map: List of page position mappings
            
        Returns:
            List of TextChunk objects with position information
        """
        logger.info("Chunking text...")
        chunks = self.text_splitter.split_text(text)
        
        result = []
        for i, chunk_text in enumerate(chunks):
            # Find where this chunk appears in the full text
            # Using start position for accurate page mapping
            chunk_start = text.find(chunk_text[:50])
            
            # If chunk_start is -1 (rare), estimate using substring search
            if chunk_start == -1:
                # Try to find the chunk with some tolerance
                for j in range(0, len(text) - len(chunk_text), 100):
                    if text[j:j+100].strip() == chunk_text[:100].strip():
                        chunk_start = j
                        break
            
            # Find which page this chunk belongs to
            page_ref = self._find_page_for_position(chunk_start, page_map)
            
            # Extract section title if present (titles are typically near start of chunk)
            section_title = self._extract_section_title(chunk_text)
            
            chunk = TextChunk(
                chunk_id=f"chunk_{i:04d}",
                text=chunk_text,
                page=page_ref["page"] if page_ref else 1,
                char_start=chunk_start if chunk_start != -1 else 0,
                char_end=chunk_start + len(chunk_text) if chunk_start != -1 else len(chunk_text),
                section_title=section_title
            )
            result.append(chunk)
        
        logger.info(f"Created {len(result)} chunks")
        return result
    
    def _find_page_for_position(self, position: int, page_map: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find which page a character position belongs to."""
        if position < 0:
            return page_map[0] if page_map else None
        
        for page_info in page_map:
            if page_info["start"] <= position < page_info["end"]:
                return page_info
        
        # If position is beyond the last page, return last page
        if position >= page_map[-1]["end"] and page_map:
            return page_map[-1]
        
        return page_map[0] if page_map else None
    
    def _extract_section_title(self, chunk_text: str) -> Optional[str]:
        """
        Try to extract a section title from a chunk.
        Looks for patterns like "## Title", "1. Title", etc.
        """
        # Common heading patterns
        patterns = [
            r'^#+\s+(.+?)(?:\n|$)',           # Markdown style: # Title
            r'^(\d+\.?\s+[A-Z][A-Za-z\s]+)(?:\n|$)',  # Numbered: 1. Title
            r'^([A-Z][A-Z\s]+)(?:\n|$)',      # ALL CAPS title
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)(?:\n|$)', # Title Case
        ]
        
        for pattern in patterns:
            match = re.search(pattern, chunk_text, re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def generate_embeddings(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """Generate embeddings for each chunk."""
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)
        
        for i, chunk in enumerate(chunks):
            chunk.embedding = embeddings[i].tolist()
        
        logger.info("Embeddings generated successfully")
        return chunks
    
    def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        Complete document processing pipeline.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dict containing document metadata, chunks, and page map
        """
        logger.info(f"Processing document: {file_path}")
        
        # 1. Parse PDF
        full_text, page_map = self.parse_pdf(file_path)
        
        # 2. Chunk text
        chunks = self.chunk_text(full_text, page_map)
        
        # 3. Generate embeddings
        chunks_with_embeddings = self.generate_embeddings(chunks)
        
        # 4. Build metadata
        metadata = self._build_metadata(file_path, full_text, chunks)
        
        result = {
            "metadata": asdict(metadata),
            "page_map": page_map,
            "chunks": [chunk.to_dict() for chunk in chunks_with_embeddings],
            "full_text": full_text
        }
        
        logger.info(f"Document processed: {metadata.filename}")
        return result
    
    def _build_metadata(self, file_path: str, full_text: str, chunks: List[TextChunk]) -> DocumentMetadata:
        """Build document metadata."""
        # Calculate file hash
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()[:16]
        
        # Try to extract document metadata
        title = None
        author = None
        creation_date = None
        
        try:
            with pdfplumber.open(file_path) as pdf:
                if pdf.metadata:
                    title = pdf.metadata.get('Title')
                    author = pdf.metadata.get('Author')
                    creation_date = pdf.metadata.get('CreationDate')
        except:
            pass
        
        return DocumentMetadata(
            filename=file_path.split('/')[-1],
            total_pages=max([chunk.page for chunk in chunks]) if chunks else 1,
            total_chars=len(full_text),
            total_chunks=len(chunks),
            processed_at=datetime.utcnow().isoformat(),
            file_hash=file_hash,
            title=title,
            author=author,
            creation_date=creation_date
        )
    
    def save_processed_document(self, result: Dict[str, Any], output_path: str):
        """Save processed document result to JSON."""
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        logger.info(f"Saved processed document to: {output_path}")
    
    def load_processed_document(self, file_path: str) -> Dict[str, Any]:
        """Load a previously processed document from JSON."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        logger.info(f"Loaded processed document from: {file_path}")
        return data


# Utility function for quick testing
def process_sample_document(file_path: str, output_dir: str = "processed_data"):
    """Quick utility to process a sample document."""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    processor = DocumentProcessor()
    result = processor.process_document(file_path)
    
    # Generate output filename
    base_name = file_path.split('/')[-1].replace('.pdf', '')
    output_path = os.path.join(output_dir, f"{base_name}_processed.json")
    
    processor.save_processed_document(result, output_path)
    return result