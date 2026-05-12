'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getGraph, streamGraphLogs } from '@/lib/api';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { 
  Activity, 
  CheckCircle2, 
  Circle, 
  Clock, 
  AlertCircle,
  Terminal,
  Layers,
  Cpu,
  LayoutDashboard,
  History
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { TimelineView } from '@/components/TimelineView';

export default function OrchestratorDashboard() {
  const { graphId } = useParams();
  const [graph, setGraph] = useState<any>(null);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'timeline'>('overview');

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const data = await getGraph(graphId as string);
        setGraph(data);
      } catch (error) {
        console.error('Failed to fetch graph:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchGraph();
    const interval = setInterval(fetchGraph, 3000);

    const unsubscribe = streamGraphLogs(graphId as string, (log) => {
      setLogs((prev) => [...prev, log].slice(-100)); // Keep last 100 logs
    });

    return () => {
      clearInterval(interval);
      unsubscribe();
    };
  }, [graphId]);

  if (loading) return <div className="p-8 text-center">Loading Orchestrator...</div>;
  if (!graph) return <div className="p-8 text-center">Graph not found</div>;

  const completedTasks = graph.subtasks.filter((t: any) => t.status === 'completed').length;
  const progress = (completedTasks / graph.subtasks.length) * 100;

  return (
    <div className="flex flex-col h-screen bg-[#09090b] text-foreground">
      {/* Header */}
      <header className="h-16 border-b border-border flex items-center justify-between px-6 shrink-0 bg-[#09090b]/50 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-4">
          <div className="bg-primary/10 p-2 rounded-lg">
            <Activity className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-bold flex items-center gap-2">
              Orchestrator <span className="text-muted-foreground font-normal">/</span> {graphId}
            </h1>
            <p className="text-xs text-muted-foreground truncate max-w-md">{graph.goal}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex bg-[#18181b] p-1 rounded-lg border border-border mr-2">
            <button 
              onClick={() => setActiveTab('overview')}
              className={cn(
                "px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all flex items-center gap-2",
                activeTab === 'overview' ? "bg-primary text-primary-foreground shadow-lg" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <LayoutDashboard className="w-3 h-3" /> Overview
            </button>
            <button 
              onClick={() => setActiveTab('timeline')}
              className={cn(
                "px-3 py-1 text-[10px] font-bold uppercase tracking-wider rounded-md transition-all flex items-center gap-2",
                activeTab === 'timeline' ? "bg-primary text-primary-foreground shadow-lg" : "text-muted-foreground hover:text-foreground"
              )}
            >
              <History className="w-3 h-3" /> Timeline
            </button>
          </div>
          <Badge variant={graph.status === 'running' ? 'default' : 'secondary'} className="capitalize">
            {graph.status}
          </Badge>
          <div className="text-xs text-muted-foreground flex items-center gap-1.5">
            <Clock className="w-3 h-3" />
            Started {new Date(graph.created_at).toLocaleTimeString()}
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-hidden p-6">
        {activeTab === 'timeline' ? (
          <div className="max-w-5xl mx-auto h-full overflow-hidden flex flex-col">
            <ScrollArea className="flex-1 pr-4">
              <TimelineView graph={graph} />
            </ScrollArea>
          </div>
        ) : (
          <div className="h-full gap-6 grid grid-cols-12 overflow-hidden">
            {/* Left Column: Subtasks and Progress */}
            <div className="col-span-8 flex flex-col gap-6 overflow-hidden">
              <Card className="bg-[#18181b] border-border shrink-0">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium flex items-center justify-between">
                    Overall Progress
                    <span className="text-primary">{Math.round(progress)}%</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <Progress value={progress} className="h-2" />
                  <div className="mt-4 grid grid-cols-4 gap-4 text-center">
                    <div>
                      <p className="text-2xl font-bold">{graph.subtasks.length}</p>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Total Tasks</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-green-500">{completedTasks}</p>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Completed</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-blue-500">
                        {graph.subtasks.filter((t: any) => t.status === 'running').length}
                      </p>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Active</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-yellow-500">
                        {graph.subtasks.filter((t: any) => t.status === 'pending').length}
                      </p>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Pending</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <div className="flex-1 flex flex-col gap-2 overflow-hidden">
                <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2 px-1">
                  <Layers className="w-3 h-3" /> Execution Plan
                </h3>
                <ScrollArea className="flex-1 pr-4">
                  <div className="space-y-3 pb-4">
                    {graph.subtasks.map((task: any) => (
                      <Card key={task.id} className={cn(
                        "bg-[#18181b] border-border transition-all",
                        task.status === 'running' && "ring-1 ring-primary/50 bg-primary/5"
                      )}>
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex items-start gap-3">
                              <div className="mt-1">
                                {task.status === 'completed' && <CheckCircle2 className="w-4 h-4 text-green-500" />}
                                {task.status === 'running' && <Activity className="w-4 h-4 text-primary animate-pulse" />}
                                {task.status === 'pending' && <Circle className="w-4 h-4 text-muted-foreground" />}
                                {task.status === 'failed' && <AlertCircle className="w-4 h-4 text-destructive" />}
                              </div>
                              <div>
                                <h4 className="text-sm font-semibold">{task.title}</h4>
                                <p className="text-xs text-muted-foreground mt-0.5">{task.description}</p>
                                <div className="flex items-center gap-2 mt-2">
                                  <Badge variant="outline" className="text-[9px] h-4 bg-zinc-900">
                                    <Cpu className="w-2.5 h-2.5 mr-1" /> {task.agent_type}
                                  </Badge>
                                  {task.dependencies.length > 0 && (
                                    <span className="text-[9px] text-muted-foreground">
                                      Depends on: {task.dependencies.join(', ')}
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>
                            <Badge className="capitalize text-[10px] h-5">
                              {task.status}
                            </Badge>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            </div>

            {/* Right Column: Live Logs */}
            <div className="col-span-4 flex flex-col gap-4 overflow-hidden">
              <div className="flex-1 flex flex-col bg-[#0c0c0e] rounded-xl border border-border overflow-hidden">
                <div className="h-10 px-4 flex items-center justify-between border-b border-border bg-[#18181b]/50">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-3.5 h-3.5 text-primary" />
                    <span className="text-xs font-bold uppercase">Live Logs</span>
                  </div>
                  <Badge variant="outline" className="h-4 text-[9px] border-green-500/20 text-green-500">Live</Badge>
                </div>
                <ScrollArea className="flex-1 font-mono text-[11px] p-4">
                  <div className="space-y-1.5">
                    {logs.length === 0 && (
                      <div className="text-muted-foreground italic">Waiting for logs...</div>
                    )}
                    {logs.map((log, i) => (
                      <div key={i} className="flex gap-3 leading-relaxed">
                        <span className="text-muted-foreground shrink-0 select-none">[{new Date().toLocaleTimeString()}]</span>
                        <span className={cn(
                          log.type === 'error' ? 'text-destructive' : 
                          log.type === 'warning' ? 'text-yellow-500' : 'text-zinc-300'
                        )}>
                          {typeof log === 'string' ? log : log.message || JSON.stringify(log)}
                        </span>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
              
              <Card className="bg-[#18181b] border-border shrink-0">
                <CardHeader className="p-4 pb-2">
                  <CardTitle className="text-xs font-bold uppercase text-muted-foreground">Active Agents</CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-2 rounded bg-zinc-900 border border-border">
                      <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                        <span className="text-xs font-medium">Orchestrator-Main</span>
                      </div>
                      <Badge variant="outline" className="text-[9px] h-4">GPT-4o</Badge>
                    </div>
                    {graph.subtasks.filter((t: any) => t.status === 'running').map((t: any) => (
                      <div key={t.id} className="flex items-center justify-between p-2 rounded bg-zinc-900 border border-border">
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                          <span className="text-xs font-medium uppercase">{t.agent_type}-Agent</span>
                        </div>
                        <Badge variant="outline" className="text-[9px] h-4">Claude 3.5</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
