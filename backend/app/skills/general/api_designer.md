# API Designer

## RESTful API Design

### URL Structure
```
Resource-based URLs:
GET    /users              - List all users
GET    /users/{id}         - Get single user
POST   /users              - Create user
PUT    /users/{id}         - Update user (full)
PATCH  /users/{id}         - Partial update
DELETE /users/{id}         - Delete user

Nested resources (use sparingly, max 2 levels):
GET    /users/{id}/orders              - Get user's orders
GET    /users/{id}/orders/{order_id}  - Get specific order

Actions as sub-resources:
POST   /users/{id}/deactivate         - Action endpoint
POST   /orders/{id}/cancel            - Cancel action
```

### HTTP Status Codes

| Code | Meaning | When to Use |
|------|---------|-------------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST creating resource |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input, validation failed |
| 401 | Unauthorized | Missing or invalid auth |
| 403 | Forbidden | Authenticated but not authorized |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource, state conflict |
| 422 | Unprocessable | Semantic validation errors |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |

### Response Structure
```python
# Success response
{
    "data": {
        "id": 123,
        "name": "John Doe",
        "email": "john@example.com"
    },
    "meta": {
        "request_id": "req_abc123",
        "timestamp": "2024-01-15T10:30:00Z"
    }
}

# Paginated response
{
    "data": [...],
    "pagination": {
        "page": 1,
        "page_size": 20,
        "total_count": 150,
        "total_pages": 8,
        "has_next": true,
        "has_prev": false
    }
}

# Error response
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input data",
        "details": [
            {
                "field": "email",
                "message": "Must be a valid email address",
                "value": "invalid-email"
            },
            {
                "field": "password",
                "message": "Must be at least 8 characters",
                "value": "short"
            }
        ]
    },
    "meta": {
        "request_id": "req_abc123",
        "timestamp": "2024-01-15T10:30:00Z"
    }
}
```

## Pydantic Schemas for APIs

```python
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List, Generic, TypeVar
from datetime import datetime
from enum import Enum

T = TypeVar('T')

# Base schemas with shared attributes
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "username": "johndoe",
                "password": "securepass123"
            }
        }
    )

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(UserBase):
    id: int
    created_at: datetime
    is_active: bool = True
    
    model_config = ConfigDict(from_attributes=True)

# Pagination wrapper
class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    pagination: "PaginationMeta"

class PaginationMeta(BaseModel):
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=100)
    total_count: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)
    has_next: bool
    has_prev: bool
```

## Versioning Strategies

### URL Versioning (Most Common)
```
GET /v1/users
GET /v2/users
```

### Header Versioning
```
Accept: application/vnd.api+json, version=2
```

### Query Parameter Versioning (Simple but less clean)
```
GET /users?version=2
```

## API Documentation

### OpenAPI/Swagger
```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="E-Commerce API",
    version="2.0.0",
    description="Complete e-commerce platform API",
)

# Enhanced OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="E-Commerce API",
        version="2.0.0",
        description="Complete e-commerce platform API",
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # Add common headers
    openapi_schema["components"]["parameters"] = {
        "RequestID": {
            "name": "X-Request-ID",
            "in": "header",
            "description": "Unique request identifier",
            "schema": {"type": "string"}
        }
    }
    
    return openapi_schema

app.openapi = custom_openapi
```

## Best Practices

### Consistency Checklist
- [ ] Same response structure for all endpoints
- [ ] Consistent error format
- [ ] Consistent naming conventions (snake_case in/out)
- [ ] Consistent date formats (ISO 8601)
- [ ] Consistent pagination style
- [ ] Consistent sorting parameters

### Performance Considerations
```python
# Use ETags for caching
@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    
    # Generate ETag
    etag = generate_etag(user)
    
    # Check If-None-Match header
    if request.headers.get("If-None-Match") == etag:
        return Response(status_code=304)
    
    return Response(
        content=user.model_dump_json(),
        media_type="application/json",
        headers={"ETag": etag}
    )

# Async for I/O operations
@app.get("/users/{user_id}/posts")
async def get_user_posts(user_id: int):
    """Fetch user posts asynchronously."""
    async with aiohttp.ClientSession() as session:
        posts = await fetch_posts(session, user_id)
    return posts
```

### Batch Operations
```python
# POST /users/batch
class BatchCreateRequest(BaseModel):
    users: List[UserCreate] = Field(..., max_length=100)

class BatchCreateResponse(BaseModel):
    successful: List[UserResponse]
    failed: List[BatchError]

class BatchError(BaseModel):
    index: int
    error: str

@app.post("/users/batch", response_model=BatchCreateResponse)
async def batch_create_users(
    batch: BatchCreateRequest,
    db: Session = Depends(get_db)
):
    """Create multiple users in a single request."""
    results = {"successful": [], "failed": []}
    
    for idx, user_data in enumerate(batch.users):
        try:
            user = create_user(user_data, db)
            results["successful"].append(user)
        except Exception as e:
            results["failed"].append(BatchError(index=idx, error=str(e)))
    
    return results
```

## GraphQL Alternative

```python
# For complex data requirements
from strawberry.fastapi import GraphQLRouter
import strawberry

@strawberry.type
class UserType:
    id: int
    name: str
    email: str
    
    @strawberry.field
    def orders(self) -> List[OrderType]:
        return get_user_orders(self.id)

@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: int) -> UserType:
        return get_user(id)
    
    @strawberry.field
    def users(
        self,
        first: int = 10,
        after: Optional[str] = None
    ) -> List[UserType]:
        return paginate_users(first=first, after=after)

@strawberry.type
class Mutation:
    @strawberry.mutation
    def create_user(self, input: UserInput) -> UserType:
        return create_user(input)

# GraphQL is better for:
# - Complex nested data
# - Multiple resources in one request
# - Client-driven queries
# - Rapid iteration
```

## Webhooks Design

```python
# Webhook payload structure
{
    "event": "order.created",
    "timestamp": "2024-01-15T10:30:00Z",
    "data": {
        "id": "ord_123",
        "customer_id": "cust_456",
        "total": 99.99,
        "status": "pending"
    },
    "signature": "sha256=abc123..."
}

# Webhook signature verification
import hmac
import hashlib

def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str
) -> bool:
    """Verify webhook signature for security."""
    expected = "sha256=" + hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)

# Retry strategy headers
# X-Webhook-Retry-After: 300
# Implement exponential backoff: 1s, 5s, 30s, 2m, 10m, 1h
```
