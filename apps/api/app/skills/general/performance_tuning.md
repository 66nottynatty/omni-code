# Performance Tuning Master

## Performance Analysis Fundamentals

### The Performance Process
1. **Identify**: Find the bottleneck
2. **Measure**: Quantify the impact
3. **Optimize**: Implement solution
4. **Verify**: Confirm improvement
5. **Monitor**: Watch for regressions

### Profiling Tools by Language

| Language | Profiler | Use Case |
|----------|----------|----------|
| Python | `cProfile` | Function-level profiling |
| Python | `py-spy` | Production profiling |
| Python | `line_profiler` | Line-by-line analysis |
| Python | `memory_profiler` | Memory usage |
| JS/TS | Chrome DevTools | CPU & Memory |
| JS/TS | `clinic.js` | Node.js profiling |
| Go | `pprof` | Go profiling |
| PostgreSQL | `EXPLAIN ANALYZE` | Query analysis |

## Python Performance

### cProfile Example
```python
import cProfile
import pstats
from io import StringIO

def profile_function(func, *args, **kwargs):
    """Profile a function and print results."""
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = func(*args, **kwargs)
    
    profiler.disable()
    
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions
    
    print(stream.getvalue())
    return result

# Usage
profile_function(process_large_dataset, data)
```

### Memory Profiling
```python
# memory_profiler.py
from memory_profiler import profile

@profile
def load_and_process_data(filename):
    """Memory-intensive operation."""
    import pandas as pd
    
    # Read data
    df = pd.read_csv(filename)  # Memory spike here
    print(f"Memory after load: {df.memory_usage(deep=True).sum()}")
    
    # Process data
    result = df.groupby('category').agg({'value': 'sum'})
    
    return result

# Alternative: Manual memory tracking
import tracemalloc

def measure_memory(func, *args):
    tracemalloc.start()
    
    result = func(*args)
    
    current, peak = tracemalloc.get_traced_memory()
    print(f"Current memory: {current / 1024 / 1024:.2f} MB")
    print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
    
    tracemalloc.stop()
    return result
```

### Database Query Optimization
```python
# ❌ Bad: N+1 queries
def get_users_with_orders_buggy():
    users = db.query(User).all()
    for user in users:
        user.orders = db.query(Order).filter_by(user_id=user.id).all()
    return users

# ✅ Good: Eager loading
def get_users_with_orders_optimized():
    return db.query(User).options(
        joinedload(User.orders)
    ).all()

# ✅ Good: Selectin loading for large collections
def get_users_with_large_orders():
    return db.query(User).options(
        selectinload(User.orders)
    ).all()

# ✅ Good: Pagination
def get_users_paginated(page=1, page_size=50):
    return db.query(User).limit(page_size).offset((page-1) * page_size).all()
```

### Caching Strategies
```python
import functools
import hashlib
import json
from typing import Any

# 1. Function memoization
@functools.lru_cache(maxsize=128)
def expensive_computation(n: int) -> int:
    """Cache expensive function results."""
    # Simulate expensive work
    return sum(i * i for i in range(n))

# 2. Redis caching for expensive operations
import redis
import json

class CacheService:
    def __init__(self, redis_client: redis.Redis, ttl: int = 3600):
        self._redis = redis_client
        self._ttl = ttl
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True)
        hash_key = hashlib.md5(data.encode()).hexdigest()
        return f"{prefix}:{hash_key}"
    
    def get_or_set(self, prefix: str, func: callable, *args, **kwargs) -> Any:
        """Get from cache or execute and cache."""
        key = self._make_key(prefix, *args, **kwargs)
        
        cached = self._redis.get(key)
        if cached:
            return json.loads(cached)
        
        result = func(*args, **kwargs)
        self._redis.setex(key, self._ttl, json.dumps(result))
        return result
    
    def invalidate(self, pattern: str):
        """Invalidate keys matching pattern."""
        for key in self._redis.scan_iter(pattern):
            self._redis.delete(key)
```

### Async Optimization
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# ❌ Bad: Sequential async calls
async def fetch_data_sequential(urls):
    results = []
    for url in urls:
        result = await fetch(url)  # Waits for each
        results.append(result)
    return results

# ✅ Good: Concurrent async calls
async def fetch_data_concurrent(urls):
    results = await asyncio.gather(*[fetch(url) for url in urls])
    return results

# ✅ Good: Batch processing with semaphores
async def fetch_with_limit(urls, max_concurrent=10):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def bounded_fetch(url):
        async with semaphore:
            return await fetch(url)
    
    return await asyncio.gather(*[bounded_fetch(url) for url in urls])

