"""
FastAPI application for CiteCast.
Provides endpoints for document upload, pipeline execution, and media viewing.
"""

import os
import json
import shutil
from typing import Optional, List
from datetime import datetime
from pathlib import Path

try:
    from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - optional dependency fallback
    raise

import uuid

from app.core.pipeline import CiteCastPipeline
from app.storage.b2_client import B2StorageClient
from app.utils.config import Config
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="CiteCast API",
    description="Citation-aware document to multimedia generator",
    version="1.0.0"
)

# Setup templates and static files
base_dir = Path(__file__).resolve().parent
repo_root = base_dir.parent.parent
templates_dir = base_dir / "templates"
static_dir = base_dir / "static"
generated_dir = repo_root / "generated_assets"
upload_dir = repo_root / "uploads"

for path in [generated_dir, upload_dir]:
    path.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/generated", StaticFiles(directory=str(generated_dir)), name="generated")

# Initialize pipeline
pipeline = CiteCastPipeline()
b2_client = B2StorageClient()


# Pydantic models
class JobCreateRequest(BaseModel):
    document_path: str
    audience: str = Field(..., pattern="^(executive|engineer|student)$")
    num_scenes: int = Field(5, ge=1, le=10)


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    audience: str
    created_at: str
    updated_at: str
    output_path: Optional[str] = None
    manifest_path: Optional[str] = None
    error: Optional[str] = None


class CitationResponse(BaseModel):
    chunk_id: str
    text_preview: str
    page: int
    confidence_level: str
    similarity_score: float
    section_title: Optional[str] = None


class SceneResponse(BaseModel):
    scene_id: str
    order: int
    claim_text: str
    image_url: str
    audio_url: str
    citations: List[CitationResponse]
    timestamp_start: float
    timestamp_end: float


# API Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the main page."""
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})


@app.get("/viewer/{job_id}", response_class=HTMLResponse)
async def viewer(request: Request, job_id: str):
    """Serve the viewer page for a specific job."""
    # Get job status
    status = pipeline.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Load manifest from B2
    try:
        manifest = b2_client.download_json(status['manifest_path'])
    except Exception as e:
        logger.error(f"Failed to load manifest: {e}")
        manifest = None
    
    return templates.TemplateResponse(
        request=request,
        name="viewer.html",
        context={
            "request": request,
            "job_id": job_id,
            "status": status,
            "manifest": manifest
        }
    )


@app.post("/api/jobs")
async def create_job(
    file: UploadFile = File(...),
    audience: str = Form("executive"),
    num_scenes: int = Form(5)
):
    """
    Create a new pipeline job from an uploaded document.
    """
    # Validate audience
    if audience not in ["executive", "engineer", "student"]:
        raise HTTPException(status_code=400, detail="Invalid audience")
    
    # Validate num_scenes
    if not 1 <= num_scenes <= 10:
        raise HTTPException(status_code=400, detail="num_scenes must be between 1 and 10")
    
    # Save uploaded file
    upload_dir = repo_root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / f"{uuid.uuid4().hex}_{file.filename}"
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # Create job
    job_id = pipeline.create_job(
        str(file_path),
        audience=audience,
        num_scenes=num_scenes
    )
    
    # Run pipeline asynchronously (we'll do sync for simplicity, but could use background tasks)
    # For production, use background tasks or Celery
    try:
        result = pipeline.run_pipeline(job_id)
        status = pipeline.get_job_status(job_id)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        status = pipeline.get_job_status(job_id)
    
    return JSONResponse({
        "job_id": job_id,
        "status": status['status'] if status else "failed",
        "viewer_url": f"/viewer/{job_id}",
        "message": "Job created and processing started"
    })


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of a pipeline job.
    """
    status = pipeline.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JSONResponse(status)


@app.get("/api/jobs/{job_id}/manifest")
async def get_manifest(job_id: str):
    """
    Get the full citation manifest for a job.
    """
    status = pipeline.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        manifest = b2_client.download_json(status['manifest_path'])
        return JSONResponse(manifest)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load manifest: {str(e)}")


@app.get("/api/jobs/{job_id}/scenes")
async def get_scenes(job_id: str):
    """
    Get scene data with citations for a job.
    """
    status = pipeline.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        manifest = b2_client.download_json(status['manifest_path'])
        
        scenes = []
        for scene in manifest.get('scenes', []):
            scenes.append({
                "scene_id": scene['scene_id'],
                "order": scene['order'],
                "claim_text": scene['claim']['text'],
                "image_url": f"/generated/{scene['media']['image']}" if scene['media']['image'] else None,
                "audio_url": f"/generated/{scene['media']['audio']}" if scene['media']['audio'] else None,
                "citations": scene['citations'],
                "timestamp_start": scene['timestamp_start'],
                "timestamp_end": scene['timestamp_end']
            })
        
        return JSONResponse({
            "job_id": job_id,
            "total_scenes": len(scenes),
            "scenes": scenes
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load scenes: {str(e)}")


@app.get("/api/jobs/{job_id}/citations/export")
async def export_citations(job_id: str, format: str = "json"):
    """
    Export citations in various formats.
    """
    status = pipeline.get_job_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        manifest = b2_client.download_json(status['manifest_path'])
        
        if format == "json":
            return JSONResponse(manifest)
        
        elif format == "csv":
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["Scene", "Claim", "Chunk ID", "Page", "Confidence", "Text Preview"])
            
            for scene in manifest.get('scenes', []):
                for citation in scene.get('citations', []):
                    writer.writerow([
                        scene['scene_id'],
                        scene['claim']['text'][:100],
                        citation['chunk_id'],
                        citation['page'],
                        citation['confidence_level'],
                        citation['text_preview']
                    ])
            
            return JSONResponse({
                "csv": output.getvalue(),
                "filename": f"citations_{job_id}.csv"
            })
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "b2_configured": bool(Config.B2_KEY_ID and Config.B2_APP_KEY)
    })