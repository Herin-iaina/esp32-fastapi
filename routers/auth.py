from fastapi import APIRouter, Depends, HTTPException
from typing import Literal, Annotated
from pydantic import BaseModel
from core.config import settings
from core.security import create_access_token, current_subject

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="username and password required")
    token = create_access_token(subject=body.username)
    return LoginResponse(access_token=token, expires_in=settings.access_token_expires_minutes * 60)

@router.get("/me")
async def me(subject: Annotated[str, Depends(current_subject)]):
    return {"subject": subject}
