const axios = require('axios');
const jwt = require('jsonwebtoken');

/**
 * Issues a delegated JWT from Descope for calling Agent B
 * @param {Object} params - Token parameters
 * @param {string} params.audience - Target audience (Agent B)
 * @param {string} params.scope - Space-separated scopes
 * @param {string} params.subject - Issuing agent identifier
 * @param {Object} params.actingFor - Acting on behalf of claims
 * @param {number} params.ttl - Time to live in seconds
 * @returns {Promise<string>} Signed JWT token
 */
async function issueDelegatedJwtFromDescope({
  audience,
  scope,
  subject,
  actingFor,
  ttl = 600
}) {
  try {
    const now = Math.floor(Date.now() / 1000);
    
    // Create JWT payload following Descope conventions
    const payload = {
      iss: `https://api.descope.com/v1/${process.env.DESCOPE_PROJECT_ID}`,
      sub: subject,
      aud: audience,
      exp: now + ttl,
      iat: now,
      nbf: now,
      scope: scope,
      azp: process.env.DESCOPE_PROJECT_ID, // authorized party
      act: actingFor, // acting claims (on-behalf-of)
      jti: `manimpro-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    };

    // For production, you'd call Descope's token endpoint
    // For now, we'll create a local JWT (you'll need to coordinate the signing key)
    const descopeEndpoint = `https://api.descope.com/v1/auth/token`;
    
    const response = await axios.post(descopeEndpoint, {
      grant_type: 'client_credentials',
      scope: scope,
      audience: audience,
      acting_party: actingFor,
      expires_in: ttl
    }, {
      headers: {
        'Authorization': `Bearer ${process.env.DESCOPE_MANAGEMENT_KEY}`,
        'Content-Type': 'application/json'
      }
    });

    return response.data.access_token;

  } catch (error) {
    console.error('Descope token delegation failed:', error.response?.data || error.message);
    
    // Fallback: Create a local JWT for development (NOT for production)
    if (process.env.NODE_ENV === 'development') {
      console.warn('⚠️  Using development JWT fallback - NOT secure for production!');
      return createDevelopmentJWT({ audience, scope, subject, actingFor, ttl });
    }
    
    throw new Error('Failed to obtain delegated token from Descope');
  }
}

/**
 * Development-only JWT creation (NOT for production use)
 */
function createDevelopmentJWT({ audience, scope, subject, actingFor, ttl }) {
  const now = Math.floor(Date.now() / 1000);
  
  const payload = {
    iss: `dev-descope-${process.env.DESCOPE_PROJECT_ID}`,
    sub: subject,
    aud: audience,
    exp: now + ttl,
    iat: now,
    nbf: now,
    scope: scope,
    azp: process.env.DESCOPE_PROJECT_ID,
    act: actingFor,
    jti: `dev-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  };

  // Use a development secret (Agent B will need the same)
  const devSecret = process.env.DEV_JWT_SECRET || 'manimpro-dev-secret-change-in-production';
  
  return jwt.sign(payload, devSecret, { algorithm: 'HS256' });
}

/**
 * Validates environment configuration for Descope
 */
function validateDescopeConfig() {
  const required = ['DESCOPE_PROJECT_ID', 'AGENT_B_AUD'];
  const missing = required.filter(key => !process.env[key]);
  
  if (missing.length > 0) {
    throw new Error(`Missing required Descope environment variables: ${missing.join(', ')}`);
  }

  if (process.env.NODE_ENV === 'production' && !process.env.DESCOPE_MANAGEMENT_KEY) {
    throw new Error('DESCOPE_MANAGEMENT_KEY is required in production');
  }
}

module.exports = {
  issueDelegatedJwtFromDescope,
  validateDescopeConfig
}; 