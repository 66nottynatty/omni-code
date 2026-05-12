import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import SessionTimeline from '@/components/SessionTimeline';

// Mock the API module
jest.mock('@/lib/api', () => ({
  getThreadHistory: jest.fn(),
  rollbackAction: jest.fn(),
}));

import { getThreadHistory, rollbackAction } from '@/lib/api';

const mockHistory = [
  {
    id: 1,
    thread_id: 1,
    action_type: 'read',
    file_path: '/src/index.ts',
    command: null,
    created_at: '2024-01-15T10:30:00Z',
  },
  {
    id: 2,
    thread_id: 1,
    action_type: 'write',
    file_path: '/src/utils.ts',
    command: null,
    created_at: '2024-01-15T10:35:00Z',
  },
  {
    id: 3,
    thread_id: 1,
    action_type: 'shell',
    file_path: null,
    command: 'npm install',
    created_at: '2024-01-15T10:40:00Z',
  },
];

describe('SessionTimeline', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    getThreadHistory.mockResolvedValue(mockHistory);
  });

  it('renders without crashing', () => {
    render(<SessionTimeline threadId={1} />);
    expect(screen.getByText('Session History')).toBeInTheDocument();
  });

  it('displays loading state initially', () => {
    render(<SessionTimeline threadId={1} />);
    // Initial render will show empty state before data loads
    expect(screen.getByText('Session History')).toBeInTheDocument();
  });

  it('displays action history after loading', async () => {
    render(<SessionTimeline threadId={1} />);

    await waitFor(() => {
      expect(getThreadHistory).toHaveBeenCalledWith(1);
    });

    expect(screen.getByText('READ')).toBeInTheDocument();
    expect(screen.getByText('WRITE')).toBeInTheDocument();
    expect(screen.getByText('SHELL')).toBeInTheDocument();
  });

  it('displays file paths when available', async () => {
    render(<SessionTimeline threadId={1} />);

    await waitFor(() => {
      expect(screen.getByText('/src/index.ts')).toBeInTheDocument();
    });
  });

  it('displays commands when available', async () => {
    render(<SessionTimeline threadId={1} />);

    await waitFor(() => {
      expect(screen.getByText('npm install')).toBeInTheDocument();
    });
  });

  it('calls rollback handler when Undo is clicked', async () => {
    const user = userEvent.setup();
    render(<SessionTimeline threadId={1} />);

    await waitFor(() => {
      expect(screen.getAllByText('Undo')[0]).toBeInTheDocument();
    });

    await user.click(screen.getAllByText('Undo')[0]);

    expect(rollbackAction).toHaveBeenCalled();
  });

  it('handles empty history gracefully', async () => {
    getThreadHistory.mockResolvedValue([]);
    render(<SessionTimeline threadId={1} />);

    await waitFor(() => {
      expect(getThreadHistory).toHaveBeenCalled();
    });

    // Should still render the section header
    expect(screen.getByText('Session History')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    getThreadHistory.mockRejectedValue(new Error('API Error'));
    const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

    render(<SessionTimeline threadId={1} />);

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalled();
    });

    consoleErrorSpy.mockRestore();
  });

  it('refetches history on interval', async () => {
    jest.useFakeTimers();
    render(<SessionTimeline threadId={1} />);

    await waitFor(() => {
      expect(getThreadHistory).toHaveBeenCalledTimes(1);
    });

    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(getThreadHistory).toHaveBeenCalledTimes(2);
    });

    jest.useRealTimers();
  });

  it('cleans up interval on unmount', () => {
    const { unmount } = render(<SessionTimeline threadId={1} />);
    const clearIntervalSpy = jest.spyOn(global, 'clearInterval');

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });
});

describe('SessionTimeline action colors', () => {
  it('applies correct color for read action', async () => {
    render(<SessionTimeline threadId={1} />);

    await waitFor(() => {
      const readElement = screen.getByText('READ');
      expect(readElement).toHaveClass('text-blue-500');
    });
  });

  it('applies correct color for write action', async () => {
    render(<SessionTimeline threadId={1} />);

    await waitFor(() => {
      const writeElement = screen.getByText('WRITE');
      expect(writeElement).toHaveClass('text-green-500');
    });
  });

  it('applies correct color for shell action', async () => {
    render(<SessionTimeline threadId={1} />);

    await waitFor(() => {
      const shellElement = screen.getByText('SHELL');
      expect(shellElement).toHaveClass('text-yellow-500');
    });
  });
});