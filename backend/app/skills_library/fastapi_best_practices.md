# FastAPI Best Practices

## Project Structure
```
app/
├── main.py              # FastAPI app initialization
├── api/                 # API route handlers
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── endpoints/
│       └── router.py
├── core/                # Core functionality
│   ├── config.py
│   ├── security.py
│   └── database.py
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic schemas
├── services/            # Business logic
└── utils/               # Utilities
```

## Application Setup
```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    logger.info("Starting up application")
    # Startup: connect to databases, warm up caches
    yield
    # Shutdown: close connections, cleanup
    logger.info("Shutting down application")

app = FastAPI(
    title="My API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Pydantic Schemas
```python
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"

class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    role: UserRole = UserRole.USER

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    role: Optional[UserRole] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
```

## Database Operations
```python
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import Depends

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/users/", response_model=UserResponse, status_code=201)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """Create a new user."""
    # Check for existing user
    existing = db.execute(
        select(User).where(User.email == user.email)
    ).scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = hash_password(user.password)
    
    db_user = User(
        email=user.email,
        username=user.username,
        role=user.role,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.get("/users/", response_model=List[UserResponse])
def list_users(
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db)
):
    """List users with pagination."""
    total = db.execute(select(func.count(User.id))).scalar()
    users = db.execute(
        select(User)
        .offset(pagination.offset)
        .limit(pagination.page_size)
    ).scalars().all()
    
    return users
```

## Dependency Injection
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = decode_jwt(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    return payload

async def get_current_user(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user = db.get(User, token_data["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/protected-route")
async def protected_route(current_user: User = Depends(get_current_user)):
    return {"message": f"Hello, {current_user.username}"}
```

## Error Handling
```python
from fastapi import Request, status
from fastapi.responses import JSONResponse

@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": exc.code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

## Async Best Practices
```python
@app.get("/async-data")
async def get_async_data():
    """Use async for I/O-bound operations."""
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.example.com/data") as response:
            return await response.json()

@app.post("/bulk-process")
async def bulk_process(items: List[ItemCreate]):
    """Process items concurrently."""
    tasks = [process_item(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]
    
    return {"successes": successes, "failures": failures}
```

## Testing
```python
from fastapi.testclient import TestClient

def test_create_user():
    with TestClient(app) as client:
        response = client.post("/users/", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "securepassword123",
            "role": "user"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data

def test_list_users():
    with TestClient(app) as client:
        response = client.get("/users/?page=1&page_size=10")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
```
