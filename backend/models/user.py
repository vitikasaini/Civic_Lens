"""
User model for CivicLens authentication and role management.
"""

import enum
from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.orm import relationship
from backend.models.database import Base


class UserRole(str, enum.Enum):
    CITIZEN = "citizen"
    AUTHORITY = "authority"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CITIZEN)

    complaints = relationship("Complaint", back_populates="citizen")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
