import React from 'react';
import { render, screen } from '@testing-library/react';
import TaskCard from '@/components/TaskCard';

// Mock window.location
const mockLocation = { href: '' };
Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true,
});

describe('TaskCard', () => {
  const mockTask = {
    id: 42,
    status: 'running',
    task_type: 'agent_run',
    created_at: '2024-01-15T10:30:00Z',
    updated_at: '2024-01-15T10:35:00Z',
  };

  it('renders task information correctly', () => {
    render(<TaskCard task={mockTask} />);

    expect(screen.getByText('Task #42 - agent_run')).toBeInTheDocument();
  });

  it('displays status badge', () => {
    render(<TaskCard task={mockTask} />);

    const badge = screen.getByText('running');
    expect(badge).toBeInTheDocument();
  });

  it('displays creation timestamp', () => {
    render(<TaskCard task={mockTask} />);

    expect(screen.getByText(/Created at/)).toBeInTheDocument();
  });

  it('shows View Details button', () => {
    render(<TaskCard task={mockTask} />);

    expect(screen.getByText('View Details')).toBeInTheDocument();
  });

  it('shows Resolve Blocker button for blocked tasks', () => {
    const blockedTask = { ...mockTask, status: 'blocked' };
    render(<TaskCard task={blockedTask} />);

    expect(screen.getByText('Resolve Blocker')).toBeInTheDocument();
  });

  it('does not show Resolve Blocker for non-blocked tasks', () => {
    render(<TaskCard task={mockTask} />);

    expect(screen.queryByText('Resolve Blocker')).not.toBeInTheDocument();
  });

  it('displays blocker message for blocked tasks', () => {
    const blockedTask = { ...mockTask, status: 'blocked' };
    render(<TaskCard task={blockedTask} />);

    expect(screen.getByText(/requires human intervention/)).toBeInTheDocument();
  });

  it('applies correct badge color for running status', () => {
    render(<TaskCard task={mockTask} />);

    const badge = screen.getByText('running');
    expect(badge.parentElement).toHaveClass('bg-blue-500');
  });

  it('applies correct badge color for completed status', () => {
    const completedTask = { ...mockTask, status: 'completed' };
    render(<TaskCard task={completedTask} />);

    const badge = screen.getByText('completed');
    expect(badge.parentElement).toHaveClass('bg-green-500');
  });

  it('applies correct badge color for failed status', () => {
    const failedTask = { ...mockTask, status: 'failed' };
    render(<TaskCard task={failedTask} />);

    const badge = screen.getByText('failed');
    expect(badge.parentElement).toHaveClass('bg-red-500');
  });

  it('applies correct badge color for blocked status', () => {
    const blockedTask = { ...mockTask, status: 'blocked' };
    render(<TaskCard task={blockedTask} />);

    const badge = screen.getByText('blocked');
    expect(badge.parentElement).toHaveClass('bg-yellow-500');
  });

  it('applies correct badge color for pending status', () => {
    const pendingTask = { ...mockTask, status: 'pending' };
    render(<TaskCard task={pendingTask} />);

    const badge = screen.getByText('pending');
    expect(badge.parentElement).toHaveClass('bg-gray-500');
  });

  it('calls onResolve when Resolve Blocker is clicked', async () => {
    const onResolve = jest.fn();
    const blockedTask = { ...mockTask, status: 'blocked' };
    const { getByText } = render(<TaskCard task={blockedTask} onResolve={onResolve} />);

    await getByText('Resolve Blocker').click();

    expect(onResolve).toHaveBeenCalledWith(42);
  });

  it('navigates to task details when View Details is clicked', () => {
    render(<TaskCard task={mockTask} />);

    const button = screen.getByText('View Details');
    button.click();

    expect(window.location.href).toContain('/dashboard/tasks/42');
  });
});

describe('TaskCard - Different task types', () => {
  it('displays repo_index task type', () => {
    const repoIndexTask = {
      id: 1,
      status: 'pending',
      task_type: 'repo_index',
      created_at: '2024-01-15T10:30:00Z',
    };
    render(<TaskCard task={repoIndexTask} />);

    expect(screen.getByText('repo_index')).toBeInTheDocument();
  });

  it('displays code_search task type', () => {
    const codeSearchTask = {
      id: 2,
      status: 'completed',
      task_type: 'code_search',
      created_at: '2024-01-15T10:30:00Z',
    };
    render(<TaskCard task={codeSearchTask} />);

    expect(screen.getByText('code_search')).toBeInTheDocument();
  });
});