# ✅ Good: CPU-bound work in thread pool
def process_cpu_intensive(data):
    # CPU-intensive calculations
    return [compute(x) for x in data]

async def process_with_threading(data):
    loop = asyncio.get_event_loop()
    executor = ThreadPoolExecutor(max_workers=4)
    
    return await loop.run_in_executor(
        executor,
        process_cpu_intensive,
        data
    )
```

## Database Performance

### Query Optimization
```sql
-- Use EXPLAIN ANALYZE to understand query plan
EXPLAIN ANALYZE
SELECT u.email, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at > '2024-01-01'
GROUP BY u.id, u.email
ORDER BY order_count DESC
LIMIT 10;

-- Create covering index for the query
CREATE INDEX idx_users_created_email 
ON users(created_at, email) INCLUDE (id);

-- Partial index for common filter
CREATE INDEX idx_active_users_email 
ON users(email) WHERE active = true;

-- Materialized view for expensive aggregations
CREATE MATERIALIZED VIEW monthly_sales AS
SELECT 
    DATE_TRUNC('month', created_at) as month,
    SUM(total) as revenue,
    COUNT(*) as order_count
FROM orders
GROUP BY DATE_TRUNC('month', created_at);

CREATE UNIQUE INDEX ON monthly_sales(month);

-- Refresh materialized view periodically
REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_sales;
```

### Connection Pooling
```python
# SQLAlchemy connection pool configuration
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,           # Number of connections to maintain
    max_overflow=10,        # Additional connections allowed
    pool_pre_ping=True,     # Verify connection before use
    pool_recycle=3600,      # Recycle connections after 1 hour
)
```

## Frontend Performance

### React Optimization
```tsx
// ❌ Bad: Creating new objects in render
function BadComponent({ items, filter }) {
  return <List data={items.filter(i => i.type === filter)} />;
}

// ✅ Good: Memoize filtered data
import { useMemo } from 'react';

function GoodComponent({ items, filter }) {
  const filteredItems = useMemo(
    () => items.filter(i => i.type === filter),
    [items, filter]
  );
  
  return <List data={filteredItems} />;
}

// ❌ Bad: New function references
function ParentComponent() {
  return <Child onClick={() => console.log('click')} />;
}

// ✅ Good: Stable function references
import { useCallback } from 'react';

function ParentComponent() {
  const handleClick = useCallback(() => {
    console.log('click');
  }, []);
  
  return <Child onClick={handleClick} />;
}
```

### Virtualization for Large Lists
```tsx
import { useVirtualizer } from '@tanstack/react-virtual';

function VirtualList({ items }) {
  const parentRef = useRef(null);
  
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50,
    overscan: 5,  // Render 5 extra items for smooth scrolling
  });
  
  return (
    <div ref={parentRef} style={{ height: '400px', overflow: 'auto' }}>
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map(({ index, start, size }) => (
          <div
            key={items[index].id}
            style={{
              position: 'absolute',
              top: start,
              height: size,
            }}
          >
            <ListItem item={items[index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

## Monitoring Performance

### Key Metrics
```python
from prometheus_client import Counter, Histogram, Gauge

# Request latency histogram
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint', 'status_code'],
    buckets=[.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5]
)

# Database query timing
DB_QUERY_DURATION = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    buckets=[.001, .005, .01, .025, .05, .1, .25, .5, 1]
)

# Memory usage
MEMORY_USAGE = Gauge(
    'process_memory_bytes',
    'Process memory usage in bytes'
)

# Cache hit ratio
CACHE_HITS = Counter('cache_operations_total', 'Cache operations', ['result'])
```

### Performance Budgets
| Metric | Target | Alert Threshold |
|--------|--------|------------------|
| Time to First Byte (TTFB) | < 200ms | > 500ms |
| First Contentful Paint | < 1.0s | > 2.0s |
| Time to Interactive | < 3.0s | > 5.0s |
| API P95 Latency | < 100ms | > 250ms |
| API P99 Latency | < 200ms | > 500ms |
| Database Query Time | < 50ms | > 100ms |
| Error Rate | < 0.1% | > 1% |

## Common Performance Anti-Patterns

| Anti-Pattern | Impact | Solution |
|-------------|--------|----------|
| N+1 Queries | High | Eager loading, batch queries |
| Sync operations in async code | High | Use proper async/await |
| Loading entire datasets | High | Pagination, streaming |
| No caching | Medium | Implement caching layer |
| Synchronous logging | Medium | Async logging queue |
| Deep object cloning | Medium | Immutable patterns |
| Regex in hot paths | Medium | Pre-compile or use simpler checks |
| Memory leaks | Cumulative | Proper cleanup, weak refs |
