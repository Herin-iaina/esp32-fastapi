from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import bcrypt
from typing import Optional
import logging
from core.logging import logger

from apps.database_configuration import db_manager, LoginModel


class UserResponse(BaseModel):
    id: int
    email: str  # mail_id depuis LoginModel
    username: str  # user_name depuis LoginModel
    status: bool
    
    class Config:
        from_attributes = True  # Pydantic v2

class UserLogin(BaseModel):
    user_name: str  # Correspond au champ de LoginModel
    password: str

def verify_password_bcrypt(password: str, hashed: str) -> bool:
    """Vérifie qu'un mot de passe correspond au hash bcrypt"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        logger.error(f"Erreur vérification mot de passe: {e}")
        return False

def validate_password_strength(password: str) -> bool:
    """Valide la force du mot de passe"""
    return len(password) >= 8 and any(c.isupper() for c in password) and any(c.isdigit() for c in password)

def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def authenticate_user(request: UserLogin) -> UserResponse | None:
    """Authentifie un utilisateur et retourne ses infos si succès"""
    try:
        with db_manager.get_session_context() as session:  # type: Session
            user = session.query(LoginModel).filter(
                LoginModel.user_name == request.user_name,
                LoginModel.status == True  # Vérifier que le compte est actif
            ).first()
            
            if user and verify_password_bcrypt(request.password, user.password):
                return UserResponse(
                    id=user.id,
                    email=user.mail_id or "",  # Gérer le cas nullable
                    username=user.user_name,
                    status=user.status
                )
            return None
            
    except Exception as e:
        logger.error(f"Erreur lors de l'authentification: {e}")
        return None

def create_user(username: str, password: str, email: Optional[str] = None) -> UserResponse | None:
    """Crée un nouvel utilisateur"""
    try:
        with db_manager.get_session_context() as session:  # type: Session
            # Vérifier si l'utilisateur existe déjà
            existing_user = session.query(LoginModel).filter(
                LoginModel.user_name == username
            ).first()
            if existing_user:
                logger.warning(f"Tentative de création d'un utilisateur existant: {username}")
                return None
            
            # Créer le nouvel utilisateur
            hashed_password = hash_password(password)
            new_user = LoginModel(
                user_name=username,
                password=hashed_password,
                mail_id=email,
                status=True
            )
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            return UserResponse(
                id=new_user.id,
                email=new_user.mail_id or "",
                username=new_user.user_name,
                status=new_user.status
            )
            
    except Exception as e:
        logger.error(f"Erreur lors de la création utilisateur: {e}")
        return None