'use client';

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { 
  Sparkles, 
  ChevronRight, 
  Clock, 
  DollarSign, 
  Cpu, 
  Zap,
  ListTodo
} from 'lucide-react';
import { previewOrchestrator, runOrchestrator } from '@/lib/api';
import { useRouter } from 'next/navigation';

interface TaskCreationModalProps {
  isOpen: boolean;
  onClose: () => void;
  workspaceId: number;
}

export function TaskCreationModal({ isOpen, onClose, workspaceId }: TaskCreationModalProps) {
  const [prompt, setPrompt] = useState('');
  const [preview, setPreview] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const router = useRouter();

  const handlePreview = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    try {
      const data = await previewOrchestrator(prompt, workspaceId);
      setPreview(data);
    } catch (error) {
      console.error('Preview failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    if (!prompt.trim()) return;
    setStarting(true);
    try {
      const { graph_id } = await runOrchestrator(prompt, workspaceId);
      router.push(`/dashboard/orchestrator/${graph_id}`);
      onClose();
    } catch (error) {
      console.error('Start failed:', error);
    } finally {
      setStarting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[700px] bg-[#09090b] border-border text-foreground overflow-hidden flex flex-col max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            Create Orchestrated Task
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col gap-6 py-4">
          <div className="space-y-2">
            <label className="text-xs font-bold uppercase text-muted-foreground tracking-wider">
              Goal / Prompt
            </label>
            <Textarea
              placeholder="Describe what you want to build or fix..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="bg-[#18181b] border-border resize-none h-24 focus:ring-primary/50"
            />
            <div className="flex justify-end">
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handlePreview} 
                disabled={loading || !prompt.trim() || starting}
                className="gap-2"
              >
                {loading ? 'Analyzing...' : 'Decompose & Preview'}
                <Zap className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>

          {preview && (
            <div className="flex-1 overflow-hidden flex flex-col gap-4 animate-in fade-in slide-in-from-top-4 duration-300">
              <Separator />
              
              <div className="flex items-center justify-between px-1">
                <h3 className="text-sm font-bold flex items-center gap-2">
                  <ListTodo className="w-4 h-4 text-primary" />
                  Decomposition Preview
                </h3>
                <div className="flex gap-4">
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" /> ~15-20m
                  </div>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <DollarSign className="w-3 h-3" /> ~$0.45
                  </div>
                </div>
              </div>

              <ScrollArea className="flex-1 border rounded-lg bg-[#0c0c0e] p-4">
                <div className="space-y-4">
                  {preview.subtasks.map((task: any, i: number) => (
                    <div key={task.id} className="flex gap-4 group">
                      <div className="flex flex-col items-center gap-1">
                        <div className="w-6 h-6 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-[10px] font-bold text-primary">
                          {i + 1}
                        </div>
                        {i !== preview.subtasks.length - 1 && (
                          <div className="w-px h-full bg-border group-hover:bg-primary/30 transition-colors" />
                        )}
                      </div>
                      <div className="flex-1 pb-4">
                        <div className="flex items-center justify-between gap-2">
                          <h4 className="text-sm font-semibold">{task.title}</h4>
                          <Badge variant="outline" className="text-[10px] h-5 bg-[#18181b]">
                            <Cpu className="w-2.5 h-2.5 mr-1" /> {task.agent_type}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">{task.description}</p>
                        
                        <div className="mt-2 flex items-center gap-3">
                          <div className="text-[10px] flex items-center gap-1 text-muted-foreground bg-zinc-900 px-1.5 py-0.5 rounded">
                            <span className="font-bold text-primary">Model:</span> 
                            {task.model_id || (task.agent_type === 'frontend' ? 'GPT-4o' : 'Claude 3.5')}
                          </div>
                          {task.dependencies.length > 0 && (
                            <div className="text-[10px] text-muted-foreground">
                              Wait for: {task.dependencies.join(', ')}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2 sm:gap-0 border-t border-border pt-4">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button 
            onClick={handleStart} 
            disabled={starting || !prompt.trim()} 
            className="gap-2 min-w-[120px]"
          >
            {starting ? 'Starting...' : 'Begin Execution'}
            <ChevronRight className="w-4 h-4" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
