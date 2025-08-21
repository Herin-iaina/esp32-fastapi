from fastapi import APIRouter, Depends, HTTPException
from typing import Literal, Annotated
from pydantic import BaseModel
from core.config import settings
from typing import Optional
from core.logging import logger

from core.security import create_access_token, current_subject
from models.login import UserLogin, authenticate_user, create_user, validate_password_strength

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="username and password required")
    
    user_login = UserLogin(user_name=body.username, password=body.password)
    user = authenticate_user(user_login)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.status:
        raise HTTPException(status_code=403, detail="User account is inactive")
    # Create access token
    token = create_access_token(subject=user.username)
    return LoginResponse(access_token=token, expires_in=settings.access_token_expires_minutes * 60)

@router.get("/me")
async def me(subject: Annotated[str, Depends(current_subject)]):
    return {"subject": subject}

@router.post("/register", response_model=LoginResponse)
async def register(body: RegisterRequest):
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="username and password required")
    if not validate_password_strength(body.password):
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long, contain an uppercase letter and a digit") 
    
    user = create_user(body.username, body.password, body.email)
    if not user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    token = create_access_token(subject=user.username)
    return LoginResponse(access_token=token, expires_in=settings.access_token_expires_minutes * 60)
