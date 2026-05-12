'use client';

import React, { useEffect, useState } from 'react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { toast } from 'sonner';
import { getThreadHistory, rollbackAction } from '@/lib/api';

interface Action {
  id: number;
  action_type: string;
  file_path?: string;
  command?: string;
  created_at: string;
}

export default function SessionTimeline({ threadId }: { threadId: number }) {
  const [history, setHistory] = useState<Action[]>([]);

  const fetchHistory = async () => {
    try {
      const data = await getThreadHistory(threadId);
      setHistory(data);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchHistory();
    const interval = setInterval(fetchHistory, 5000);
    return () => clearInterval(interval);
  }, [threadId]);

  const handleRollback = async (actionId: number) => {
    try {
      await rollbackAction(actionId);
      toast.success('Rolled back successfully');
      fetchHistory();
    } catch {
      toast.error('Rollback failed');
    }
  };

  const getActionColor = (type: string) => {
    switch (type) {
      case 'write': return 'text-green-500';
      case 'read': return 'text-blue-500';
      case 'shell': return 'text-yellow-500';
      default: return 'text-muted-foreground';
    }
  };

  return (
    <ScrollArea className="h-full">
      <div className="p-4 space-y-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-muted-foreground">Session History</h3>
        {history.map((action) => (
          <div key={action.id} className="flex flex-col gap-1 border-l-2 pl-3 py-1 border-border hover:border-primary transition-colors">
            <div className="flex justify-between items-start">
              <span className={`text-xs font-mono font-bold ${getActionColor(action.action_type)}`}>
                {action.action_type.toUpperCase()}
              </span>
              <Button variant="ghost" size="sm" className="h-6 px-2 text-[10px]" onClick={() => handleRollback(action.id)}>
                Undo
              </Button>
            </div>
            <p className="text-xs truncate text-foreground">
              {action.file_path || action.command}
            </p>
            <span className="text-[10px] text-muted-foreground">
              {new Date(action.created_at).toLocaleTimeString()}
            </span>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}