import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import FileResponse, RedirectResponse

from models import SignupRequest, LoginRequest, ForgotPasswordRequest, ResetPasswordRequest
from auth import create_user, authenticate_user, get_user_from_token, generate_reset_token, reset_password
from utils.email_service import send_password_reset_email

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


@router.get("/reset-password")
async def reset_password_page():
    return FileResponse("static/reset-password.html")


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


@router.post("/api/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, req: Request):
    """Generate a password reset token and email the reset link"""
    result = generate_reset_token(request.email)

    if not result['success']:
        raise HTTPException(status_code=500, detail=result['message'])

    reset_token = result.get('reset_token')
    if reset_token:
        # Prefer explicit SERVER_URL; fall back to request origin
        server_url = os.getenv('SERVER_URL', '').rstrip('/')
        if not server_url:
            scheme = req.headers.get('x-forwarded-proto', req.url.scheme)
            host = req.headers.get('x-forwarded-host', req.headers.get('host', req.url.netloc))
            server_url = f"{scheme}://{host}"
        reset_url = f"{server_url}/reset-password?token={reset_token}"
        sent = send_password_reset_email(request.email, reset_url)
        if not sent:
            print(f"[Auth] Reset link for {request.email}: {reset_url}")

    return {"message": result['message']}


@router.post("/api/auth/reset-password")
async def reset_password_endpoint(request: ResetPasswordRequest):
    """Reset user password with a valid token"""
    result = reset_password(request.token, request.new_password)

    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])

    return {"message": result['message']}
