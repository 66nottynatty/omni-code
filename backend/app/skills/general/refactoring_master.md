# Refactoring Master

## When to Refactor

### Code Smells to Watch For
- **Duplicated Code**: Same logic repeated in multiple places
- **Long Methods**: Functions exceeding 40-50 lines
- **Large Classes**: Classes doing too many things
- **Long Parameter Lists**: Functions with 4+ parameters
- **Divergent Change**: One module changes for different reasons
- **Shotgun Surgery**: Changes require editing many modules
- **Feature Envy**: Class using another class's data more than its own
- **Data Clumps**: Groups of variables passed together
- **Primitive Obsession**: Using primitives instead of small objects
- **Switch Statements**: Repeated case/switch logic
- **Parallel Inheritance**: Duplicated class hierarchies
- **Lazy Class**: Classes doing too little
- **Speculative Generality**: Unused code for "future flexibility"
- **Temporary Field**: Fields only used sometimes
- **Message Chains**: Client asking one object for another repeatedly
- **Middle Man**: Classes just delegating to other classes
- **Inappropriate Intimacy**: Classes too tightly coupled
- **Alternative Classes**: Similar functionality with different interfaces
- **Incomplete Library Class**: Library class needs more methods
- **Data Class**: Classes with only fields and accessors
- **Refused Bequest**: Subclasses not using inherited functionality
- **Comments**: Over-commented code trying to hide bad code

## Refactoring Techniques

### Extract Method
```python
# Before: Long method with multiple responsibilities
def process_order(order: Order) -> dict:
    # Validate order
    if not order.items:
        raise ValueError("Order must have items")
    if not order.customer_id:
        raise ValueError("Customer ID required")
    if not order.shipping_address:
        raise ValueError("Shipping address required")
    
    # Calculate totals
    subtotal = sum(item.price * item.quantity for item in order.items)
    shipping = 10.0 if subtotal < 100 else 0.0
    tax = subtotal * 0.08
    total = subtotal + shipping + tax
    
    # Save order
    order.status = "confirmed"
    order.subtotal = subtotal
    order.shipping = shipping
    order.tax = tax
    order.total = total
    db.save(order)
    
    # Send confirmation
    email_service.send(
        to=customer.email,
        template="order_confirmation",
        context={"order": order}
    )
    
    return {"status": "success", "order_id": order.id}

# After: Well-separated responsibilities
def process_order(order: Order) -> dict:
    validate_order(order)
    pricing = calculate_order_pricing(order)
    order = save_order(order, pricing)
    notify_customer(order)
    return {"status": "success", "order_id": order.id}

def validate_order(order: Order) -> None:
    """Validate order has all required fields."""
    if not order.items:
        raise ValueError("Order must have items")
    if not order.customer_id:
        raise ValueError("Customer ID required")
    if not order.shipping_address:
        raise ValueError("Shipping address required")

def calculate_order_pricing(order: Order) -> Pricing:
    """Calculate pricing for an order."""
    subtotal = sum(item.price * item.quantity for item in order.items)
    shipping = 0.0 if subtotal >= 100 else 10.0
    tax = subtotal * TAX_RATE
    return Pricing(
        subtotal=subtotal,
        shipping=shipping,
        tax=tax,
        total=subtotal + shipping + tax
    )
```

### Replace Conditional with Polymorphism
```python
# Before: Complex conditional logic
class OrderProcessor:
    def calculate_shipping(self, order: Order) -> float:
        if order.customer.tier == "premium":
            if order.total > 100:
                return 0.0
            return 5.0
        elif order.customer.tier == "standard":
            if order.total > 200:
                return 0.0
            elif order.total > 100:
                return 5.0
            return 10.0
        else:  # basic
            if order.total > 500:
                return 0.0
            return 15.0

# After: Polymorphic approach
from abc import ABC, abstractmethod

class ShippingStrategy(ABC):
    @abstractmethod
    def calculate(self, order: Order) -> float:
        pass

class PremiumShipping(ShippingStrategy):
    def calculate(self, order: Order) -> float:
        return 0.0 if order.total > 100 else 5.0

class StandardShipping(ShippingStrategy):
    def calculate(self, order: Order) -> float:
        if order.total > 200:
            return 0.0
        return 5.0 if order.total > 100 else 10.0

class BasicShipping(ShippingStrategy):
    def calculate(self, order: Order) -> float:
        return 0.0 if order.total > 500 else 15.0

class OrderProcessor:
    def __init__(self):
        self.shipping_strategies = {
            "premium": PremiumShipping(),
            "standard": StandardShipping(),
            "basic": BasicShipping(),
        }
    
    def calculate_shipping(self, order: Order) -> float:
        strategy = self.shipping_strategies[order.customer.tier]
        return strategy.calculate(order)
```

