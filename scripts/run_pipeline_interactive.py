#!/usr/bin/env python
"""
Interactive script for running the CiteCast pipeline.
Allows selecting document, audience, and viewing results.
"""

import os
import sys
import json
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.pipeline import CiteCastPipeline
from app.utils.config import Config

console = Console()

def list_pdfs():
    """List available PDFs in test_data."""
    test_dir = Path("test_data")
    if not test_dir.exists():
        return []
    return list(test_dir.glob("*.pdf"))

def display_status(status):
    """Display job status in a nice table."""
    table = Table(title="Job Status")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="green")
    
    for key, value in status.items():
        if isinstance(value, (dict, list)):
            value = json.dumps(value, indent=2)[:100]
        table.add_row(key, str(value))
    
    console.print(table)

def main():
    """Interactive pipeline runner."""
    console.print("[bold blue]🎬 CiteCast Pipeline Interactive Runner[/bold blue]")
    console.print("=" * 60)
    
    # Check for sample PDFs
    pdfs = list_pdfs()
    if not pdfs:
        console.print("[red]❌ No PDF files found in test_data/[/red]")
        console.print("Please place a sample PDF in test_data/")
        return
    
    # Select PDF
    console.print("\n[bold]Available PDFs:[/bold]")
    for i, pdf in enumerate(pdfs):
        console.print(f"  {i+1}. {pdf.name}")
    
    choice = Prompt.ask("Select PDF number", default="1")
    try:
        pdf_path = str(pdfs[int(choice) - 1])
    except (ValueError, IndexError):
        console.print("[red]Invalid selection[/red]")
        return
    
    # Select audience
    audiences = {
        "1": "executive",
        "2": "engineer", 
        "3": "student"
    }
    
    console.print("\n[bold]Select Audience:[/bold]")
    console.print("  1. Executive (Business/Strategic)")
    console.print("  2. Engineer (Technical/Detailed)")
    console.print("  3. Student (Simplified/Educational)")
    
    audience_choice = Prompt.ask("Select audience", choices=["1", "2", "3"], default="1")
    audience = audiences[audience_choice]
    
    # Number of scenes
    num_scenes = Prompt.ask("Number of scenes", default="5")
    try:
        num_scenes = int(num_scenes)
    except ValueError:
        num_scenes = 5
    
    # Confirm
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Document: {Path(pdf_path).name}")
    console.print(f"  Audience: {audience}")
    console.print(f"  Scenes: {num_scenes}")
    
    if not Confirm.ask("Proceed with pipeline run?", default=True):
        console.print("Cancelled")
        return
    
    # Initialize pipeline
    console.print("\n[bold yellow]🚀 Initializing pipeline...[/bold yellow]")
    pipeline = CiteCastPipeline()
    
    # Create job
    job_id = pipeline.create_job(pdf_path, audience=audience, num_scenes=num_scenes)
    console.print(f"✅ Created job: [bold]{job_id}[/bold]")
    
    # Run pipeline with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running pipeline...", total=None)
        
        try:
            start_time = time.time()
            result = pipeline.run_pipeline(job_id)
            elapsed = time.time() - start_time
            
            progress.update(task, completed=True)
            
            console.print(f"\n[bold green]✅ Pipeline completed in {elapsed:.2f}s[/bold green]")
            console.print(f"  Total Scenes: {result['total_scenes']}")
            console.print(f"  Total Citations: {result['total_citations']}")
            
            # Show status
            status = pipeline.get_job_status(job_id)
            if status:
                display_status(status)
            
            # Ask if user wants to view manifest
            if Confirm.ask("View full manifest?", default=False):
                manifest = pipeline.b2_client.download_json(status['manifest_path'])
                console.print_json(json.dumps(manifest))
            
            # Ask if user wants to download assets
            if Confirm.ask("Download generated assets to local?", default=False):
                output_dir = f"downloaded_assets/{job_id}"
                os.makedirs(output_dir, exist_ok=True)
                console.print(f"📥 Downloading assets to: {output_dir}")
                
                # List and download files
                prefix = status['output_path']
                files = pipeline.b2_client.list_files(prefix)
                
                for file in files:
                    local_path = os.path.join(output_dir, os.path.basename(file))
                    pipeline.b2_client.download_file(file, local_path)
                    console.print(f"  Downloaded: {os.path.basename(file)}")
                
                console.print("[green]✅ Assets downloaded![/green]")
                
        except Exception as e:
            console.print(f"\n[bold red]❌ Pipeline failed: {e}[/bold red]")
            status = pipeline.get_job_status(job_id)
            if status:
                console.print(f"Error: {status.get('error', 'Unknown error')}")

if __name__ == "__main__":
    main()