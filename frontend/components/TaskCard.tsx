'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';

interface Task {
  id: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'blocked';
  task_type: string;
  created_at: string;
  updated_at: string;
}

export default function TaskCard({ task, onResolve }: { task: Task; onResolve?: (taskId: number) => void }) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-blue-500';
      case 'completed': return 'bg-green-500';
      case 'failed': return 'bg-red-500';
      case 'blocked': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  return (
    <Card className="mb-4">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">
          Task #{task.id} - {task.task_type}
        </CardTitle>
        <Badge className={getStatusColor(task.status)}>
          {task.status}
        </Badge>
      </CardHeader>
      <CardContent>
        <div className="text-xs text-muted-foreground">
          Created at {new Date(task.created_at).toLocaleString()}
        </div>
        {task.status === 'blocked' && (
          <div className="mt-4 p-2 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 rounded text-sm">
            Agent is blocked and requires human intervention.
          </div>
        )}
      </CardContent>
      <CardFooter className="flex justify-end space-x-2">
        <Button variant="outline" size="sm" onClick={() => window.location.href = `/dashboard/tasks/${task.id}`}>
          View Details
        </Button>
        {task.status === 'blocked' && (
          <Button size="sm" onClick={() => onResolve && onResolve(task.id)}>
            Resolve Blocker
          </Button>
        )}
      </CardFooter>
    </Card>
  );
}