### Introduce Parameter Object
```python
# Before: Long parameter list
def create_report(
    title: str,
    start_date: date,
    end_date: date,
    include_charts: bool,
    include_tables: bool,
    include_summary: bool,
    format: str,
    author: str
) -> Report:
    pass

# After: Grouped parameters
from dataclasses import dataclass

@dataclass
class DateRange:
    start_date: date
    end_date: date

@dataclass
class ReportConfig:
    title: str
    date_range: DateRange
    include_charts: bool = True
    include_tables: bool = True
    include_summary: bool = True
    format: str = "pdf"
    author: str = ""

def create_report(config: ReportConfig) -> Report:
    pass

# Usage
report = create_report(ReportConfig(
    title="Monthly Sales",
    date_range=DateRange(start_date, end_date),
    author="Sales Team"
))
```

### Rename and Extract Variables
```python
# Before: Cryptic names
def calc(p, t, r):
    return p * (1 + r * t)

# After: Self-documenting
def calculate_simple_interest(
    principal_amount: Decimal,
    annual_rate: Decimal,
    time_years: Decimal
) -> Decimal:
    """Calculate simple interest: I = P × (1 + R × T)"""
    return principal_amount * (1 + annual_rate * time_years)
```

## Large-Scale Refactoring

### Branch by Abstraction
```
Main (stable) ──────┬─── Abstraction Layer ───┐
                    │                          │
Feature A ──────────┘                          │
                    │                          │
Feature B ────────────────────────────────────┘
```

1. Introduce abstraction layer
2. Redirect consumers to abstraction
3. Implement new code behind abstraction
4. Remove old implementation

### Strangler Fig Pattern
```python
# 1. Create facade that routes to old or new
class PaymentGateway:
    def __init__(self):
        self._legacy = LegacyPaymentGateway()
        self._new = NewPaymentGateway()
        self._use_new = False  # Feature flag
    
    def process_payment(self, amount: Decimal) -> PaymentResult:
        if self._use_new:
            return self._new.process_payment(amount)
        return self._legacy.process_payment(amount)

# 2. Incrementally migrate endpoints
class NewPaymentGateway:
    async def process_card(self, card: Card) -> PaymentResult:
        """New endpoint implementation."""
        # Implement new logic here
        pass
    
    async def process_bank_transfer(self, bank: Bank) -> PaymentResult:
        """Still using legacy - will migrate next."""
        return await self._legacy.process_bank_transfer(bank)
```

## Testing During Refactoring

### The Two Worlds Pattern
```python
# Keep both implementations running during transition
class DataService:
    def __init__(self):
        self._legacy = LegacyDataService()
        self._new = RefactoredDataService()
        self._validate_results = True  # Compare outputs
    
    def get_user(self, user_id: int) -> User:
        if settings.USE_NEW_IMPLEMENTATION:
            result = self._new.get_user(user_id)
        else:
            result = self._legacy.get_user(user_id)
        
        # Validation during transition
        if self._validate_results:
            new_result = self._new.get_user(user_id)
            if result != new_result:
                raise RefactoringError(
                    f"Results differ: {result} vs {new_result}"
                )
        
        return result
```

## Git Workflow for Refactoring

```bash
# 1. Create feature branch
git checkout -b refactor/order-pricing

# 2. Make small, commit-able changes
git add src/services/pricing.py
git commit -m "refactor: Extract calculate_order_pricing()"

# 3. Run tests after each change
pytest tests/ -v

# 4. Squash related commits before merge
git rebase -i HEAD~5

# 5. Merge with squash
git checkout main
git merge --squash refactor/order-pricing
git commit -m "refactor: Complete order pricing refactor"
```

## Metrics to Track

| Metric | Target | Measuring Tool |
|--------|--------|---------------|
| Cyclomatic Complexity | < 10 per function | SonarQube |
| Lines of Code | < 100 per function | cloc |
| Coupling | Low inter-module dependencies | Dependency analysis |
| Coverage | > 80% after refactor | pytest-cov |
| Duplication | < 3% | SonarQube |
| Method Length | < 40 lines | ESLint, pylint |
