"""
Manifest Builder - Creates and manages citation manifests.
Combines document metadata, citations, and media assets into a unified manifest.
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from app.core.citation_manager import ClaimWithCitations, Citation
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ManifestMetadata:
    """Metadata for the manifest."""
    version: str = "1.0.0"
    created_at: str = ""
    job_id: str = ""
    audience: str = ""
    document_hash: str = ""
    total_scenes: int = 0
    total_citations: int = 0


class ManifestBuilder:
    """
    Builds comprehensive citation manifests.
    """
    
    def __init__(self):
        self.manifest = {
            "metadata": {},
            "document": {},
            "scenes": [],
            "statistics": {},
            "validation": {}
        }
    
    def build_manifest(
        self,
        job_id: str,
        document_metadata: Dict[str, Any],
        claims_with_citations: List[ClaimWithCitations],
        media_outputs: Dict[str, Any],
        audience: str
    ) -> Dict[str, Any]:
        """
        Build a complete citation manifest.
        """
        manifest = {
            "metadata": {
                "version": "1.0.0",
                "created_at": datetime.utcnow().isoformat(),
                "job_id": job_id,
                "audience": audience,
                "total_scenes": len(claims_with_citations),
                "total_citations": 0
            },
            "document": document_metadata,
            "scenes": [],
            "statistics": {
                "confidence_distribution": {"high": 0, "medium": 0, "low": 0},
                "pages_covered": []
            },
            "validation": {
                "all_scenes_have_citations": True,
                "coverage_score": 0.0
            }
        }
        
        pages_covered = set()
        
        for i, claim in enumerate(claims_with_citations):
            scene = {
                "scene_id": f"scene_{i:03d}",
                "order": i,
                "claim": {
                    "text": claim.text,
                    "visual_prompt": claim.visual_prompt,
                    "audio_script": claim.audio_script
                },
                "timestamp_start": claim.timestamp_start,
                "timestamp_end": claim.timestamp_end,
                "media": {
                    "image": media_outputs.get("images", [{}])[i].get("remote_path", "") if i < len(media_outputs.get("images", [])) else "",
                    "audio": media_outputs.get("audio", [{}])[i].get("remote_path", "") if i < len(media_outputs.get("audio", [])) else ""
                },
                "citations": [
                    {
                        "chunk_id": c.chunk_id,
                        "page": c.page,
                        "text_preview": c.text_preview,
                        "similarity_score": c.similarity_score,
                        "confidence_level": c.confidence_level,
                        "section_title": c.section_title,
                        "char_start": c.char_start,
                        "char_end": c.char_end
                    }
                    for c in claim.citations
                ]
            }
            
            manifest["scenes"].append(scene)
            manifest["metadata"]["total_citations"] += len(claim.citations)
            
            # Update statistics
            for c in claim.citations:
                manifest["statistics"]["confidence_distribution"][c.confidence_level] += 1
                pages_covered.add(c.page)
        
        # Update validation
        manifest["statistics"]["pages_covered"] = sorted(list(pages_covered))
        manifest["validation"]["all_scenes_have_citations"] = all(
            len(c.citations) > 0 for c in claims_with_citations
        )
        manifest["validation"]["coverage_score"] = sum(
            1 for c in claims_with_citations if len(c.citations) > 0
        ) / len(claims_with_citations) if claims_with_citations else 0.0
        
        self.manifest = manifest
        return manifest
    
    def save_manifest(self, file_path: str):
        """Save manifest to file."""
        with open(file_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)
        logger.info(f"Saved manifest to: {file_path}")
    
    def load_manifest(self, file_path: str) -> Dict[str, Any]:
        """Load manifest from file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        self.manifest = data
        return data
    
    def generate_citation_report(self, format: str = "json") -> str:
        """
        Generate a human-readable citation report.
        """
        if format == "json":
            return json.dumps(self.manifest, indent=2)
        
        elif format == "markdown":
            lines = []
            lines.append("# Citation Report")
            lines.append("")
            lines.append(f"**Job ID:** {self.manifest.get('metadata', {}).get('job_id', 'N/A')}")
            lines.append(f"**Audience:** {self.manifest.get('metadata', {}).get('audience', 'N/A')}")
            lines.append(f"**Total Scenes:** {self.manifest.get('metadata', {}).get('total_scenes', 0)}")
            lines.append(f"**Total Citations:** {self.manifest.get('metadata', {}).get('total_citations', 0)}")
            lines.append("")
            
            lines.append("## Citations by Scene")
            lines.append("")
            for scene in self.manifest.get('scenes', []):
                lines.append(f"### Scene {scene.get('order', 0) + 1}: {scene.get('claim', {}).get('text', '')[:100]}...")
                lines.append("")
                for citation in scene.get('citations', []):
                    lines.append(f"- **Page {citation.get('page', 'N/A')}** ({citation.get('confidence_level', 'unknown')} confidence): {citation.get('text_preview', '')[:100]}...")
                lines.append("")
            
            lines.append("## Statistics")
            lines.append("")
            stats = self.manifest.get('statistics', {})
            lines.append(f"- Confidence Distribution: {stats.get('confidence_distribution', {})}")
            lines.append(f"- Pages Covered: {stats.get('pages_covered', [])}")
            
            return "\n".join(lines)
        
        else:
            raise ValueError(f"Unsupported format: {format}")