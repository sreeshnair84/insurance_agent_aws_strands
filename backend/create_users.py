"""Quick script to create test users for login."""
import asyncio
import sys
sys.path.insert(0, 'backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.future import select
import bcrypt

# Simple inline models
from sqlalchemy import Column, Integer, String, Enum
import enum

Base = declarative_base()

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

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

async def create_users():
    engine = create_async_engine("sqlite+aiosqlite:///./sql_app.db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check if users exist
        result = await session.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none():
            print("✓ Users already exist")
            return
        
        # Create users
        users = [
            User(username="user", password_hash=hash_password("password"), role=UserRole.USER),
            User(username="approver", password_hash=hash_password("password"), role=UserRole.APPROVER),
            User(username="admin", password_hash=hash_password("password"), role=UserRole.ADMIN),
        ]
        
        session.add_all(users)
        await session.commit()
        print("[OK] Created users: user, approver, admin (all with password: 'password')")

if __name__ == "__main__":
    asyncio.run(create_users())
