import asyncio
from app.db.session import engine
from app.db.base import Base
# Import all models to register with Base
import app.models.user
import app.models.claim
import app.models.audit

async def init_models():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # internal dev only
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

if __name__ == "__main__":
    asyncio.run(init_models())
