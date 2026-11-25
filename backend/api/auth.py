"""
Authentication routes for CivicLens.
Provides citizen registration and login endpoints returning JWT tokens.
Authority accounts are seeded at startup via AUTHORITY_EMAIL / AUTHORITY_PASSWORD env vars.
"""

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.models.database import get_db
from backend.models.user import User, UserRole
from backend.models.schemas import TokenResponse, RegisterRequest, LoginRequest

router = APIRouter(prefix="/api/auth", tags=["Auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET", "civiclens_super_secret_jwt_key_2026_academic_project")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def seed_authority(db: Session):
    """Create authority user from env vars if not already present."""
    email = os.getenv("AUTHORITY_EMAIL")
    password = os.getenv("AUTHORITY_PASSWORD")
    if not email or not password:
        return
    existing = db.query(User).filter(User.email == email).first()
    if not existing:
        authority = User(
            email=email,
            hashed_password=get_password_hash(password),
            role=UserRole.AUTHORITY,
        )
        db.add(authority)
        db.commit()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new citizen account. Always creates citizen role."""
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    if len(request.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 6 characters",
        )
    user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        role=UserRole.CITIZEN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password, receive JWT."""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if request.role:
        expected = request.role.lower().strip()
        if expected == "authority" and user.role != UserRole.AUTHORITY:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is not an Authority account",
            )
        elif expected == "citizen" and user.role != UserRole.CITIZEN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please use Authority Login",
            )
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return TokenResponse(access_token=token)


@router.get("/me")
def me(db: Session = Depends(get_db)):
    """Placeholder – real implementation uses get_current_user dependency."""
    return {"detail": "Use Authorization: Bearer <token>"}
