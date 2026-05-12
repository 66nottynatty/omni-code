'use client';

import React, { useEffect, useRef, useState } from 'react';
import { ScrollArea } from './ui/scroll-area';

import { client } from '@/lib/api';

interface LogEntry {
  id: number;
  content: string;
  type: 'info' | 'command' | 'result' | 'error';
}

export default function AgentLogsPanel({ threadId, taskId }: { threadId?: number; taskId?: number }) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let stopStream: (() => void) | undefined;
    
    if (taskId) {
      stopStream = client.tasks.streamLogs(taskId, (newLog) => {
        setLogs((prev) => [...prev, newLog]);
      });
    } else if (threadId) {
      stopStream = client.threads.streamLogs(threadId, (newLog) => {
        setLogs((prev) => [...prev, newLog]);
      });
    }

    return () => stopStream?.();
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
