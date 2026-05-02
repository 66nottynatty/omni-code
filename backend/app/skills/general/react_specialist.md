# React Specialist

## Component Architecture

### Functional Components with Hooks
```tsx
import { useState, useEffect, useCallback, useMemo } from 'react';

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (row: T) => void;
}

export function DataTable<T extends { id: string | number }>({
  data,
  columns,
  onRowClick,
}: DataTableProps<T>) {
  const [sortConfig, setSortConfig] = useState<SortConfig<T> | null>(null);

  const sortedData = useMemo(() => {
    if (!sortConfig) return data;
    return [...data].sort((a, b) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];
      const modifier = sortConfig.direction === 'asc' ? 1 : -1;
      return aVal < bVal ? -modifier : modifier;
    });
  }, [data, sortConfig]);

  const handleSort = useCallback((key: keyof T) => {
    setSortConfig(prev => ({
      key,
      direction: prev?.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  }, []);

  return (
    <table className="w-full">
      <thead>
        <tr>
          {columns.map(col => (
            <th key={col.key as string} onClick={() => handleSort(col.key)}>
              {col.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sortedData.map(row => (
          <tr key={row.id} onClick={() => onRowClick?.(row)}>
            {columns.map(col => (
              <td key={col.key as string}>{String(row[col.key])}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

## State Management

### Local vs Global State
- **Local State**: Use `useState` for component-specific state
- **Shared State**: Use Context API or state management libraries
- **Server State**: Use React Query or SWR for data fetching

### Custom Hooks Pattern
```tsx
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}

function useFetch<T>(url: string) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    
    async function fetchData() {
      try {
        setLoading(true);
        const response = await fetch(url);
        const json = await response.json();
        if (!cancelled) setData(json);
      } catch (e) {
        if (!cancelled) setError(e as Error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => { cancelled = true; };
  }, [url]);

  return { data, loading, error };
}
```

## Performance Optimization

### React.memo and useMemo
```tsx
const ExpensiveList = React.memo(function ExpensiveList({ items }: { items: Item[] }) {
  return (
    <ul>
      {items.map(item => (
        <ListItem key={item.id} item={item} />
      ))}
    </ul>
  );
});

const memoizedValue = useMemo(() => computeExpensiveValue(a, b), [a, b]);
```

### Code Splitting
```tsx
import { lazy, Suspense } from 'react';
import LoadingSpinner from './LoadingSpinner';

const HeavyComponent = lazy(() => import('./HeavyComponent'));

function App() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <HeavyComponent />
    </Suspense>
  );
}
```

## Best Practices

1. **Colocation**: Keep components, hooks, and styles close to where they're used
2. **Composition**: Build complex UIs from smaller, reusable components
3. **Prop Types**: Always define clear prop interfaces
4. **Cleanup**: Always clean up effects with return functions
5. **Keys**: Use stable, unique keys for list items
6. **Accessibility**: Use semantic HTML and ARIA attributes

## Testing React Components
```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

test('form submission', async () => {
  const onSubmit = jest.fn();
  render(<ContactForm onSubmit={onSubmit} />);
  
  await userEvent.type(screen.getByLabelText('Email'), 'test@example.com');
  await userEvent.click(screen.getByRole('button', { name: 'Submit' }));
  
  expect(onSubmit).toHaveBeenCalledWith({ email: 'test@example.com' });
});
```
