# SQL Optimization Master

## Query Analysis Fundamentals

### Understanding EXPLAIN
Always start with `EXPLAIN` or `EXPLAIN ANALYZE` to understand query execution plans:

```sql
EXPLAIN ANALYZE
SELECT u.name, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at > '2024-01-01'
GROUP BY u.id, u.name
HAVING COUNT(o.id) > 5
ORDER BY order_count DESC
LIMIT 20;
```

### Index Types and When to Use Them

| Index Type | Use Case | Example |
|-----------|----------|---------|
| B-Tree | Equality, range, sorting | `CREATE INDEX idx_users_email ON users(email)` |
| Hash | Fast equality lookups | `CREATE INDEX idx_sessions_token ON sessions USING HASH(token)` |
| GIN | JSON, full-text search | `CREATE INDEX idx_products_attrs ON products USING GIN(attrs)` |
| GiST | Geometric, range types | `CREATE INDEX idx_ranges ON ranges USING GIST(tsrange)` |
| Partial | Filtered queries | `CREATE INDEX idx_active_users ON users(email) WHERE active = true` |
| Composite | Multi-column queries | `CREATE INDEX idx_orders_user_date ON orders(user_id, created_at)` |

## Writing Efficient Queries

### Good vs Bad Patterns

**❌ Bad: SELECT * and N+1 Queries**
```sql
-- Bad: Selecting all columns
SELECT * FROM orders;

-- Bad: N+1 query pattern
SELECT * FROM orders;
-- Then for each order:
SELECT * FROM order_items WHERE order_id = 1;
SELECT * FROM order_items WHERE order_id = 2;
-- ... repeated for each order
```

**✅ Good: Specific Columns and Joins**
```sql
-- Good: Specific columns only
SELECT o.id, o.total, u.email
FROM orders o
JOIN users u ON o.user_id = u.id;

-- Good: Single query with JOINs
SELECT o.id, o.total, u.email,
       json_agg(json_build_object('id', i.id, 'qty', i.quantity)) as items
FROM orders o
JOIN users u ON o.user_id = u.id
JOIN order_items i ON o.id = i.order_id
WHERE o.created_at > '2024-01-01'
GROUP BY o.id, o.total, u.email;
```

### Window Functions for Analytics
```sql
-- Running totals and rankings
SELECT 
    date,
    revenue,
    SUM(revenue) OVER (ORDER BY date) as running_total,
    AVG(revenue) OVER (
        ORDER BY date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as moving_avg_7d,
    RANK() OVER (ORDER BY revenue DESC) as revenue_rank
FROM daily_sales;
```

### Common Table Expressions (CTEs)
```sql
WITH monthly_sales AS (
    SELECT 
        DATE_TRUNC('month', created_at) as month,
        SUM(total) as revenue,
        COUNT(*) as order_count
    FROM orders
    WHERE created_at >= '2023-01-01'
    GROUP BY DATE_TRUNC('month', created_at)
),
ranked_months AS (
    SELECT 
        month,
        revenue,
        LAG(revenue) OVER (ORDER BY month) as prev_month_revenue,
        revenue - LAG(revenue) OVER (ORDER BY month) as growth
    FROM monthly_sales
)
SELECT 
    month,
    revenue,
    prev_month_revenue,
    ROUND(100.0 * (revenue - prev_month_revenue) / prev_month_revenue, 2) as growth_pct
FROM ranked_months
ORDER BY month DESC;
```

## Index Optimization

### Composite Index Ordering
```sql
-- For query: WHERE status = 'active' AND created_at > '2024-01-01' ORDER BY created_at
-- Most selective column first is NOT always optimal
-- Put equality conditions first, range condition last

CREATE INDEX idx_orders_status_created 
ON orders(status, created_at);  -- Good for the query above

-- For query: WHERE created_at > '2024-01-01' AND status = 'active' ORDER BY created_at
CREATE INDEX idx_orders_created_status 
ON orders(created_at, status);  -- Different order based on usage
```

### Partial Indexes
```sql
-- For frequently queried active users
CREATE INDEX idx_users_email_active 
ON users(email) 
WHERE active = true AND deleted_at IS NULL;

-- For recent unprocessed records
CREATE INDEX idx_orders_pending 
ON orders(created_at DESC) 
WHERE status = 'pending' AND processed_at IS NULL;
```

### Covering Indexes
```sql
-- Include all columns needed by the query to avoid table lookups
CREATE INDEX idx_users_email_covering 
ON users(email) 
INCLUDE (name, created_at, role);
-- Now this query is covered by the index alone:
SELECT name, created_at FROM users WHERE email = 'test@example.com';
```

## Schema Design

### Normalization vs Denormalization

**Normalized (3NF):**
```sql
-- Tables are well-structured with minimal redundancy
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    product_id INT REFERENCES products(id),
    quantity INT,
    unit_price DECIMAL(10,2),
    total DECIMAL(10,2)
);
```

**Denormalized for Read Performance:**
```sql
-- Add redundant fields for faster reads
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    user_email VARCHAR(255),  -- Denormalized
    user_name VARCHAR(100),   -- Denormalized
    product_id INT REFERENCES products(id),
    product_name VARCHAR(255), -- Denormalized
    quantity INT,
    unit_price DECIMAL(10,2),
    total DECIMAL(10,2)
);
-- Use triggers or application logic to keep denormalized fields in sync
```

### Partitioning Strategy
```sql
-- Partition by date for time-series data
CREATE TABLE orders (
    id SERIAL,
    created_at TIMESTAMP NOT NULL,
    total DECIMAL(10,2),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE orders_2024_q1 PARTITION OF orders
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE orders_2024_q2 PARTITION OF orders
    FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');
```

## Monitoring and Maintenance

### Key Metrics to Monitor
- Query execution time
- Index hit ratio
- Sequential scan count
- Lock wait time
- Connection pool usage
- Cache hit ratio

### Vacuum and Analyze
```sql
-- Regular maintenance
VACUUM ANALYZE orders;
VACUUM FULL orders;  -- Only when table is bloated

-- Monitor bloat
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(tablename::regclass)) as total_size,
    pg_size_pretty(pg_relation_size(tablename::regclass)) as table_size,
    n_dead_tup,
    n_live_tup
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY n_dead_tup DESC;
```

### Connection Management
```sql
-- Monitor active connections
SELECT 
    count(*) as total_connections,
    state,
    datname
FROM pg_stat_activity
GROUP BY state, datname;

-- Kill idle connections (use carefully)
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle' 
AND state_change < NOW() - INTERVAL '30 minutes';
```
