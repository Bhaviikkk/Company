"""
Authentication endpoints for production backend
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from app.core.auth import login_endpoint, get_current_user, get_admin_user
from app.core.rate_limiting import rate_limit
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

@router.post("/login", response_model=TokenResponse)
@rate_limit("10/minute")
async def login(request: Request, login_data: LoginRequest):
    """
    Login endpoint that returns JWT token for API access
    """
    try:
        result = await login_endpoint(login_data.username, login_data.password)
        return TokenResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.get("/verify")
async def verify_token(current_user: dict = Depends(get_current_user)):
    """
    Verify current JWT token and return user info
    """
    return {
        "status": "valid",
        "user": current_user.get("sub"),
        "role": current_user.get("role"),
        "expires": current_user.get("exp")
    }

@router.get("/admin/status")
async def admin_status(admin_user: dict = Depends(get_admin_user)):
    """
    Admin-only endpoint to check system status
    """
    return {
        "message": "Admin access granted",
        "admin_user": admin_user.get("sub"),
        "system_status": "operational"
    }