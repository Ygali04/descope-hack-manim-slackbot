import os
import tempfile
import subprocess
import asyncio
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()

class SafeRenderer:
    """Secure Manim video renderer with sandboxing and safety controls"""
    
    def __init__(self):
        self.max_duration = int(os.getenv("MAX_RENDER_DURATION", "300"))
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", "100000000"))
        self.output_dir = Path(os.getenv("MANIM_OUTPUT_DIR", "/tmp/manim_output"))
        self.cache_dir = Path(os.getenv("MANIM_CACHE_DIR", "/tmp/manim_cache"))
        
        # Create directories if they don't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def render_video(
        self, 
        script_content: str, 
        render_params: Dict[str, Any], 
        timeout: int = 120
    ) -> bytes:
        """
        Safely render Manim script to video bytes
        
        Args:
            script_content: The Manim Python script content
            render_params: Rendering parameters (quality, dimensions, etc.)
            timeout: Maximum time to allow for rendering
            
        Returns:
            bytes: The rendered MP4 video file bytes
        """
        
        # Validate render parameters
        self._validate_render_params(render_params)
        
        # Create isolated temporary directory for this render
        with tempfile.TemporaryDirectory(prefix="manim_render_") as temp_dir:
            temp_path = Path(temp_dir)
            
            try:
                # Write script to file
                script_path = temp_path / "educational_video.py"
                script_path.write_text(script_content)
                
                # Prepare Manim command
                cmd = self._build_manim_command(script_path, render_params, temp_path)
                
                logger.info("Starting Manim render", cmd=cmd, timeout=timeout)
                
                # Execute Manim in isolated environment
                result = await self._execute_manim_safely(cmd, timeout)
                
                # Find and read the output video
                video_bytes = await self._extract_video_bytes(temp_path)
                
                logger.info("Render completed successfully", video_size=len(video_bytes))
                return video_bytes
                
            except Exception as e:
                logger.error("Render failed", error=str(e), temp_dir=temp_dir)
                raise

    def _validate_render_params(self, params: Dict[str, Any]) -> None:
        """Validate rendering parameters for safety"""
        duration = params.get('duration_s', 30)
        if duration > self.max_duration:
            raise ValueError(f"Duration {duration}s exceeds maximum {self.max_duration}s")
        
        width = params.get('width', 1280)
        height = params.get('height', 720)
        
        # Reasonable resolution limits
        if width > 1920 or height > 1080:
            raise ValueError(f"Resolution {width}x{height} exceeds maximum 1920x1080")
        
        if width < 480 or height < 360:
            raise ValueError(f"Resolution {width}x{height} below minimum 480x360")

    def _build_manim_command(
        self, 
        script_path: Path, 
        render_params: Dict[str, Any], 
        output_dir: Path
    ) -> list:
        """Build safe Manim command with appropriate flags"""
        
        # Base command
        cmd = ["manim"]
        
        # Quality settings
        quality = render_params.get('quality', 'medium_quality')
        quality_flags = {
            'low_quality': ['-ql'],
            'medium_quality': ['-qm'], 
            'high_quality': ['-qh'],
            'production_quality': ['-qk']  # 4K - careful with this
        }
        cmd.extend(quality_flags.get(quality, ['-qm']))
        
        # Output directory
        cmd.extend(['--media_dir', str(output_dir)])
        
        # Disable preview window (headless)
        cmd.append('--disable_caching')
        cmd.append('--verbose')
        
        # Custom resolution if specified
        width = render_params.get('width')
        height = render_params.get('height')
        if width and height:
            cmd.extend(['--resolution', f'{width},{height}'])
        
        # Frame rate
        fps = render_params.get('fps', 30)
        cmd.extend(['--frame_rate', str(fps)])
        
        # Output format
        cmd.extend(['--format', 'mp4'])
        
        # Script and scene
        cmd.extend([str(script_path), 'EducationalVideo'])
        
        return cmd

    async def _execute_manim_safely(self, cmd: list, timeout: int) -> subprocess.CompletedProcess:
        """Execute Manim command with safety controls"""
        
        # Set up safe environment
        env = os.environ.copy()
        env.update({
            'MANIM_DISABLE_TELEMETRY': '1',
            'PYTHONPATH': '',  # Clear Python path for security
            'PATH': '/usr/local/bin:/usr/bin:/bin',  # Minimal PATH
        })
        
        try:
            # Run with timeout and resource limits
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd='/',  # Run from root to avoid path issues
                preexec_fn=self._setup_process_limits if os.name != 'nt' else None
            )
            
            # Wait with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=timeout
            )
            
            if process.returncode != 0:
                error_output = stderr.decode('utf-8', errors='replace')
                logger.error("Manim render failed", 
                           returncode=process.returncode, 
                           stderr=error_output)
                raise subprocess.CalledProcessError(
                    process.returncode, cmd, output=stdout, stderr=stderr
                )
            
            logger.debug("Manim render successful", stdout_lines=len(stdout.splitlines()))
            return subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)
            
        except asyncio.TimeoutError:
            logger.error("Render timeout", timeout=timeout)
            if 'process' in locals():
                process.terminate()
                await asyncio.sleep(1)
                if process.returncode is None:
                    process.kill()
            raise subprocess.TimeoutExpired(cmd, timeout)

    def _setup_process_limits(self):
        """Set up resource limits for the render process (Unix only)"""
        try:
            import resource
            # Limit CPU time (seconds)
            resource.setrlimit(resource.RLIMIT_CPU, (300, 300))  # 5 minutes max
            # Limit memory (bytes) - 2GB
            resource.setrlimit(resource.RLIMIT_AS, (2**31, 2**31))
            # Limit number of processes
            resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))
        except ImportError:
            # Windows doesn't have resource module
            pass

    async def _extract_video_bytes(self, temp_dir: Path) -> bytes:
        """Find and extract the rendered video file"""
        
        # Manim typically outputs to media/videos/script_name/quality/
        # Look for MP4 files recursively
        video_files = list(temp_dir.rglob("*.mp4"))
        
        if not video_files:
            logger.error("No video output found", temp_dir=str(temp_dir))
            raise FileNotFoundError("Manim did not produce any video output")
        
        # Take the first (and should be only) video file
        video_file = video_files[0]
        
        # Check file size
        file_size = video_file.stat().st_size
        if file_size > self.max_file_size:
            raise ValueError(f"Video file too large: {file_size} bytes > {self.max_file_size}")
        
        if file_size == 0:
            raise ValueError("Video file is empty")
        
        logger.info("Found video output", file=str(video_file), size=file_size)
        
        # Read and return file bytes
        return video_file.read_bytes()

    def get_render_info(self, render_params: Dict[str, Any]) -> Dict[str, Any]:
        """Get information about what will be rendered"""
        return {
            'quality': render_params.get('quality', 'medium_quality'),
            'resolution': f"{render_params.get('width', 1280)}x{render_params.get('height', 720)}",
            'fps': render_params.get('fps', 30),
            'duration_s': render_params.get('duration_s', 30),
            'estimated_size_mb': self._estimate_file_size(render_params)
        }

    def _estimate_file_size(self, render_params: Dict[str, Any]) -> float:
        """Estimate output file size in MB"""
        width = render_params.get('width', 1280)
        height = render_params.get('height', 720)
        duration = render_params.get('duration_s', 30)
        fps = render_params.get('fps', 30)
        quality = render_params.get('quality', 'medium_quality')
        
        # Rough estimation based on typical Manim output
        pixels_per_frame = width * height
        frames = duration * fps
        
        # Bytes per pixel varies by quality
        quality_multipliers = {
            'low_quality': 0.01,
            'medium_quality': 0.03,
            'high_quality': 0.08,
            'production_quality': 0.15
        }
        
        multiplier = quality_multipliers.get(quality, 0.03)
        estimated_bytes = pixels_per_frame * frames * multiplier
        
        return round(estimated_bytes / (1024 * 1024), 2)  # Convert to MB 