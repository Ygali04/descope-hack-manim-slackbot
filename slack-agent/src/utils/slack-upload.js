/**
 * Utilities for Slack file upload using the modern external upload flow
 * Note: Main logic is in app.js, this provides helper functions
 */

/**
 * Generates a safe filename for Slack upload
 * @param {string} topic - The topic for the video
 * @param {string} extension - File extension (default: 'mp4')
 * @returns {string} Safe filename
 */
function generateSafeFilename(topic, extension = 'mp4') {
  const sanitized = topic
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '_')
    .substring(0, 30);
    
  const timestamp = Date.now();
  return `manim_${sanitized}_${timestamp}.${extension}`;
}

/**
 * Estimates file size for Slack upload reservation
 * @param {Object} renderParams - Render parameters
 * @returns {number} Estimated file size in bytes
 */
function estimateFileSize(renderParams) {
  const {
    width = 1280,
    height = 720,
    duration_s = 30,
    fps = 30,
    quality = 'medium'
  } = renderParams;

  // Very conservative estimation for Slack upload reservation
  // We'll use a small initial estimate - Slack allows resize during upload
  // For educational animations (mostly simple graphics), Manim produces small files
  
  // Base size calculation for simple animations
  let baseSize;
  switch (quality) {
    case 'low': baseSize = 200_000; break;      // 200KB
    case 'medium': baseSize = 500_000; break;   // 500KB  
    case 'high': baseSize = 1_000_000; break;   // 1MB
    default: baseSize = 500_000;                // 500KB
  }
  
  // Scale by duration (but cap it reasonably)
  const durationFactor = Math.min(duration_s / 10, 3); // Max 3x for longer videos
  const estimatedSize = baseSize * durationFactor;
  
  // Conservative cap at 1MB for initial Slack reservation
  // Slack can handle larger files during actual upload
  return Math.min(estimatedSize, 1_000_000);
}

/**
 * Validates Slack file upload response
 * @param {Object} response - Slack API response
 * @returns {boolean} True if response is valid
 */
function validateUploadResponse(response) {
  return response && 
         response.ok && 
         response.upload_url && 
         response.file_id;
}

/**
 * Handles upload errors with appropriate user messages
 * @param {Error} error - The upload error
 * @returns {string} User-friendly error message
 */
function getUploadErrorMessage(error) {
  if (error.response?.status === 413) {
    return 'Video file is too large for Slack. Please try a shorter duration or lower quality.';
  }
  
  if (error.response?.status === 429) {
    return 'Rate limit reached. Please wait a moment before trying again.';
  }
  
  if (error.code === 'ECONNABORTED') {
    return 'Upload timed out. The video might be too large or network is slow.';
  }
  
  if (error.message?.includes('invalid_auth')) {
    return 'Authentication error. Please contact an administrator.';
  }
  
  return 'Upload failed. Please try again or contact support if the problem persists.';
}

/**
 * Slack file size limits and recommendations
 */
const SLACK_LIMITS = {
  MAX_FILE_SIZE: 1_000_000_000, // 1GB
  RECOMMENDED_MAX: 100_000_000,  // 100MB for good performance
  SUPPORTED_VIDEO_FORMATS: ['mp4', 'mov', 'avi', 'mkv', 'webm'],
  OPTIMAL_DURATION: 60, // seconds
  MAX_REASONABLE_DURATION: 300 // 5 minutes
};

module.exports = {
  generateSafeFilename,
  estimateFileSize,
  validateUploadResponse,
  getUploadErrorMessage,
  SLACK_LIMITS
}; 