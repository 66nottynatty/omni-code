# Test-Driven Development (TDD)

## The TDD Cycle

```
Red → Green → Refactor
 │       │        │
 │       │        └── Improve code while tests pass
 │       │
 │       └── Make the test pass
 │
 └── Write a failing test
```

## Core Principles

1. **Write the simplest test that could possibly fail**
2. **Get it to compile (if needed)**
3. **Make it fail in the expected way**
4. **Write the simplest code to make it pass**
5. **Refactor with confidence**

## Python Testing with pytest

### Test Structure
```python
# tests/test_order_service.py
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.order_service import OrderService
from app.models.order import Order, OrderStatus

class TestOrderService:
    """Test suite for OrderService."""

    @pytest.fixture
    def order_service(self):
        """Create a fresh OrderService for each test."""
        return OrderService(db_session=Mock())

    @pytest.fixture
    def sample_order(self):
        """Create a sample order for testing."""
        return Order(
            id=1,
            user_id=100,
            status=OrderStatus.PENDING,
            total=99.99,
            created_at=datetime.utcnow()
        )

    def test_create_order_success(self, order_service, sample_order):
        """Test successful order creation."""
        with patch.object(order_service, '_save_order') as mock_save:
            mock_save.return_value = sample_order
            
            result = order_service.create_order(
                user_id=100,
                items=[{"product_id": 1, "quantity": 2}]
            )
            
            assert result.status == OrderStatus.PENDING
            assert result.total == 99.99
            mock_save.assert_called_once()

    def test_create_order_empty_items_raises_error(self, order_service):
        """Test that empty items list raises validation error."""
        with pytest.raises(ValueError, match="At least one item required"):
            order_service.create_order(user_id=100, items=[])

    @pytest.mark.parametrize("quantity,expected_total", [
        (1, 49.99),
        (5, 249.95),
        (10, 499.90),
    ])
    def test_order_total_calculation(self, order_service, quantity, expected_total):
        """Test order total calculation with various quantities."""
        order = order_service.calculate_order_total([
            {"product_id": 1, "quantity": quantity, "unit_price": 49.99}
        ])
        assert order.total == expected_total
```

### Fixtures and Dependency Injection
```python
# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def db_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a fresh database session for each test."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def mock_email_service():
    """Mock email service for testing."""
    return Mock(spec=EmailService)
```

## JavaScript/TypeScript Testing with Vitest

### Component Testing
```typescript
// tests/components/Button.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from '../components/Button';

describe('Button', () => {
  it('renders with correct label', () => {
    render(<Button label="Click me" onClick={() => {}} />);
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const handleClick = vi.fn();
    render(<Button label="Click me" onClick={handleClick} />);
    
    await userEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledOnce();
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button label="Click me" onClick={() => {}} disabled />);
    expect(screen.getByRole('button')).toBeDisabled();
  });

  it.each([
    { variant: 'primary', expectedClass: 'bg-blue-500' },
    { variant: 'secondary', expectedClass: 'bg-gray-500' },
    { variant: 'danger', expectedClass: 'bg-red-500' },
  ])('applies correct variant class for $variant', ({ variant, expectedClass }) => {
    const { container } = render(
      <Button label="Test" onClick={() => {}} variant={variant} />
    );
    expect(container.firstChild).toHaveClass(expectedClass);
  });
});
```

### Service Testing
```typescript
// tests/services/userService.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { UserService } from '../services/userService';

describe('UserService', () => {
  let userService: UserService;
  let mockApiClient: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockApiClient = vi.fn();
    userService = new UserService(mockApiClient);
  });

  describe('createUser', () => {
    it('creates user with hashed password', async () => {
      mockApiClient.post = vi.fn().mockResolvedValue({
        id: '123',
        email: 'test@example.com',
        name: 'Test User'
      });

      const result = await userService.createUser({
        email: 'test@example.com',
        password: 'plaintext123',
        name: 'Test User'
      });

      expect(result.password).toBeUndefined(); // Password should not be returned
      expect(mockApiClient.post).toHaveBeenCalledWith('/users', expect.objectContaining({
        hashedPassword: expect.any(String)
      }));
    });

    it('throws error for duplicate email', async () => {
      mockApiClient.post = vi.fn().mockRejectedValue(
        new Error('Email already exists')
      );

      await expect(userService.createUser({
        email: 'existing@example.com',
        password: 'password123',
        name: 'Test'
      })).rejects.toThrow('Email already exists');
    });
  });
});
```

## Testing Patterns

### Arrange-Act-Assert (AAA)
```python
def test_transfer_funds_success(self):
    # Arrange
    source_account = Account(balance=1000.00)
    dest_account = Account(balance=500.00)
    
    # Act
    transfer_service.transfer(source_account, dest_account, 200.00)
    
    # Assert
    assert source_account.balance == 800.00
    assert dest_account.balance == 700.00
```

### Given-When-Then (GWT)
```typescript
describe('User Registration', () => {
  it('should send welcome email when user verifies email', () => {
    // Given
    const user = createUnverifiedUser();
    const emailService = createMockEmailService();
    
    // When
    userService.verifyEmail(user.email);
    
    // Then
    expect(emailService.send).toHaveBeenCalledWith(
      expect.objectContaining({
        to: user.email,
        template: 'welcome'
      })
    );
  });
});
```

### Test Doubles
```python
# Dummy: Objects that are passed but never used
dummy_config = None

# Fake: Working implementation with shortcuts
class FakeUserRepository:
    def __init__(self):
        self.users = {}
    def save(self, user):
        self.users[user.id] = user
    def find_by_id(self, id):
        return self.users.get(id)

# Stub: Pre-programmed responses
mock_repository = Mock()
mock_repository.find_by_id.return_value = User(name="Test")

# Spy: Records how they were called
spy_repository = Spy(UserRepository)
spy_repository.find_by_id(1)
assert spy_repository.find_by_id.was_called_with(1)

# Mock: Pre-programmed with expectations
mock_service = Mock()
mock_service.process.return_value = {"status": "success"}
mock_service.process.assert_called_once_with(expected_input)
```

## Coverage and Quality

### Target Coverage Levels
- **Unit Tests**: 80%+ coverage
- **Critical Paths**: 100% coverage
- **Integration Tests**: Cover all API endpoints
- **E2E Tests**: Cover happy paths and key error scenarios

### Running Tests
```bash
# Python
pytest tests/ -v --cov=app --cov-report=html
pytest tests/ -k "test_create"  # Run specific tests

# Node.js
vitest run --coverage
vitest run tests/unit/auth.test.ts
```

## Common TDD Anti-Patterns

| Anti-Pattern | Problem | Solution |
|-------------|---------|----------|
| Testing implementation | Brittle tests | Test behavior, not implementation |
| No test isolation | Flaky tests | Use fixtures, clean state |
| Too many assertions | Unclear failure | One assertion per test |
| Ignoring edge cases | Incomplete coverage | Test boundaries, nulls, empty |
| Skipping refactoring | Technical debt | Refactor after green |
