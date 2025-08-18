import os
import sys
import asyncio
import tempfile
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

import structlog
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from dotenv import load_dotenv

from auth.jwt_auth import verify_jwt_token, require_scopes
from render.manim_generator import ManimGenerator
from render.safe_renderer import SafeRenderer
from mcp.server import MCPServer
from utils.validation import validate_render_request
from utils.file_upload import upload_to_slack_url

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Initialize FastAPI app
app = FastAPI(
    title="ManimPro Agent B",
    description="Secure Manim video generation service with MCP support",
    version="1.0.0",
    docs_url="/docs" if os.getenv("DEBUG", "false").lower() == "true" else None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_HOSTS", "localhost").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Initialize components
manim_generator = ManimGenerator()
safe_renderer = SafeRenderer()
mcp_server = MCPServer()

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting ManimPro Agent B")
    
    # Create necessary directories
    output_dir = Path(os.getenv("MANIM_OUTPUT_DIR", "/tmp/manim_output"))
    cache_dir = Path(os.getenv("MANIM_CACHE_DIR", "/tmp/manim_cache"))
    
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Directories created", output_dir=str(output_dir), cache_dir=str(cache_dir))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "manimpro-agent-b"}

@app.get("/mcp/capabilities")
async def mcp_capabilities():
    """MCP server capabilities endpoint"""
    return mcp_server.get_capabilities()

@app.post("/tools/generate_and_render")
async def generate_and_render(
    request: Request,
    token_claims: Dict[str, Any] = Depends(verify_jwt_token)
):
    """
    Main MCP tool: Generate Manim code and render video
    Requires scopes: video.create, manim.render
    """
    # Verify required scopes
    require_scopes(token_claims, {"video.create", "manim.render"})
    
    # Parse request body
    try:
        body = await request.json()
        topic = body["topic"]
        upload_url = body.get("upload_url")  # Optional for backwards compatibility
        file_id = body.get("file_id")        # Optional for backwards compatibility
        render_params = body.get("render", {})
        
        # Validate request
        validate_render_request(topic, render_params)
        
        logger.info(
            "Render request received",
            topic=topic,
            user=token_claims.get("act", {}).get("slack_user_id"),
            subject=token_claims.get("sub")
        )
        
    except (KeyError, ValueError) as e:
        logger.error("Invalid request", error=str(e))
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")
    
    try:
        # 1) Generate safe Manim script from topic
        script_content = await manim_generator.generate_script(topic, render_params)
        logger.info("Generated Manim script", topic=topic, script_length=len(script_content))
        
        # 2) Render video safely
        video_bytes = await safe_renderer.render_video(
            script_content=script_content,
            render_params=render_params,
            timeout=int(os.getenv("MANIM_TIMEOUT", "120"))
        )
        logger.info("Rendered video", topic=topic, video_size=len(video_bytes))
        
        # 3) Return video bytes as base64 for direct upload by Slack agent
        import base64
        video_base64 = base64.b64encode(video_bytes).decode('utf-8')
        
        logger.info("Video encoded for direct upload", topic=topic, video_size=len(video_bytes))
        
        return {
            "ok": True,
            "topic": topic,
            "video_size": len(video_bytes),
            "video_base64": video_base64,
            "actor": token_claims.get("sub"),
            "acting_for": token_claims.get("act", {}).get("slack_user_id")
        }
        
    except subprocess.TimeoutExpired:
        logger.error("Render timeout", topic=topic)
        raise HTTPException(status_code=408, detail="Video rendering timed out")
    
    except subprocess.CalledProcessError as e:
        logger.error("Render failed", topic=topic, error=str(e))
        raise HTTPException(status_code=500, detail="Video rendering failed")
    
    except Exception as e:
        logger.error("Unexpected error", topic=topic, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/mcp/tools/call")
async def mcp_tool_call(
    request: Request,
    token_claims: Dict[str, Any] = Depends(verify_jwt_token)
):
    """MCP-compliant tool call endpoint"""
    try:
        body = await request.json()
        tool_name = body.get("name")
        tool_args = body.get("arguments", {})
        
        if tool_name == "generate_and_render":
            # Route to our main tool
            return await generate_and_render(request, token_claims)
        else:
            raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
            
    except Exception as e:
        logger.error("MCP tool call error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with logging"""
    logger.warning(
        "HTTP exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

if __name__ == "__main__":
    # Configure uvicorn
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        workers=1,  # Single worker for simplicity in development
        log_config=log_config,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    ) 