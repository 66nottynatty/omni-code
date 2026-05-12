import api, {
  getTasks,
  getTask,
  createTask,
  resolveBlocker,
  getThreadHistory,
  rollbackAction,
  getModels,
  acceptChange,
  rejectChange,
  checkHealth,
} from '@/lib/api';

describe('API Utility', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn();
  });

  describe('getTasks', () => {
    it('fetches tasks without parameters', async () => {
      const mockTasks = [{ id: 1, status: 'pending' }];
      global.fetch.mockResolvedValueOnce({
        ok: true,
        data: mockTasks,
        json: () => Promise.resolve(mockTasks),
      });

      const result = await getTasks();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/tasks'),
        expect.any(Object)
      );
    });

    it('fetches tasks with workspace_id filter', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      });

      await getTasks(123);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('workspace_id=123'),
        expect.any(Object)
      );
    });

    it('fetches tasks with status filter', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      });

      await getTasks(undefined, 'running');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('status=running'),
        expect.any(Object)
      );
    });

    it('fetches tasks with both filters', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      });

      await getTasks(1, 'pending');

      const call = global.fetch.mock.calls[0][0];
      expect(call).toContain('workspace_id=1');
      expect(call).toContain('status=pending');
    });
  });

  describe('getTask', () => {
    it('fetches a single task by ID', async () => {
      const mockTask = { id: 42, status: 'running' };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockTask),
      });

      const result = await getTask(42);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/tasks/42'),
        expect.any(Object)
      );
      expect(result).toEqual(mockTask);
    });
  });

  describe('createTask', () => {
    it('creates a new task', async () => {
      const mockResponse = { task_id: 123, status: 'pending' };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const payload = { repo: 'test/repo' };
      const result = await createTask(1, 'agent_run', payload);

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/tasks',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            workspace_id: 1,
            task_type: 'agent_run',
            payload: payload,
          }),
        })
      );
    });
  });

  describe('resolveBlocker', () => {
    it('resolves a blocker with resolution text', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'success' }),
      });

      await resolveBlocker(42, 'User confirmed the change');

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/tasks/42/resolve',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ resolution: 'User confirmed the change' }),
        })
      );
    });
  });

  describe('getThreadHistory', () => {
    it('fetches thread history by thread ID', async () => {
      const mockHistory = [
        { id: 1, action_type: 'read' },
        { id: 2, action_type: 'write' },
      ];
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockHistory),
      });

      const result = await getThreadHistory(5);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/threads/5/history'),
        expect.any(Object)
      );
      expect(result).toEqual(mockHistory);
    });
  });

  describe('rollbackAction', () => {
    it('rolls back an action by ID', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'success' }),
      });

      await rollbackAction(10);

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/rollback/10',
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  describe('getModels', () => {
    it('fetches available AI models', async () => {
      const mockModels = [
        { id: 'gpt-4', name: 'GPT-4', provider: 'OpenAI' },
      ];
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockModels),
      });

      const result = await getModels();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/models'),
        expect.any(Object)
      );
      expect(result).toEqual(mockModels);
    });
  });

  describe('acceptChange', () => {
    it('accepts a pending change', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'success' }),
      });

      await acceptChange(5);

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/pending-changes/5/accept',
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  describe('rejectChange', () => {
    it('rejects a pending change', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'success' }),
      });

      await rejectChange(5);

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/pending-changes/5/reject',
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  describe('checkHealth', () => {
    it('checks health endpoint', async () => {
      const mockHealth = { status: 'ok', db: 'connected', redis: 'connected' };
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockHealth),
      });

      const result = await checkHealth();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/health'),
        expect.any(Object)
      );
      expect(result).toEqual(mockHealth);
    });
  });
});

describe('API Error Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('handles 401 unauthorized errors', async () => {
    const mockRedirect = jest.fn();
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
      configurable: true,
    });

    global.fetch = jest.fn().mockResolvedValueOnce({
      response: { status: 401 },
    });

    const apiModule = require('@/lib/api');
  });

  it('rejects failed requests', async () => {
    global.fetch = jest.fn().mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
    });

    const { getHealth } = require('@/lib/api');

    await expect(checkHealth()).rejects.toThrow();
  });
});

describe('API Request Interceptors', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.resetModules();
  });

  it('adds Authorization header when token is available', async () => {
    // Mock document.cookie
    Object.defineProperty(document, 'cookie', {
      value: 'next-auth.session-token=test-token-123',
      writable: true,
    });

    global.fetch = jest.fn().mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([]),
    });

    const { getTasks } = require('@/lib/api');
    await getTasks();

    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token-123',
        }),
      })
    );
  });
});