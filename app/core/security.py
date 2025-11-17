"""
JWT token validation and user authentication.
Extracts user_id and subscription_level from JWT tokens.
"""
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Dict, Optional
import structlog

from app.config import settings

logger = structlog.get_logger()
security = HTTPBearer()

class TokenData:
    """Parsed JWT token data"""
    def __init__(self, user_id: str, email: str, subscription_level: str = "free", org_id: Optional[str] = None):
        self.user_id = user_id
        self.email = email
        self.subscription_level = subscription_level
        self.org_id = org_id

def verify_jwt_token(token: str) -> Dict:
    """
    Verify JWT token signature and expiration.

    Returns:
        Dict with token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning("invalid_jwt_token", error=str(e))
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> TokenData:
    """
    FastAPI dependency to extract and validate user from JWT token.

    Usage in routes:
        async def endpoint(current_user: TokenData = Depends(get_current_user)):
            user_id = current_user.user_id
    """
    token = credentials.credentials
    payload = verify_jwt_token(token)

    # Extract required fields
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Extract optional fields (email not required in minimal JWT from auth-api)
    email = payload.get("email", "unknown@example.com")
    subscription_level = payload.get("subscription_level", "free")
    org_id = payload.get("org_id")

    return TokenData(
        user_id=user_id,
        email=email,
        subscription_level=subscription_level,
        org_id=org_id
    )

def verify_service_token(token: str) -> bool:
    """
    Verify internal service-to-service token.
    Used for POST /notifications endpoint.
    """
    return token == settings.SERVICE_TOKEN
