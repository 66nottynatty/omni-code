# Clean Architecture

## Core Principles

1. **Separation of Concerns**: Each layer has specific responsibilities
2. **Dependency Inversion**: High-level modules don't depend on low-level modules
3. **Single Responsibility**: Each class/module has one reason to change
4. **Explicit Dependencies**: Dependencies are passed in, not created internally

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│         (Controllers, Views, DTOs, API Schemas)              │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                         │
│        (Use Cases, Application Services, Commands)            │
├─────────────────────────────────────────────────────────────┤
│                      Domain Layer                            │
│       (Entities, Value Objects, Domain Services)              │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                       │
│    (Repositories, External Services, Database Access)        │
└─────────────────────────────────────────────────────────────┘
```

## Python Project Structure

```
app/
├── main.py                      # FastAPI entry point
├── api/                         # Presentation - API routes
│   ├── __init__.py
│   ├── dependencies.py          # Dependency injection
│   └── v1/
│       ├── __init__.py
│       ├── router.py
│       └── endpoints/
│           ├── users.py
│           └── orders.py
├── application/                 # Application - Use cases
│   ├── __init__.py
│   ├── use_cases/
│   │   ├── create_user.py
│   │   └── process_order.py
│   ├── dto/                     # Data Transfer Objects
│   │   └── user_dto.py
│   └── interfaces/              # Ports (interfaces)
│       ├── user_repository.py
│       └── notification_service.py
├── domain/                      # Domain - Core business logic
│   ├── __init__.py
│   ├── entities/
│   │   ├── user.py
│   │   └── order.py
│   ├── value_objects/
│   │   ├── email.py
│   │   ├── money.py
│   │   └── address.py
│   ├── events/
│   │   └── user_events.py
│   └── exceptions.py
├── infrastructure/              # Infrastructure - External concerns
│   ├── __init__.py
│   ├── repositories/
│   │   └── sqlalchemy_user_repository.py
│   ├── services/
│   │   ├── email_notification.py
│   │   └── payment_gateway.py
│   └── database/
│       ├── session.py
│       └── models.py
└── shared/                      # Cross-cutting concerns
    ├── config.py
    ├── logging.py
    └── exceptions.py
```

## Domain Layer Implementation

### Entities
```python
# domain/entities/user.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import uuid

@dataclass
class User:
    id: Optional[int]
    email: str
    username: str
    password_hash: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    def __post_init__(self):
        if not self.email or '@' not in self.email:
            raise ValueError("Invalid email address")
        if len(self.username) < 3:
            raise ValueError("Username must be at least 3 characters")
    
    def update_email(self, new_email: str) -> None:
        if '@' not in new_email:
            raise ValueError("Invalid email address")
        self.email = new_email
        self.updated_at = datetime.utcnow()
    
    def change_password(self, old_password_hash: str, new_password: str) -> None:
        if self.password_hash != old_password_hash:
            raise ValueError("Invalid current password")
        self.password_hash = self._hash_password(new_password)
        self.updated_at = datetime.utcnow()
```

### Value Objects
```python
# domain/value_objects/money.py
from dataclasses import dataclass
from decimal import Decimal
from typing import Union

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        if len(self.currency) != 3:
            raise ValueError("Currency must be 3-letter ISO code")
    
    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError(f"Cannot add {self.currency} and {other.currency}")
        return Money(self.amount + other.amount, self.currency)
    
    def __mul__(self, quantity: Union[int, Decimal]) -> 'Money':
        return Money(self.amount * Decimal(str(quantity)), self.currency)
    
    @classmethod
    def zero(cls, currency: str = 'USD') -> 'Money':
        return cls(Decimal('0'), currency)
```

### Domain Events
```python
# domain/events/user_events.py
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod

@dataclass(frozen=True)
class DomainEvent:
    occurred_on: datetime = datetime.utcnow()

@dataclass(frozen=True)
class UserCreated(DomainEvent):
    user_id: int
    email: str

@dataclass(frozen=True)
class UserEmailChanged(DomainEvent):
    user_id: int
    old_email: str
    new_email: str

class EventDispatcher:
    def __init__(self):
        self._handlers: dict[type, list] = {}
    
    def register(self, event_type: type, handler: callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def dispatch(self, event: DomainEvent):
        for handler in self._handlers.get(type(event), []):
            handler(event)
```

## Application Layer

### Use Cases
```python
# application/use_cases/create_user.py
from dataclasses import dataclass
from application.interfaces.user_repository import UserRepository
from application.interfaces.notification_service import NotificationService
from domain.entities.user import User
from domain.events.user_events import UserCreated

@dataclass
class CreateUserInput:
    email: str
    username: str
    password: str

@dataclass
class CreateUserOutput:
    user_id: int
    email: str
    username: str

class CreateUserUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        notification_service: NotificationService
    ):
        self._user_repository = user_repository
        self._notification_service = notification_service
    
    def execute(self, input: CreateUserInput) -> CreateUserOutput:
        # Check for existing user
        existing = self._user_repository.find_by_email(input.email)
        if existing:
            raise ValueError(f"User with email {input.email} already exists")
        
        # Create user entity (domain logic)
        user = User(
            email=input.email,
            username=input.username,
            password_hash=hash_password(input.password)
        )
        
        # Persist
        saved_user = self._user_repository.save(user)
        
        # Send notification
        self._notification_service.send_welcome_email(saved_user.email)
        
        return CreateUserOutput(
            user_id=saved_user.id,
            email=saved_user.email,
            username=saved_user.username
        )
