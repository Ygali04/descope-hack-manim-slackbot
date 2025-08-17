/**
 * Validates if a topic is appropriate for educational video generation
 * @param {string} topic - The requested topic
 * @returns {boolean} True if topic is valid and appropriate
 */
function validateTopic(topic) {
  if (!topic || typeof topic !== 'string') {
    return false;
  }

  const trimmed = topic.trim();
  
  // Basic length checks
  if (trimmed.length < 3 || trimmed.length > 200) {
    return false;
  }

  // Forbidden patterns (inappropriate content)
  const forbidden = [
    /\b(porn|sex|nude|naked|explicit)\b/i,
    /\b(violence|murder|kill|bomb|weapon)\b/i,
    /\b(hate|racism|nazi|terrorist)\b/i,
    /\b(drug|cocaine|heroin|meth)\b/i,
    /\b(hack|exploit|virus|malware)\b/i,
    /<script|javascript:|data:/i, // XSS attempts
    /\b(exec|eval|system|shell)\b/i // Code injection attempts
  ];

  if (forbidden.some(pattern => pattern.test(trimmed))) {
    return false;
  }

  // Educational topic patterns (encourage these)
  const educational = [
    /\b(math|physics|chemistry|biology|science|calculus|algebra|geometry)\b/i,
    /\b(history|literature|language|art|music|philosophy)\b/i,
    /\b(programming|computer|algorithm|data|statistics)\b/i,
    /\b(motion|wave|energy|force|gravity|momentum|friction)\b/i,
    /\b(equation|formula|theorem|proof|principle|law)\b/i,
    /\b(learn|understand|explain|demonstrate|illustrate)\b/i
  ];

  // If it matches educational patterns, it's definitely good
  if (educational.some(pattern => pattern.test(trimmed))) {
    return true;
  }

  // For other topics, be more permissive but check for basic sanity
  // Allow general academic topics, avoid obvious non-educational requests
  const nonEducational = [
    /\b(meme|funny|joke|entertainment|celebrity|gossip)\b/i,
    /\b(personal|private|secret|password|login)\b/i,
    /\b(download|pirate|crack|torrent)\b/i
  ];

  if (nonEducational.some(pattern => pattern.test(trimmed))) {
    return false;
  }

  return true;
}

/**
 * Sanitizes a topic string for safe filename generation
 * @param {string} topic - The topic to sanitize
 * @returns {string} Sanitized topic suitable for filenames
 */
function sanitizeTopicForFilename(topic) {
  return topic
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '') // Remove special chars except spaces and hyphens
    .replace(/\s+/g, '_') // Replace spaces with underscores
    .replace(/_+/g, '_') // Collapse multiple underscores
    .substring(0, 50) // Limit length
    .replace(/^_|_$/g, ''); // Remove leading/trailing underscores
}

/**
 * Generates suggested topics for users
 * @returns {Array<string>} Array of educational topic suggestions
 */
function getSuggestedTopics() {
  return [
    "simple harmonic motion",
    "quadratic equations",
    "photosynthesis process",
    "Newton's laws of motion",
    "Pythagorean theorem",
    "cellular respiration",
    "electromagnetic waves",
    "sorting algorithms",
    "derivatives and integrals",
    "DNA replication",
    "thermodynamics",
    "periodic table trends",
    "binary search trees",
    "geometric transformations",
    "chemical bonding"
  ];
}

/**
 * Validates render parameters
 * @param {Object} params - Render parameters
 * @returns {boolean} True if parameters are valid
 */
function validateRenderParams(params) {
  if (!params || typeof params !== 'object') {
    return false;
  }

  // Check video dimensions
  if (params.width && (params.width < 480 || params.width > 1920)) {
    return false;
  }
  
  if (params.height && (params.height < 360 || params.height > 1080)) {
    return false;
  }

  // Check duration (max 5 minutes for safety)
  if (params.duration_s && (params.duration_s < 5 || params.duration_s > 300)) {
    return false;
  }

  // Check FPS
  if (params.fps && (params.fps < 15 || params.fps > 60)) {
    return false;
  }

  return true;
}

module.exports = {
  validateTopic,
  sanitizeTopicForFilename,
  getSuggestedTopics,
  validateRenderParams
}; 