import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Annotated
from pydantic import BaseModel
from core.config import settings

ALGORITHM = "HS256"
bearer_scheme = HTTPBearer(auto_error=True)

class TokenPayload(BaseModel):
    sub: str
    iat: int
    nbf: int
    exp: int

def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    if not subject or len(subject.strip()) == 0:
        raise ValueError("Subject cannot be empty")
    exp_minutes = expires_minutes or settings.access_token_expires_minutes
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_minutes)).timestamp()),
        "iss": settings.app_name,  
        "aud": "api-users"
    }
    return jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm=ALGORITHM)

def decode_token(token: str) -> TokenPayload:
    try:
        decoded = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=[ALGORITHM])
        return TokenPayload(**decoded)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def refresh_access_token(current_token: str) -> str:
    payload = decode_token(current_token)
    return create_access_token(payload.sub)

async def current_subject(creds: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)]) -> str:
    return decode_token(creds.credentials).sub