```

### Interfaces (Ports)
```python
# application/interfaces/user_repository.py
from abc import ABC, abstractmethod
from typing import Optional, List
from domain.entities.user import User

class UserRepository(ABC):
    @abstractmethod
    def find_by_id(self, user_id: int) -> Optional[User]:
        pass
    
    @abstractmethod
    def find_by_email(self, email: str) -> Optional[User]:
        pass
    
    @abstractmethod
    def find_all(self, limit: int = 100, offset: int = 0) -> List[User]:
        pass
    
    @abstractmethod
    def save(self, user: User) -> User:
        pass
    
    @abstractmethod
    def delete(self, user_id: int) -> None:
        pass
```

## Infrastructure Layer

### Repository Implementation
```python
# infrastructure/repositories/sqlalchemy_user_repository.py
from typing import Optional, List
from sqlalchemy.orm import Session
from domain.entities.user import User
from application.interfaces.user_repository import UserRepository

class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session):
        self._session = session
    
    def find_by_id(self, user_id: int) -> Optional[User]:
        db_user = self._session.query(DbUser).filter(
            DbUser.id == user_id
        ).first()
        return self._to_domain(db_user) if db_user else None
    
    def find_by_email(self, email: str) -> Optional[User]:
        db_user = self._session.query(DbUser).filter(
            DbUser.email == email
        ).first()
        return self._to_domain(db_user) if db_user else None
    
    def save(self, user: User) -> User:
        db_user = DbUser(
            email=user.email,
            username=user.username,
            password_hash=user.password_hash
        )
        self._session.add(db_user)
        self._session.commit()
        self._session.refresh(db_user)
        return self._to_domain(db_user)
    
    def _to_domain(self, db_user: 'DbUser') -> User:
        return User(
            id=db_user.id,
            email=db_user.email,
            username=db_user.username,
            password_hash=db_user.password_hash,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )
```

## Dependency Injection

```python
# api/dependencies.py
from functools import lru_cache
from sqlalchemy.orm import Session
from app.infrastructure.database.session import get_session
from app.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from app.infrastructure.services.email_notification import EmailNotificationService
from app.application.use_cases.create_user import CreateUserUseCase

@lru_cache
def get_user_repository() -> SQLAlchemyUserRepository:
    session = get_session()
    return SQLAlchemyUserRepository(session)

@lru_cache
def get_notification_service() -> EmailNotificationService:
    return EmailNotificationService()

@lru_cache
def get_create_user_use_case() -> CreateUserUseCase:
    return CreateUserUseCase(
        user_repository=get_user_repository(),
        notification_service=get_notification_service()
    )
```

## Testing Clean Architecture

```python
# tests/unit/test_create_user.py
import pytest
from unittest.mock import Mock
from application.use_cases.create_user import CreateUserUseCase, CreateUserInput
from domain.entities.user import User

class TestCreateUserUseCase:
    @pytest.fixture
    def mock_repository(self):
        return Mock()
    
    @pytest.fixture
    def mock_notification(self):
        return Mock()
    
    @pytest.fixture
    def use_case(self, mock_repository, mock_notification):
        return CreateUserUseCase(
            user_repository=mock_repository,
            notification_service=mock_notification
        )
    
    def test_creates_user_successfully(self, use_case, mock_repository, mock_notification):
        # Arrange
        mock_repository.find_by_email.return_value = None
        mock_repository.save.return_value = User(
            id=1,
            email="test@example.com",
            username="testuser",
            password_hash="hashed"
        )
        input = CreateUserInput(
            email="test@example.com",
            username="testuser",
            password="password123"
        )
        
        # Act
        output = use_case.execute(input)
        
        # Assert
        assert output.user_id == 1
        assert output.email == "test@example.com"
        mock_notification.send_welcome_email.assert_called_once()
    
    def test_raises_error_for_existing_email(self, use_case, mock_repository):
        # Arrange
        mock_repository.find_by_email.return_value = User(
            id=1,
            email="existing@example.com",
            username="existing",
            password_hash="hash"
        )
        input = CreateUserInput(
            email="existing@example.com",
            username="newuser",
            password="password123"
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="already exists"):
            use_case.execute(input)
```
