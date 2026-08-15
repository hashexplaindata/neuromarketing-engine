"""
Authentication & Appwrite JWT Verification Layer
Zero Billing Constraints - Direct Figma Plugin Identity Resolution
"""

import time
import json
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from core.config import settings
from core.appwrite_service import appwrite_service

logger = logging.getLogger("icm.auth")

try:
    import jwt
except ImportError:
    jwt = None

@dataclass
class AuthenticatedUser:
    user_id: str
    tenant_id: str
    email: str
    name: str = "Designer"

def create_access_token(tenant_id: str, user_id: str, email: str, expires_in_seconds: int = 3600) -> str:
    """Helper to create a standard signed token for client tests & Figma plugin."""
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "email": email,
        "exp": int(time.time()) + expires_in_seconds,
        "iat": int(time.time()),
        "iss": "neuromarketing-engine"
    }
    if jwt:
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
    else:
        import base64
        return f"mock.header.{base64.b64encode(json.dumps(payload).encode()).decode()}.signature"

def verify_jwt_token(token: str) -> AuthenticatedUser:
    """
    Verifies Appwrite JWT token and extracts tenant identity.
    Throws ValueError on invalid or expired token.
    """
    if not token:
        raise ValueError("Missing authentication token")
    
    if token.startswith("Bearer ") or token.startswith("bearer "):
        token = token[7:].strip()
        
    # 1. Dev/Test Mock bypass token format: "test_tenant_{tenant_id}"
    if token.startswith("test_tenant_"):
        tenant_id = token.replace("test_tenant_", "").strip()
        return AuthenticatedUser(
            user_id="usr_dev_001",
            tenant_id=tenant_id,
            email=f"dev@{tenant_id}.com",
            name="Figma Designer"
        )

    # 2. Try Appwrite JWT Verification
    try:
        user_info = appwrite_service.verify_appwrite_jwt(token)
        return AuthenticatedUser(
            user_id=user_info["user_id"],
            tenant_id=user_info["tenant_id"],
            email=user_info["email"],
            name=user_info.get("name", "Figma User")
        )
    except ValueError as val_err:
        if "Invalid or expired" in str(val_err):
            raise val_err

    # 3. Standard HS256 verification (for signed client test tokens)
    if jwt:
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_exp": True}
            )
            user_id = payload.get("sub", "usr_unknown")
            tenant_id = payload.get("tenant_id", f"tenant_{user_id[:8]}")
            email = payload.get("email", "designer@agency.com")
            return AuthenticatedUser(
                user_id=user_id,
                tenant_id=tenant_id,
                email=email,
                name="Figma User"
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Authentication token has expired")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid authentication token: {e}")

    raise ValueError("Unable to verify authentication token")
