'use client';

import React from 'react';
import { MonacoDiffEditor } from './editor/MonacoEditor';
import { Button } from './ui/button';
import { toast } from 'sonner';

interface PendingChange {
  id: number;
  file_path: string;
  diff: string;
  original_content: string;
  new_content: string;
}

export default function DiffReviewPanel({ change }: { change: PendingChange }) {
  const handleAccept = async () => {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/pending-changes/${change.id}/accept`, {
      method: 'POST',
    });
    if (res.ok) {
      toast.success('Change accepted');
    } else {
      toast.error('Failed to accept change');
    }
  };

  const handleReject = async () => {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/pending-changes/${change.id}/reject`, {
      method: 'POST',
    });
    if (res.ok) {
      toast.success('Change rejected');
    } else {
      toast.error('Failed to reject change');
    }
  };

  return (
    <div className="flex flex-col h-full bg-background border-l">
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="text-sm font-semibold truncate">{change.file_path}</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleReject}>Reject</Button>
          <Button size="sm" onClick={handleAccept}>Accept</Button>
        </div>
      </div>
      <div className="flex-1">
        <MonacoDiffEditor
          original={change.original_content}
          modified={change.new_content}
          language="typescript"
        />
      </div>
    </div>
  );
}
