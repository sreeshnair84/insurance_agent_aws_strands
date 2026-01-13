"""
Seed database with test users and sample claims for different scenarios.
Performs a full clean (DROP ALL) before seeding.
"""
import asyncio
import sys
import os

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import bcrypt

# Import actual app models
from app.db.base import Base
from app.models.user import User, UserRole
from app.models.claim import Claim, ClaimStatus, ClaimType
from app.models.audit import Message, SenderType
from app.core.config import settings

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

async def seed_database():
    # Force SQLite URL for testing if not set
    # database_url = settings.SQLALCHEMY_DATABASE_URI or "sqlite+aiosqlite:///./sql_app.db"
    database_url = "sqlite+aiosqlite:///./sql_app.db"
    
    engine = create_async_engine(database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("[*] Resetting database...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("[*] Tables recreated.")

    async with async_session() as session:
        print("[*] Seeding database with test data...")
        
        # Create Users
        users = [
            # Regular Users (submit claims)
            User(username="john_user", password_hash=hash_password("password123"), role=UserRole.USER),
            User(username="sarah_user", password_hash=hash_password("password123"), role=UserRole.USER),
            User(username="mike_user", password_hash=hash_password("password123"), role=UserRole.USER),
            
            # Approvers (review claims)
            User(username="emma_approver", password_hash=hash_password("password123"), role=UserRole.APPROVER),
            User(username="david_approver", password_hash=hash_password("password123"), role=UserRole.APPROVER),
            
            # Admin
            User(username="admin", password_hash=hash_password("admin123"), role=UserRole.ADMIN),
            
            # Legacy simple credentials
            User(username="user", password_hash=hash_password("password"), role=UserRole.USER),
            User(username="approver", password_hash=hash_password("password"), role=UserRole.APPROVER),
            
            # Verification user
            User(username="testuser_verif", password_hash=hash_password("fake"), role=UserRole.USER),
        ]
        
        session.add_all(users)
        await session.commit()
        
        # Refresh to get IDs
        for user in users:
            await session.refresh(user)
        
        print(f"[OK] Created {len(users)} users")
        
        # Create Sample Claims with different scenarios
        now = datetime.utcnow()
        
        claims = [
            # Scenario 1: LOW RISK - Auto-approved (< $50k, low fraud score)
            Claim(
                policy_number="POL-2024-001",
                claim_type=ClaimType.HEALTH,
                claim_amount=15000.00,
                incident_date=now - timedelta(days=5),
                description="Routine medical procedure - appendectomy",
                documents_uploaded=True,
                fraud_risk_score=0.1,
                status=ClaimStatus.DRAFT,
                created_by_id=users[0].id  # john_user
            ),
            
            # Scenario 2: MEDIUM RISK - Requires approval ($50k-$500k)
            Claim(
                policy_number="POL-2024-002",
                claim_type=ClaimType.AUTO,
                claim_amount=85000.00,
                incident_date=now - timedelta(days=10),
                description="Vehicle collision - total loss of luxury sedan",
                documents_uploaded=True,
                fraud_risk_score=0.3,
                status=ClaimStatus.DRAFT,
                created_by_id=users[1].id  # sarah_user
            ),
            
            # Scenario 3: HIGH RISK - Requires approval (> $500k or high fraud score)
            Claim(
                policy_number="POL-2024-003",
                claim_type=ClaimType.PROPERTY,
                claim_amount=750000.00,
                incident_date=now - timedelta(days=3),
                description="Fire damage to commercial property",
                documents_uploaded=True,
                fraud_risk_score=0.6,
                status=ClaimStatus.DRAFT,
                created_by_id=users[2].id  # mike_user
            ),
            
            # Scenario 4: HIGH FRAUD RISK - Requires approval (high fraud score)
            Claim(
                policy_number="POL-2024-004",
                claim_type=ClaimType.HEALTH,
                claim_amount=45000.00,
                incident_date=now - timedelta(days=1),
                description="Emergency surgery claim with inconsistent documentation",
                documents_uploaded=False,
                fraud_risk_score=0.85,
                status=ClaimStatus.DRAFT,
                created_by_id=users[0].id  # john_user
            ),
            
            # Scenario 5: PENDING APPROVAL - Already submitted
            Claim(
                policy_number="POL-2024-005",
                claim_type=ClaimType.AUTO,
                claim_amount=125000.00,
                incident_date=now - timedelta(days=15),
                description="Multi-vehicle accident with injuries",
                documents_uploaded=True,
                fraud_risk_score=0.4,
                status=ClaimStatus.PENDING_APPROVAL,
                created_by_id=users[1].id,  # sarah_user
                assigned_approver_id=users[3].id,  # emma_approver
                claim_metadata={
                    "interrupt_id": "test-interrupt-123",
                    "interrupt_reason": {
                        "claim_id": 5,
                        "risk_level": "MEDIUM",
                        "summary": "Claim involves multiple parties and significant medical expenses. Requires verification of police report and medical documentation.",
                        "claim_amount": 125000.00
                    }
                }
            ),
            
            # Scenario 6: APPROVED - Completed claim
            Claim(
                policy_number="POL-2024-006",
                claim_type=ClaimType.HEALTH,
                claim_amount=8500.00,
                incident_date=now - timedelta(days=30),
                description="Dental procedure - crown replacement",
                documents_uploaded=True,
                fraud_risk_score=0.05,
                status=ClaimStatus.APPROVED,
                created_by_id=users[2].id,  # mike_user
                assigned_approver_id=users[4].id  # david_approver
            ),
            
            # Scenario 7: REJECTED - Denied claim
            Claim(
                policy_number="POL-2024-007",
                claim_type=ClaimType.AUTO,
                claim_amount=95000.00,
                incident_date=now - timedelta(days=45),
                description="Accident claim with pre-existing damage",
                documents_uploaded=True,
                fraud_risk_score=0.9,
                status=ClaimStatus.REJECTED,
                created_by_id=users[0].id,  # john_user
                assigned_approver_id=users[3].id  # emma_approver
            ),
            
            # Scenario 8: NEEDS MORE INFO - Waiting for user response
            Claim(
                policy_number="POL-2024-008",
                claim_type=ClaimType.PROPERTY,
                claim_amount=250000.00,
                incident_date=now - timedelta(days=7),
                description="Water damage to residential property",
                documents_uploaded=False,
                fraud_risk_score=0.35,
                status=ClaimStatus.NEEDS_MORE_INFO,
                created_by_id=users[1].id,  # sarah_user
                assigned_approver_id=users[4].id  # david_approver
            ),
        ]
        
        session.add_all(claims)
        await session.commit()
        
        # Refresh claims to get IDs
        for claim in claims:
            await session.refresh(claim)
        
        print(f"[OK] Created {len(claims)} sample claims")
        
        # Create sample chat messages for demonstration
        messages = [
            Message(
                claim_id=claims[0].id,
                sender_type=SenderType.USER,
                sender_id=users[0].id,
                content="What is the status of my claim?",
                created_at=now - timedelta(hours=2)
            ),
            Message(
                claim_id=claims[0].id,
                sender_type=SenderType.AGENT,
                sender_id=None,
                content="Your claim (Policy: POL-2024-001) is in DRAFT status. This is a low-risk claim for $15,000. Once you submit it, it will be automatically processed.",
                message_metadata={
                    "a2ui": [
                        {
                            "type": "status_card",
                            "status": "DRAFT",
                            "title": "Claim Status: Draft",
                            "description": "Not yet submitted",
                            "color": "gray",
                            "icon": "📝"
                        },
                        {
                            "type": "info_card",
                            "title": "Claim Details",
                            "fields": [
                                {"label": "Policy Number", "value": "POL-2024-001"},
                                {"label": "Type", "value": "HEALTH"},
                                {"label": "Amount", "value": "$15,000.00"},
                                {"label": "Status", "value": "Draft"}
                            ]
                        }
                    ]
                },
                created_at=now - timedelta(hours=2, minutes=-1)
            ),
            
            # Sample messages for claim 5 (pending approval)
            Message(
                claim_id=claims[4].id,
                sender_type=SenderType.USER,
                sender_id=users[1].id,
                content="How long will the approval take?",
                created_at=now - timedelta(hours=1)
            ),
            Message(
                claim_id=claims[4].id,
                sender_type=SenderType.AGENT,
                sender_id=None,
                content="Your claim is currently pending approval. For MEDIUM risk claims like yours ($125,000), the typical review time is 2-5 business days. An approver will review your claim and make a decision soon.",
                message_metadata={
                    "a2ui": [
                        {
                            "type": "status_card",
                            "status": "PENDING_APPROVAL",
                            "title": "Claim Status: Pending Approval",
                            "description": "Awaiting human review",
                            "color": "yellow",
                            "icon": "⏳"
                        }
                    ]
                },
                created_at=now - timedelta(hours=1, minutes=-1)
            ),

            # NEW: General Chat Messages (No Claim ID)
            Message(
                 claim_id=None,
                 sender_type=SenderType.USER,
                 sender_id=users[0].id,
                 content="List my claims please.",
                 created_at=now - timedelta(minutes=30)
            ),
             Message(
                 claim_id=None,
                 sender_type=SenderType.AGENT,
                 sender_id=None,
                 content="Here are your recent claims:\n- POL-2024-001 (DRAFT)\n- POL-2024-004 (DRAFT)\n- POL-2024-007 (REJECTED)",
                 created_at=now - timedelta(minutes=29)
            )
        ]
        
        session.add_all(messages)
        await session.commit()
        
        print(f"[OK] Created {len(messages)} sample chat messages (including general chat)")
        print("\n" + "="*60)
        print("TEST CREDENTIALS")
        print("="*60)
        print("\nUSERS (Submit Claims):")
        print("  - john_user / password123")
        print("  - sarah_user / password123")
        print("  - mike_user / password123")
        print("  - user / password (legacy)")
        
        print("\nAPPROVERS (Review Claims):")
        print("  - emma_approver / password123")
        print("  - david_approver / password123")
        print("  - approver / password (legacy)")
        
        print("\nADMIN:")
        print("  - admin / admin123")
        
        print("\n" + "="*60)
        print("SAMPLE CLAIMS")
        print("="*60)
        print("\n1. POL-2024-001 - LOW RISK ($15k) - Auto-approve scenario [HAS CHAT]")
        print("2. POL-2024-002 - MEDIUM RISK ($85k) - Interrupt scenario")
        print("3. POL-2024-003 - HIGH RISK ($750k) - Interrupt scenario")
        print("4. POL-2024-004 - HIGH FRAUD (0.85) - Interrupt scenario")
        print("5. POL-2024-005 - PENDING APPROVAL - Ready for review [HAS CHAT]")
        print("6. POL-2024-006 - APPROVED - Completed")
        print("7. POL-2024-007 - REJECTED - Denied")
        print("8. POL-2024-008 - NEEDS MORE INFO - Awaiting user")
        
        print("\n[SUCCESS] Database cleaned and seeded successfully!")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_database())
