from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import FileResponse, RedirectResponse

from models import SignupRequest, LoginRequest
from auth import create_user, authenticate_user, get_user_from_token

router = APIRouter()


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@router.get("/")
async def root():
    """Root redirect to login"""
    return RedirectResponse(url="/login")


@router.get("/login")
async def login_page():
    return FileResponse("static/login.html")


@router.get("/signup")
async def signup_page():
    return FileResponse("static/signup.html")


@router.get("/app")
async def app_page():
    return FileResponse("static/index.html")


# ---------------------------------------------------------------------------
# Auth API
# ---------------------------------------------------------------------------

@router.post("/api/auth/signup")
async def signup(request: SignupRequest):
    """User signup endpoint"""
    result = create_user(request.name, request.email, request.password)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])

    return {
        "message": result['message'],
        "token": result['token'],
        "user": result['user']
    }


@router.post("/api/auth/login")
async def login(request: LoginRequest):
    """User login endpoint"""
    result = authenticate_user(request.email, request.password)

    if not result['success']:
        raise HTTPException(status_code=401, detail=result['message'])

    return {
        "message": result['message'],
        "token": result['token'],
        "user": result['user']
    }


@router.get("/api/auth/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current authenticated user"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace('Bearer ', '')
    user = get_user_from_token(token)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {"user": user}


@router.post("/api/auth/logout")
async def logout():
    """Logout endpoint (client-side token removal)"""
    return {"message": "Logged out successfully"}
