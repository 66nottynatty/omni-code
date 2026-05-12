from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

settings = get_settings()

# Sync engine for migrations/initialization
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine for application use
async_database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
async_engine = create_async_engine(
    async_database_url,
    pool_size=20,
    max_overflow=100,
    pool_timeout=30,
    pool_recycle=1800,
)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session
