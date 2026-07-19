import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict

from genblaze_core import Pipeline, Step, Sinks, KeyStrategy, PipelineConfig
from genblaze_core.providers import (
    GPTProvider,
    ImageGenProvider,
    AudioGenProvider,
    VideoGenProvider,
    TextGenProvider
)
from genblaze_s3 import S3StorageBackend
from genblaze_gmicloud import GMIProvider
from genblaze_openai import OpenAIProvider

from app.core.document_processor import DocumentProcessor
from app.core.citation_manager import (
    CitationManager, 
    ClaimWithCitations,
    Citation
)
from app.storage.b2_client import B2StorageClient
from app.utils.config import Config
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineJob:
    """Represents a pipeline job with all its metadata."""
    job_id: str
    document_path: str
    audience: str  # "executive", "engineer", "student"
    status: str  # "pending", "processing", "completed", "failed"
    created_at: str
    updated_at: str
    output_path: str
    manifest_path: str
    error: Optional[str] = None


class CiteCastPipeline:
    """
    The main Genblaze pipeline for CiteCast.
    Orchestrates document processing, citation generation, and media creation.
    """
    
    def __init__(self, b2_bucket: Optional[str] = None):
        """
        Initialize the CiteCast pipeline.
        
        Args:
            b2_bucket: Backblaze B2 bucket name (defaults to config)
        """
        self.b2_bucket = b2_bucket or Config.B2_BUCKET_NAME
        self.b2_client = B2StorageClient(self.b2_bucket)
        self.doc_processor = DocumentProcessor()
        self.citation_manager = CitationManager()
        
        # Store active jobs
        self.active_jobs: Dict[str, PipelineJob] = {}
        
        # Configure the Genblaze pipeline
        self.pipeline_config = PipelineConfig(
            name="citecast_pipeline",
            retry_on_failure=True,
            max_retries=3,
            parallel_execution=True,
            max_parallel_steps=10
        )
        
        logger.info(f"Initialized CiteCastPipeline with bucket: {self.b2_bucket}")
    
    def create_job(
        self, 
        document_path: str, 
        audience: str = "executive",
        num_scenes: int = 5
    ) -> str:
        """
        Create a new pipeline job.
        
        Args:
            document_path: Path to the source PDF
            audience: Target audience ("executive", "engineer", "student")
            num_scenes: Number of scenes to generate
            
        Returns:
            Job ID
        """
        job_id = f"job_{uuid.uuid4().hex[:8]}"
        
        job = PipelineJob(
            job_id=job_id,
            document_path=document_path,
            audience=audience,
            status="pending",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            output_path=f"generated-assets/{job_id}/{audience}/",
            manifest_path=f"generated-assets/{job_id}/{audience}/manifest.json",
            error=None
        )
        
        self.active_jobs[job_id] = job
        logger.info(f"Created job {job_id} for audience: {audience}")
        return job_id
    
    def run_pipeline(self, job_id: str) -> Dict[str, Any]:
        """
        Run the full pipeline for a given job.
        
        Args:
            job_id: The job ID to process
            
        Returns:
            Dictionary with pipeline results
        """
        job = self.active_jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        logger.info(f"Starting pipeline for job {job_id}")
        
        try:
            # Update job status
            job.status = "processing"
            job.updated_at = datetime.utcnow().isoformat()
            
            # Step 1: Process the document
            logger.info(f"Step 1: Processing document: {job.document_path}")
            processed_doc = self.doc_processor.process_document(job.document_path)
            
            # Store processed document in B2
            doc_path = f"processed-documents/{job_id}/processed.json"
            self.b2_client.upload_json(processed_doc, doc_path)
            
            # Step 2: Generate summaries for the audience
            logger.info(f"Step 2: Generating audience-specific summary ({job.audience})")
            summary = self._generate_audience_summary(
                processed_doc['chunks'],
                job.audience,
                num_scenes=5
            )
            
            # Step 3: Generate citations for each claim
            logger.info("Step 3: Generating citations")
            claims_with_citations = self._generate_citations(
                summary['claims'],
                processed_doc['chunks']
            )
            
            # Step 4: Generate media (images, audio, video)
            logger.info("Step 4: Generating media assets")
            media_outputs = self._generate_media(
                claims_with_citations,
                job.audience,
                job.output_path
            )
            
            # Step 5: Build the final manifest
            logger.info("Step 5: Building final manifest")
            manifest = self._build_final_manifest(
                processed_doc,
                claims_with_citations,
                media_outputs,
                job.audience
            )
            
            # Step 6: Upload manifest to B2
            logger.info("Step 6: Uploading manifest to B2")
            self.b2_client.upload_json(manifest, job.manifest_path)
            
            # Step 7: Upload all media assets to B2
            logger.info("Step 7: Uploading media assets to B2")
            self._upload_media_assets(media_outputs, job.output_path)
            
            # Update job status
            job.status = "completed"
            job.updated_at = datetime.utcnow().isoformat()
            
            logger.info(f"Pipeline completed successfully for job {job_id}")
            
            return {
                "job_id": job_id,
                "status": "completed",
                "manifest_url": f"s3://{self.b2_bucket}/{job.manifest_path}",
                "output_path": job.output_path,
                "total_scenes": len(claims_with_citations),
                "total_citations": sum(len(c.citations) for c in claims_with_citations)
            }
            
        except Exception as e:
            logger.error(f"Pipeline failed for job {job_id}: {str(e)}")
            job.status = "failed"
            job.error = str(e)
            job.updated_at = datetime.utcnow().isoformat()
            raise
    
    def _generate_audience_summary(
        self, 
        chunks: List[Dict[str, Any]], 
        audience: str,
        num_scenes: int = 5
    ) -> Dict[str, Any]:
        """
        Generate an audience-specific summary using Genblaze.
        
        Args:
            chunks: List of document chunks
            audience: Target audience
            num_scenes: Number of scenes to generate
            
        Returns:
            Dictionary with summary and claims
        """
        # Create the summary prompt based on audience
        prompt_templates = {
            "executive": """
                You are an executive summary writer. Create a {num_scenes}-scene executive summary from the following document.
                For each scene, provide:
                1. A clear, concise claim (1-2 sentences)
                2. A visual prompt for image generation
                3. An audio script for voiceover
                
                Focus on: Strategic insights, key metrics, high-level conclusions, and business impact.
                Keep each claim under 150 characters.
                
                Document content:
                {document_text}
            """,
            "engineer": """
                You are a technical writer. Create a {num_scenes}-scene technical summary from the following document.
                For each scene, provide:
                1. A precise technical claim (1-2 sentences)
                2. A visual prompt for diagram or technical illustration
                3. An audio script for voiceover
                
                Focus on: Technical specifications, architecture details, data flows, and implementation details.
                Keep each claim under 150 characters.
                
                Document content:
                {document_text}
            """,
            "student": """
                You are an educational content creator. Create a {num_scenes}-scene simplified summary from the following document.
                For each scene, provide:
                1. A simple, easy-to-understand claim (1-2 sentences)
                2. A visual prompt for an engaging, educational illustration
                3. An audio script for voiceover
                
                Focus on: Core concepts, simple explanations, relatable examples, and key takeaways.
                Keep each claim under 150 characters.
                
                Document content:
                {document_text}
            """
        }
        
        # Get the appropriate prompt template
        prompt_template = prompt_templates.get(audience, prompt_templates["executive"])
        
        # Prepare the document text (first 2000 chars to keep prompt size reasonable)
        document_text = "\n\n".join([chunk['text'][:300] for chunk in chunks[:10]])
        if len(document_text) > 2000:
            document_text = document_text[:2000] + "..."
        
        # Create the prompt
        prompt = prompt_template.format(
            num_scenes=num_scenes,
            document_text=document_text
        )
        
        # Use Genblaze with OpenAI or GMI Cloud for summarization
        try:
            # Try GMI Cloud first (as per hackathon requirements)
            llm_provider = GMIProvider(
                model="gmi-cloud/llama-3-70b",
                api_key=Config.GMI_API_KEY
            )
            response = llm_provider.generate_text(prompt)
        except Exception as e:
            logger.warning(f"GMI Cloud failed, falling back to OpenAI: {e}")
            llm_provider = OpenAIProvider(
                model="gpt-4-turbo-preview",
                api_key=Config.OPENAI_API_KEY
            )
            response = llm_provider.generate_text(prompt)
        
        # Parse the response into structured claims
        claims = self._parse_summary_response(response, num_scenes)
        
        return {
            "audience": audience,
            "num_scenes": len(claims),
            "claims": claims,
            "raw_response": response
        }
    
    def _parse_summary_response(self, response: str, expected_scenes: int) -> List[Dict[str, str]]:
        """
        Parse the LLM response into structured claims.
        
        This is a simplified parser - in production you'd want more robust parsing.
        """
        claims = []
        
        # Split by scene markers (assuming numbered or bulleted list)
        lines = response.split('\n')
        
        current_claim = {}
        scene_count = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to detect a new scene
            if line.startswith(('1.', '2.', '3.', '4.', '5.', 'Scene', 'Scene:', '---')):
                if current_claim and 'text' in current_claim:
                    claims.append(current_claim)
                    scene_count += 1
                
                current_claim = {}
            
            # Extract claim text
            elif 'claim' in line.lower() or 'text' in line.lower() or 'sentence' in line.lower():
                # Try to extract the claim
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_claim['text'] = parts[1].strip()
                else:
                    current_claim['text'] = line.replace('Claim:', '').replace('Text:', '').strip()
            
            # Extract visual prompt
            elif 'visual' in line.lower() or 'image' in line.lower():
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_claim['visual_prompt'] = parts[1].strip()
                else:
                    current_claim['visual_prompt'] = line.replace('Visual:', '').replace('Image:', '').strip()
            
            # Extract audio script
            elif 'audio' in line.lower() or 'voice' in line.lower() or 'narration' in line.lower():
                parts = line.split(':', 1)
                if len(parts) > 1:
                    current_claim['audio_script'] = parts[1].strip()
                else:
                    current_claim['audio_script'] = line.replace('Audio:', '').replace('Voice:', '').strip()
        
        # Add the last claim
        if current_claim and 'text' in current_claim:
            claims.append(current_claim)
        
        # Ensure we have the expected number of claims
        while len(claims) < expected_scenes:
            # Add placeholder if needed
            claims.append({
                'text': f"Key point {len(claims) + 1} from the document",
                'visual_prompt': f"Illustration for key point {len(claims) + 1}",
                'audio_script': f"Narration for key point {len(claims) + 1}"
            })
        
        # Set defaults for missing fields
        for claim in claims:
            if 'visual_prompt' not in claim:
                claim['visual_prompt'] = f"Visual illustrating: {claim['text'][:100]}"
            if 'audio_script' not in claim:
                claim['audio_script'] = f"Voiceover: {claim['text']}"
        
        return claims[:expected_scenes]
    
    def _generate_citations(
        self, 
        claims: List[Dict[str, str]], 
        chunks_data: List[Dict[str, Any]]
    ) -> List[ClaimWithCitations]:
        """
        Generate citations for each claim using the CitationManager.
        """
        # Convert chunks data to TextChunk objects
        from app.core.document_processor import TextChunk
        chunks = [
            TextChunk(
                chunk_id=chunk['chunk_id'],
                text=chunk['text'],
                page=chunk['page'],
                char_start=chunk['char_start'],
                char_end=chunk['char_end'],
                section_title=chunk.get('section_title'),
                embedding=chunk.get('embedding')
            )
            for chunk in chunks_data
        ]
        
        # Generate citations for all claims
        claims_with_citations = self.citation_manager.generate_citations_batch(
            claims, chunks, top_k=3
        )
        
        return claims_with_citations
    
    def _generate_media(
        self, 
        claims: List[ClaimWithCitations], 
        audience: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Generate media assets (images, audio) for each claim.
        Uses Genblaze providers in parallel.
        """
        media_outputs = {
            "images": [],
            "audio": [],
            "scenes": []
        }
        
        # Create a Genblaze pipeline for parallel media generation
        media_pipeline = Pipeline(
            name=f"citecast_media_{audience}",
            config=self.pipeline_config
        )
        
        # Add steps for each claim
        for i, claim in enumerate(claims):
            scene_id = f"scene_{i:03d}"
            
            # Image generation step
            media_pipeline.add_step(Step(
                name=f"image_gen_{scene_id}",
                provider=GMIProvider(
                    model="gmi-cloud/seedream-v1",
                    api_key=Config.GMI_API_KEY
                ),
                config={
                    "prompt": claim.visual_prompt,
                    "size": "1024x1024",
                    "negative_prompt": "blurry, low quality, distorted"
                },
                output_key=f"image_{scene_id}",
                retry_on_failure=True,
                max_retries=3
            ))
            
            # Audio generation step
            media_pipeline.add_step(Step(
                name=f"audio_gen_{scene_id}",
                provider=GMIProvider(
                    model="gmi-cloud/elevenlabs-v2",
                    api_key=Config.GMI_API_KEY
                ),
                config={
                    "text": claim.audio_script,
                    "voice": "en-US-JennyNeural" if audience == "student" else "en-US-GuyNeural",
                    "speed": 1.0
                },
                output_key=f"audio_{scene_id}",
                retry_on_failure=True,
                max_retries=3
            ))
        
        try:
            # Run the media generation pipeline
            results = media_pipeline.run()
            
            # Organize results by scene
            for i, claim in enumerate(claims):
                scene_id = f"scene_{i:03d}"
                
                image_key = f"image_{scene_id}"
                audio_key = f"audio_{scene_id}"
                
                # Get the generated content
                image_data = results.get(image_key)
                audio_data = results.get(audio_key)
                
                # Save locally (will be uploaded to B2 later)
                local_base = f"generated_assets/{output_path}"
                os.makedirs(local_base, exist_ok=True)
                
                image_path = f"{local_base}/{scene_id}.png"
                audio_path = f"{local_base}/{scene_id}.mp3"
                
                if image_data:
                    with open(image_path, 'wb') as f:
                        f.write(image_data.content)
                
                if audio_data:
                    with open(audio_path, 'wb') as f:
                        f.write(audio_data.content)
                
                media_outputs["images"].append({
                    "scene_id": scene_id,
                    "path": image_path,
                    "remote_path": f"{output_path}{scene_id}.png"
                })
                
                media_outputs["audio"].append({
                    "scene_id": scene_id,
                    "path": audio_path,
                    "remote_path": f"{output_path}{scene_id}.mp3"
                })
                
                media_outputs["scenes"].append({
                    "scene_id": scene_id,
                    "claim": claim,
                    "image_path": image_path,
                    "audio_path": audio_path
                })
                
        except Exception as e:
            logger.error(f"Media generation failed: {e}")
            # Fallback to placeholder images
            for i, claim in enumerate(claims):
                scene_id = f"scene_{i:03d}"
                media_outputs["scenes"].append({
                    "scene_id": scene_id,
                    "claim": claim,
                    "image_path": None,
                    "audio_path": None,
                    "error": str(e)
                })
        
        return media_outputs
    
    def _build_final_manifest(
        self,
        processed_doc: Dict[str, Any],
        claims_with_citations: List[ClaimWithCitations],
        media_outputs: Dict[str, Any],
        audience: str
    ) -> Dict[str, Any]:
        """
        Build the final manifest combining all data.
        """
        manifest = {
            "job_info": {
                "created_at": datetime.utcnow().isoformat(),
                "audience": audience,
                "version": "1.0.0"
            },
            "document": processed_doc.get('metadata', {}),
            "scenes": [],
            "statistics": {
                "total_scenes": len(claims_with_citations),
                "total_citations": 0,
                "confidence_distribution": {"high": 0, "medium": 0, "low": 0}
            }
        }
        
        for i, claim in enumerate(claims_with_citations):
            scene_media = media_outputs["scenes"][i] if i < len(media_outputs["scenes"]) else {}
            
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
                    "image": scene_media.get("remote_path", ""),
                    "audio": scene_media.get("remote_path", "").replace(".png", ".mp3")
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
            
            # Update statistics
            manifest["statistics"]["total_citations"] += len(claim.citations)
            for c in claim.citations:
                manifest["statistics"]["confidence_distribution"][c.confidence_level] += 1
        
        # Add validation summary
        manifest["validation"] = {
            "all_have_citations": all(len(c.citations) > 0 for c in claims_with_citations),
            "coverage": sum(1 for c in claims_with_citations if len(c.citations) > 0) / len(claims_with_citations)
        }
        
        return manifest
    
    def _upload_media_assets(self, media_outputs: Dict[str, Any], output_path: str):
        """
        Upload generated media assets to B2.
        """
        # Upload images
        for image_data in media_outputs.get("images", []):
            if os.path.exists(image_data["path"]):
                with open(image_data["path"], 'rb') as f:
                    self.b2_client.sink.write(
                        path=image_data["remote_path"],
                        content=f.read(),
                        content_type="image/png"
                    )
                logger.info(f"Uploaded image: {image_data['remote_path']}")
        
        # Upload audio
        for audio_data in media_outputs.get("audio", []):
            if os.path.exists(audio_data["path"]):
                with open(audio_data["path"], 'rb') as f:
                    self.b2_client.sink.write(
                        path=audio_data["remote_path"],
                        content=f.read(),
                        content_type="audio/mpeg"
                    )
                logger.info(f"Uploaded audio: {audio_data['remote_path']}")

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the status of a pipeline job.
        """
        job = self.active_jobs.get(job_id)
        if not job:
            return None
        
        return {
            "job_id": job.job_id,
            "status": job.status,
            "audience": job.audience,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "output_path": job.output_path,
            "manifest_path": job.manifest_path,
            "error": job.error
        }