"""
Video assembly module for combining images and audio into a final video.
This is an optional enhancement for the full video output.
"""

import subprocess
import os
from typing import List, Dict, Any
from PIL import Image
import numpy as np

from app.utils.logging import get_logger

logger = get_logger(__name__)


class VideoAssembler:
    """
    Assembles images and audio into a video using FFmpeg.
    """
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """Check if FFmpeg is installed."""
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning("FFmpeg not found. Video assembly will be disabled.")
            self.ffmpeg_available = False
        else:
            self.ffmpeg_available = True
    
    def assemble_video(
        self,
        images: List[str],
        audio_files: List[str],
        output_path: str,
        fps: int = 1,
        duration_per_scene: float = 3.0
    ) -> bool:
        """
        Assemble images and audio into a video.
        
        Args:
            images: List of image file paths
            audio_files: List of audio file paths
            output_path: Output video path
            fps: Frames per second for slideshow
            duration_per_scene: Duration per scene in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.ffmpeg_available:
            logger.error("FFmpeg not available")
            return False
        
        if len(images) != len(audio_files):
            logger.error("Number of images and audio files must match")
            return False
        
        try:
            # Create a temporary directory for intermediate files
            temp_dir = os.path.dirname(output_path) or "."
            
            # Generate a concat file for FFmpeg
            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, 'w') as f:
                for i, (image_path, audio_path) in enumerate(zip(images, audio_files)):
                    f.write(f"file '{image_path}'\n")
                    f.write(f"duration {duration_per_scene}\n")
            
            # Build FFmpeg command
            cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-i", "concat:" + "|".join(audio_files),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                "-shortest",
                "-y",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Clean up
            os.remove(concat_file)
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                return False
            
            logger.info(f"Video assembled: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Video assembly failed: {e}")
            return False