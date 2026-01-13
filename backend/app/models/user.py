import enum
from sqlalchemy import Column, Integer, String, Enum
from app.db.base import Base

class UserRole(str, enum.Enum):
    USER = "USER"
    APPROVER = "APPROVER"
    ADMIN = "ADMIN"
    AGENT = "AGENT"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
