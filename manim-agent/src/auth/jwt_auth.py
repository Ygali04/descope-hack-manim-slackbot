import os
import jwt
import requests
from typing import Dict, Any, Set
from fastapi import HTTPException, Request
import structlog

logger = structlog.get_logger()

# Cache for JWKS (in production, use Redis or similar)
_jwks_cache = {}
_cache_ttl = 3600  # 1 hour

def get_jwks() -> Dict[str, Any]:
    """Fetch and cache JWKS from Descope"""
    global _jwks_cache
    
    jwks_url = os.getenv("DESCOPE_JWKS_URL")
    if not jwks_url:
        raise HTTPException(status_code=500, detail="JWKS URL not configured")
    
    try:
        # In production, implement proper caching with TTL
        if not _jwks_cache:
            response = requests.get(jwks_url, timeout=10)
            response.raise_for_status()
            _jwks_cache = response.json()
            logger.info("JWKS fetched and cached")
        
        return _jwks_cache
        
    except requests.RequestException as e:
        logger.error("Failed to fetch JWKS", error=str(e))
        raise HTTPException(status_code=500, detail="Cannot fetch signing keys")

def verify_jwt_token(request: Request) -> Dict[str, Any]:
    """
    Verify JWT token from Authorization header
    Returns decoded token claims if valid
    """
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        # First try development mode (check if token issuer indicates dev)
        unverified_payload = jwt.decode(token, options={"verify_signature": False})
        issuer = unverified_payload.get("iss", "")
        
        if issuer.startswith("dev-descope") or os.getenv("NODE_ENV") == "development":
            # Development mode verification
            logger.info("Using development JWT verification")
            dev_secret = os.getenv("DEV_JWT_SECRET", "manimpro-dev-secret-change-in-production")
            claims = jwt.decode(
                token, 
                dev_secret, 
                algorithms=["HS256"],
                audience=os.getenv("AGENT_B_AUD"),
                options={"verify_exp": True}
            )
            logger.info("Development JWT verified successfully")
            return claims
        
        # Production mode verification with JWKS
        logger.info("Using production JWT verification")
        
        # Get JWKS for verification
        jwks = get_jwks()
        
        # Decode header to get key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(status_code=401, detail="Token missing key ID")
        
        # Find the matching key
        signing_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break
        
        if not signing_key:
            raise HTTPException(status_code=401, detail="Signing key not found")
        
        # Verify token
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=os.getenv("AGENT_B_AUD"),
            options={"verify_exp": True, "verify_aud": True}
        )
        
        logger.info(
            "Production JWT verified",
            subject=claims.get("sub"),
            scopes=claims.get("scope", ""),
            acting_for=claims.get("act", {})
        )
        
        return claims
        
    except jwt.ExpiredSignatureError:
        logger.error("JWT verification error", error="Token expired")
        raise HTTPException(status_code=401, detail="Token has expired")
    
    except jwt.InvalidAudienceError:
        logger.error("JWT verification error", error="Invalid audience")
        raise HTTPException(status_code=401, detail="Invalid token audience")
    
    except jwt.InvalidTokenError as e:
        logger.error("JWT verification error", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid token")
    
    except Exception as e:
        logger.error("JWT verification error", error=str(e))
        raise HTTPException(status_code=500, detail="Token verification failed")

def require_scopes(claims: Dict[str, Any], required_scopes: Set[str]) -> None:
    """
    Verify that the token has required scopes
    Raises HTTPException if scopes are insufficient
    """
    token_scopes = set(claims.get("scope", "").split())
    
    if not required_scopes.issubset(token_scopes):
        missing = required_scopes - token_scopes
        logger.warning(
            "Insufficient scopes",
            required=list(required_scopes),
            provided=list(token_scopes),
            missing=list(missing)
        )
        raise HTTPException(
            status_code=403, 
            detail=f"Insufficient scope. Missing: {', '.join(missing)}"
        )
    
    logger.debug("Scope verification passed", scopes=list(token_scopes))

def extract_acting_user(claims: Dict[str, Any]) -> str:
    """Extract the user this request is acting on behalf of"""
    act_claims = claims.get("act", {})
    return act_claims.get("slack_user_id", claims.get("sub", "unknown"))

def validate_token_claims(claims: Dict[str, Any]) -> None:
    """Validate standard token claims"""
    required_claims = ["sub", "aud", "exp", "iat"]
    missing = [claim for claim in required_claims if claim not in claims]
    
    if missing:
        raise HTTPException(
            status_code=401, 
            detail=f"Token missing required claims: {', '.join(missing)}"
        )
    
    # Validate audience
    expected_aud = os.getenv("AGENT_B_AUD")
    if claims.get("aud") != expected_aud:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid audience. Expected: {expected_aud}"
        ) 