'use client';

import React, { useEffect, useRef, useState } from 'react';
import { ScrollArea } from './ui/scroll-area';

interface LogEntry {
  id: number;
  content: string;
  type: 'info' | 'command' | 'result' | 'error';
}

export default function AgentLogsPanel({ threadId, taskId }: { threadId?: number; taskId?: number }) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const url = taskId 
      ? `${process.env.NEXT_PUBLIC_API_URL}/api/tasks/${taskId}/logs/sse`
      : `${process.env.NEXT_PUBLIC_API_URL}/api/threads/${threadId}/logs/sse`;
    
    const eventSource = new EventSource(url);
    
    eventSource.onmessage = (event) => {
      const newLog = JSON.parse(event.data);
      setLogs((prev) => [...prev, newLog]);
    };

    return () => eventSource.close();
  }, [threadId, taskId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  return (
    <ScrollArea className="h-full bg-black text-white font-mono p-4">
      <div className="space-y-2">
        {logs.map((log, i) => (
          <div key={i} className={`text-xs ${log.type === 'error' ? 'text-red-400' : ''}`}>
            {log.type === 'command' ? (
              <div className="bg-zinc-900 p-2 rounded border border-zinc-800 my-2">
                <span className="text-zinc-500 mr-2">$</span>
                {log.content}
              </div>
            ) : (
              <div className={log.type === 'info' ? 'text-zinc-400' : ''}>
                {log.content}
              </div>
            )}
          </div>
        ))}
        <div ref={scrollRef} />
      </div>
    </ScrollArea>
  );
}
