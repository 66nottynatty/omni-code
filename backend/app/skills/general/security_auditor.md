# Security Auditor

## Security Principles

1. **Defense in Depth**: Multiple layers of security
2. **Least Privilege**: Minimum necessary permissions
3. **Secure by Default**: Safe choices out of the box
4. **Fail Safely**: Handle errors securely

## Input Validation & Sanitization

### SQL Injection Prevention
```python
# ❌ Never do this - SQL Injection vulnerable
query = f"SELECT * FROM users WHERE id = {user_id}"
db.execute(query)

# ✅ Use parameterized queries
from sqlalchemy import text
query = text("SELECT * FROM users WHERE id = :user_id")
db.execute(query, {"user_id": user_id})

# ✅ Use ORM (SQLAlchemy handles escaping)
user = db.query(User).filter(User.id == user_id).first()
```

### XSS Prevention
```typescript
// ❌ Never render raw HTML without sanitization
<div dangerouslySetInnerHTML={{ __html: userContent }} />

// ✅ Use context-aware escaping
<div>{userContent}</div>  // React escapes by default

// ✅ Sanitize HTML with DOMPurify
import DOMPurify from 'dompurify';
const clean = DOMPurify.sanitize(userContent, {
  ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a'],
  ALLOWED_ATTR: ['href'],
});
```

### Command Injection Prevention
```python
# ❌ Never pass user input to shell commands
os.system(f"ls {user_path}")  # Vulnerable!

# ✅ Use subprocess with list arguments
import subprocess
subprocess.run(["ls", user_path], check=True)  # Safe

# ✅ Use pathlib for file operations
from pathlib import Path
file_path = Path(user_path)
if file_path.resolve().is_relative_to(base_path):
    # Safe to use
```

## Authentication & Authorization

### Password Handling
```python
import bcrypt

def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())

# Argon2 is also excellent (used by many modern systems)
import argon2
ph = argon2.PasswordHasher()
hashed = ph.hash("password123")
try:
    ph.verify(hashed, "password123")
except argon2.exceptions.VerifyMismatchError:
    print("Invalid password")
```

### JWT Security
```python
from jose import jwt, JWTError
from datetime import datetime, timedelta

SECRET_KEY = os.environ["JWT_SECRET"]  # Minimum 256 bits
ALGORITHM = "HS256"

def create_token(user_id: int, expires_delta: timedelta = timedelta(hours=1)) -> str:
    """Create a secure JWT token."""
    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"  # Distinguish token types
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict | None:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
```

### Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

@app.post("/login")
@limiter.limit("5/minute")  # Brute force protection
async def login(request: Request):
    """Login endpoint with rate limiting."""
    # Implementation
```

## Data Protection

### Encryption at Rest
```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64

def derive_key(password: str, salt: bytes) -> bytes:
    """Derive encryption key from password."""
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_data(data: str, key: bytes) -> tuple[bytes, bytes]:
    """Encrypt sensitive data."""
    f = Fernet(key)
    return f.encrypt(data.encode())

def decrypt_data(encrypted: bytes, key: bytes) -> str:
    """Decrypt data."""
    f = Fernet(key)
    return f.decrypt(encrypted).decode()
```

### PII Handling
```python
import re

def mask_pii(data: str, pii_type: str) -> str:
    """Mask PII for logging and display."""
    patterns = {
        "email": r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        "phone": r"(\+\d{1,2})?[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}",
        "ssn": r"\d{3}-\d{2}-\d{4}",
        "credit_card": r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}",
    }
    
    if pii_type == "email":
        return re.sub(patterns["email"], r"***@\2", data)
    elif pii_type == "phone":
        return re.sub(patterns["phone"], "***-***-****", data)
    return "***"
```

## Secure Headers

```python
# Security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Prevent clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # Prevent MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # XSS Protection
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'"
    )
    
    # HSTS (HTTPS only)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response
```

## Common Vulnerability Checks

### Checklist for Code Review

- [ ] All user inputs validated and sanitized
- [ ] SQL queries use parameterized statements
- [ ] Authentication tokens are properly validated
- [ ] Session management is secure
- [ ] File uploads are validated (type, size, content)
- [ ] Error messages don't expose sensitive info
- [ ] Secrets not in code or version control
- [ ] Dependencies are up to date
- [ ] Rate limiting on sensitive endpoints
- [ ] HTTPS enforced in production
- [ ] Passwords hashed with strong algorithms
- [ ] No hardcoded credentials or API keys

## Security Testing

```python
# Security-focused pytest markers
import pytest

@pytest.mark.security
def test_sql_injection_prevention():
    """Verify SQL injection attempts are handled safely."""
    malicious_input = "'; DROP TABLE users; --"
    result = search_users(malicious_input)
    assert result == []
    assert "DROP" not in str(result)  # Injection failed

@pytest.mark.security  
def test_xss_prevention():
    """Verify XSS payloads are escaped."""
    xss_payload = '<script>alert("xss")</script>'
    result = render_user_content(xss_payload)
    assert '<script>' not in result
    assert '&lt;script&gt;' in result  # Properly escaped

@pytest.mark.security
def test_csrf_protection():
    """Verify CSRF tokens are required."""
    response = client.post("/api/data", json={"data": "test"})
    assert response.status_code == 403  # Missing CSRF token
```
