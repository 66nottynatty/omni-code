'use client';

import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';

interface Props {
  taskId: number;
  isOpen: boolean;
  onClose: () => void;
  onResolve: (taskId: number, resolution: string) => Promise<void>;
}

export default function BlockerResolutionModal({ taskId, isOpen, onClose, onResolve }: Props) {
  const [resolution, setResolution] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onResolve(taskId, resolution);
      onClose();
    } catch (error) {
      console.error('Failed to resolve blocker:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-zinc-900">
        <h2 className="mb-4 text-lg font-bold">Resolve Blocker for Task #{taskId}</h2>
        <p className="mb-4 text-sm text-zinc-500">
          The agent is stuck. Please provide instructions or missing information to help it proceed.
        </p>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="mb-2 block text-sm font-medium">Resolution Instruction</label>
            <Input
              value={resolution}
              onChange={(e) => setResolution(e.target.value)}
              placeholder="e.g., Use the production API key, or look in the 'docs' folder"
              required
            />
          </div>
          <div className="flex justify-end space-x-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Resuming...' : 'Resume Task'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
