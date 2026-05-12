'use client';

import React, { useEffect, useState } from 'react';
import TaskCard from '@/components/TaskCard';
import BlockerResolutionModal from '@/components/BlockerResolutionModal';
import { TaskCreationModal } from '@/components/TaskCreationModal';
import { Button } from '@/components/ui/button';
import { Plus, Sparkles } from 'lucide-react';

export default function DashboardPage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const fetchTasks = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/tasks`);
      const data = await response.json();
      setTasks(data);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    }
  };

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  const handleResolveClick = (taskId: number) => {
    setSelectedTaskId(taskId);
    setIsModalOpen(true);
  };

  const handleResolveSubmit = async (taskId: number, resolution: string) => {
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/tasks/${taskId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resolution }),
    });
    fetchTasks();
  };

  return (
    <div className="container mx-auto py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">Agent Task Dashboard</h1>
        <Button onClick={() => setIsCreateModalOpen(true)} className="gap-2">
          <Sparkles className="w-4 h-4" />
          New Orchestrated Task
        </Button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} onResolve={handleResolveClick} />
        ))}
      </div>

      {tasks.length === 0 && (
        <div className="text-center py-20 text-zinc-500">
          No background tasks found.
        </div>
      )}

      {selectedTaskId && (
        <BlockerResolutionModal
          taskId={selectedTaskId}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onResolve={handleResolveSubmit}
        />
      )}

      <TaskCreationModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        workspaceId={1} // Default workspace for now
      />
    </div>
  );
}
