import re
from typing import Dict, Any
import structlog

logger = structlog.get_logger()

def validate_render_request(topic: str, render_params: Dict[str, Any]) -> None:
    """
    Validate a complete render request
    
    Args:
        topic: The educational topic
        render_params: Rendering parameters
        
    Raises:
        ValueError: If any parameter is invalid
    """
    # Validate topic
    if not topic or not isinstance(topic, str):
        raise ValueError("Topic must be a non-empty string")
    
    topic = topic.strip()
    if len(topic) < 3:
        raise ValueError("Topic must be at least 3 characters long")
    
    if len(topic) > 200:
        raise ValueError("Topic must be no more than 200 characters long")
    
    # Check for dangerous content
    if _contains_dangerous_content(topic):
        raise ValueError("Topic contains inappropriate or dangerous content")
    
    # Validate render parameters
    _validate_render_parameters(render_params)
    
    logger.debug("Render request validation passed", topic=topic[:50])

def _contains_dangerous_content(text: str) -> bool:
    """Check if text contains dangerous or inappropriate content"""
    
    # Patterns for potentially dangerous content
    dangerous_patterns = [
        r'\b(exec|eval|compile|__import__|getattr|setattr)\b',
        r'\b(os|sys|subprocess|socket|requests|urllib)\b',
        r'[<>\'"`;\\\n\r]',  # Injection characters
        r'\b(porn|sex|nude|violence|hate|drug|hack|exploit)\b',
        r'<script|javascript:|data:',  # XSS patterns
    ]
    
    text_lower = text.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    
    return False

def _validate_render_parameters(params: Dict[str, Any]) -> None:
    """Validate rendering parameters"""
    
    if not isinstance(params, dict):
        params = {}  # Default to empty dict if not provided
    
    # Validate quality
    quality = params.get('quality', 'medium_quality')
    valid_qualities = ['low_quality', 'medium_quality', 'high_quality', 'production_quality']
    if quality not in valid_qualities:
        raise ValueError(f"Quality must be one of: {', '.join(valid_qualities)}")
    
    # Validate dimensions
    width = params.get('width', 1280)
    height = params.get('height', 720)
    
    if not isinstance(width, int) or width < 480 or width > 1920:
        raise ValueError("Width must be an integer between 480 and 1920")
    
    if not isinstance(height, int) or height < 360 or height > 1080:
        raise ValueError("Height must be an integer between 360 and 1080")
    
    # Validate duration
    duration = params.get('duration_s', 30)
    if not isinstance(duration, (int, float)) or duration < 5 or duration > 300:
        raise ValueError("Duration must be a number between 5 and 300 seconds")
    
    # Validate FPS
    fps = params.get('fps', 30)
    if not isinstance(fps, int) or fps < 15 or fps > 60:
        raise ValueError("FPS must be an integer between 15 and 60")
    
    # Check for reasonable combinations
    total_frames = duration * fps
    if total_frames > 18000:  # 10 minutes at 30fps
        raise ValueError("Total frame count too high - reduce duration or FPS")
    
    pixel_count = width * height
    if pixel_count > 2073600:  # 1920x1080
        raise ValueError("Resolution too high - maximum is 1920x1080")

def sanitize_filename(filename: str) -> str:
    """Sanitize a filename for safe file system usage"""
    # Remove or replace dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
    
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(' .')
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = "video"
    
    # Limit length
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    
    return sanitized

def validate_upload_url(url: str) -> None:
    """Validate that an upload URL is properly formatted and safe"""
    if not url or not isinstance(url, str):
        raise ValueError("Upload URL must be a non-empty string")
    
    # Basic URL validation
    if not url.startswith(('http://', 'https://')):
        raise ValueError("Upload URL must be HTTP or HTTPS")
    
    # Check for Slack domains (additional safety)
    slack_domains = ['files.slack.com', 'slack-files.com', 'slack.com']
    if not any(domain in url for domain in slack_domains):
        logger.warning("Upload URL is not from known Slack domains", url=url[:50])
    
    # Check for obviously malicious URLs
    suspicious_patterns = [
        r'javascript:',
        r'data:',
        r'file:',
        r'ftp:',
        r'localhost',
        r'127\.0\.0\.1',
        r'0\.0\.0\.0'
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            raise ValueError(f"Upload URL contains suspicious pattern: {pattern}")

def get_safe_topic_suggestions() -> list:
    """Return a list of safe, educational topic suggestions"""
    return [
        "simple harmonic motion",
        "quadratic equations",
        "photosynthesis process", 
        "Newton's laws of motion",
        "Pythagorean theorem",
        "cellular respiration",
        "electromagnetic waves",
        "binary search algorithm",
        "derivatives and limits",
        "DNA structure and replication",
        "thermodynamics principles",
        "periodic table trends",
        "geometric transformations",
        "probability distributions",
        "chemical bonding types"
    ] 