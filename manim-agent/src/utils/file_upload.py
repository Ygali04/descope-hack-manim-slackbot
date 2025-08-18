import asyncio
import aiohttp
from typing import Optional
import structlog

logger = structlog.get_logger()

async def upload_to_slack_url(upload_url: str, video_bytes: bytes) -> bool:
    """
    Upload video bytes to Slack's pre-signed URL
    
    Args:
        upload_url: Pre-signed URL from Slack's getUploadURLExternal
        video_bytes: The video file as bytes
        
    Returns:
        bool: True if upload successful, False otherwise
    """
    
    if not upload_url or not video_bytes:
        logger.error("Missing upload URL or video bytes")
        return False
    
    if len(video_bytes) == 0:
        logger.error("Video bytes are empty")
        return False
    
    logger.info("Starting upload to Slack", url=upload_url[:50], size=len(video_bytes))
    
    try:
        timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            
            # Prepare headers for upload
            headers = {
                'Content-Type': 'application/octet-stream',
                'Content-Length': str(len(video_bytes))
            }
            
            # Upload using PUT first (Slack typically expects PUT for pre-signed URLs)
            # Then try POST as fallback
            methods_to_try = ['PUT', 'POST']
            
            for method in methods_to_try:
                try:
                    logger.debug(f"Attempting upload with {method}", method=method)
                    
                    async with session.request(
                        method=method,
                        url=upload_url,
                        data=video_bytes,
                        headers=headers
                    ) as response:
                        
                        response_text = await response.text()
                        
                        if response.status in (200, 201, 204):
                            logger.info("Upload successful", 
                                      method=method,
                                      status=response.status,
                                      response_size=len(response_text))
                            return True
                        
                        elif response.status in (405, 501):
                            # Method not allowed - try the other method
                            logger.info(f"{method} not allowed, trying next method",
                                       method=method,
                                       status=response.status)
                            continue
                        
                        else:
                            # For server errors (5xx), try the other method
                            # For client errors (4xx), don't retry
                            if 500 <= response.status < 600:
                                logger.warning("Server error, trying next method",
                                             method=method,
                                             status=response.status,
                                             response=response_text[:100])
                                continue
                            else:
                                logger.error("Upload failed",
                                           method=method,
                                           status=response.status,
                                           response=response_text[:500])
                                return False
                            
                except aiohttp.ClientError as e:
                    logger.error(f"Client error during {method} upload", 
                               method=method, error=str(e))
                    continue
                    
                except Exception as e:
                    logger.error(f"Unexpected error during {method} upload",
                               method=method, error=str(e))
                    continue
            
            # If we get here, all methods failed
            logger.error("All upload methods failed")
            return False
            
    except asyncio.TimeoutError:
        logger.error("Upload timeout")
        return False
        
    except Exception as e:
        logger.error("Upload failed with exception", error=str(e), exc_info=True)
        return False

async def verify_upload_url(upload_url: str) -> bool:
    """
    Verify that an upload URL is reachable (optional safety check)
    
    Args:
        upload_url: The pre-signed URL to verify
        
    Returns:
        bool: True if URL appears valid and reachable
    """
    
    if not upload_url:
        return False
    
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # Short timeout for verification
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Try a HEAD request to verify the URL without uploading
            async with session.head(upload_url) as response:
                # Most pre-signed URLs will return 405 (Method Not Allowed) for HEAD
                # but that still means the URL is valid and reachable
                if response.status in (200, 405, 501):
                    logger.debug("Upload URL verification successful", 
                               status=response.status)
                    return True
                else:
                    logger.warning("Upload URL verification failed",
                                 status=response.status)
                    return False
                    
    except Exception as e:
        logger.warning("Upload URL verification error", error=str(e))
        return False

def estimate_upload_time(file_size_bytes: int, bandwidth_mbps: float = 10.0) -> float:
    """
    Estimate upload time based on file size and assumed bandwidth
    
    Args:
        file_size_bytes: Size of file in bytes
        bandwidth_mbps: Assumed upload bandwidth in Mbps
        
    Returns:
        float: Estimated upload time in seconds
    """
    
    # Convert Mbps to bytes per second
    bandwidth_bytes_per_sec = (bandwidth_mbps * 1_000_000) / 8
    
    # Calculate base upload time
    base_time = file_size_bytes / bandwidth_bytes_per_sec
    
    # Add overhead factor (network latency, protocol overhead, etc.)
    overhead_factor = 1.5
    
    estimated_time = base_time * overhead_factor
    
    # Minimum 1 second, maximum 300 seconds (5 minutes)
    return max(1.0, min(estimated_time, 300.0))

def get_upload_progress_callback():
    """
    Create a callback function for tracking upload progress
    (Would be used with more advanced upload libraries)
    """
    
    def progress_callback(bytes_uploaded: int, total_bytes: int):
        if total_bytes > 0:
            percent = (bytes_uploaded / total_bytes) * 100
            logger.debug("Upload progress", 
                        uploaded=bytes_uploaded, 
                        total=total_bytes, 
                        percent=round(percent, 1))
    
    return progress_callback 