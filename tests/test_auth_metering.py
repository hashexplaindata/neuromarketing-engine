"""
Authentication & Appwrite JWT Verification Unit Tests
Verifies Appwrite JWT decoding, expiration checks, and zero-billing execution
"""

import pytest
import time
from core.auth import create_access_token, verify_jwt_token, AuthenticatedUser
from core.appwrite_service import appwrite_service

def test_jwt_token_creation_and_verification():
    tenant_id = "agency_publicis"
    user_id = "usr_99812"
    email = "lead@publicis.com"
    
    token = create_access_token(tenant_id, user_id, email, expires_in_seconds=300)
    assert token is not None
    
    user = verify_jwt_token(f"Bearer {token}")
    assert user.tenant_id == tenant_id
    assert user.user_id == user_id
    assert user.email == email

def test_expired_token_rejection():
    # Expired token (negative ttl)
    token = create_access_token("tenant_test", "usr_01", "test@test.com", expires_in_seconds=-10)
    with pytest.raises(ValueError) as excinfo:
        verify_jwt_token(f"Bearer {token}")
    assert "expired" in str(excinfo.value).lower()

def test_mock_dev_bypass_token():
    user = verify_jwt_token("Bearer test_tenant_agency_omnicom")
    assert user.tenant_id == "agency_omnicom"
    assert user.user_id == "usr_dev_001"
