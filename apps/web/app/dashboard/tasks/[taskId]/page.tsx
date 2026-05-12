'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface LogEntry {
  content: string;
  level: 'info' | 'warning' | 'error';
  task_id: number;
}

export default function TaskDetailsPage() {
  const params = useParams();
  const taskId = params.taskId;
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [task, setTask] = useState<any>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Fetch task details
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/tasks/${taskId}`)
      .then(res => res.json())
      .then(data => setTask(data));

    // Stream logs
    const eventSource = new EventSource(`${process.env.NEXT_PUBLIC_API_URL}/api/tasks/${taskId}/logs/sse`);
    
    eventSource.onmessage = (event) => {
      const newLog = JSON.parse(event.data);
      setLogs((prev) => [...prev, newLog]);
    };

    return () => eventSource.close();
  }, [taskId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  if (!task) return <div className="p-8 text-center">Loading task details...</div>;

  return (
    <div className="container mx-auto py-8 h-[calc(100vh-4rem)] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold">Task #{taskId}</h1>
          <p className="text-zinc-500">{task.task_type}</p>
        </div>
        <Badge>{task.status}</Badge>
      </div>

      <div className="flex-1 min-h-0 border rounded-lg overflow-hidden flex flex-col bg-black">
        <div className="bg-zinc-900 px-4 py-2 text-xs font-mono text-zinc-400 border-b border-zinc-800">
          EXECUTION LOGS
        </div>
        <ScrollArea className="flex-1 p-4 font-mono text-sm">
          <div className="space-y-1">
            {logs.map((log, i) => (
              <div key={i} className={`${log.level === 'error' ? 'text-red-400' : 'text-zinc-300'}`}>
                <span className="text-zinc-600 mr-2">[{new Date().toLocaleTimeString()}]</span>
                {log.content}
              </div>
            ))}
            {logs.length === 0 && (
              <div className="text-zinc-600 italic">Waiting for logs...</div>
            )}
            <div ref={scrollRef} />
          </div>
        </ScrollArea>
      </div>
      
      <div className="mt-4 flex justify-between">
        <Button variant="outline" onClick={() => window.location.href = '/dashboard'}>
          Back to Dashboard
        </Button>
      </div>
    </div>
  );
}
