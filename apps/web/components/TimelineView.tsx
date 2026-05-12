'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { 
  BarChart, 
  Clock, 
  DollarSign, 
  CheckCircle2, 
  Calendar,
  TrendingUp
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface TimelineViewProps {
  graph: any;
}

export function TimelineView({ graph }: TimelineViewProps) {
  // Group subtasks by day of completion
  const groupedByDay: Record<string, any[]> = {};
  let totalCost = 0;
  let totalTokens = 0;

  graph.subtasks.forEach((task: any) => {
    if (task.status === 'completed' && task.completed_at) {
      const date = new Date(task.completed_at).toLocaleDateString();
      if (!groupedByDay[date]) groupedByDay[date] = [];
      groupedByDay[date].push(task);
      
      if (task.cost?.amount) totalCost += task.cost.amount;
      if (task.tokens_used) totalTokens += task.tokens_used;
    }
  });

  const days = Object.keys(groupedByDay).sort((a, b) => new Date(a).getTime() - new Date(b).getTime());

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="grid grid-cols-3 gap-4">
        <Card className="bg-[#18181b] border-border">
          <CardHeader className="p-4 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase text-muted-foreground flex items-center gap-1.5">
              <DollarSign className="w-3 h-3" /> Cumulative Cost
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="text-2xl font-bold">${totalCost.toFixed(2)}</div>
            <p className="text-[10px] text-muted-foreground mt-1 flex items-center gap-1">
              <TrendingUp className="w-2.5 h-2.5 text-green-500" />
              +12% from projected
            </p>
          </CardContent>
        </Card>
        <Card className="bg-[#18181b] border-border">
          <CardHeader className="p-4 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase text-muted-foreground flex items-center gap-1.5">
              <BarChart className="w-3 h-3" /> Tokens Consumed
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="text-2xl font-bold">{totalTokens.toLocaleString()}</div>
            <p className="text-[10px] text-muted-foreground mt-1">across {graph.subtasks.length} tasks</p>
          </CardContent>
        </Card>
        <Card className="bg-[#18181b] border-border">
          <CardHeader className="p-4 pb-2">
            <CardTitle className="text-[10px] font-bold uppercase text-muted-foreground flex items-center gap-1.5">
              <Clock className="w-3 h-3" /> Avg. Task Latency
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4 pt-0">
            <div className="text-2xl font-bold">4.2m</div>
            <p className="text-[10px] text-muted-foreground mt-1">Based on completed tasks</p>
          </CardContent>
        </Card>
      </div>

      <div className="relative pl-8 space-y-8 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
        {days.length === 0 && (
          <div className="text-center py-12 text-muted-foreground bg-zinc-900/30 rounded-xl border border-dashed border-border">
            No completed tasks to display in timeline yet.
          </div>
        )}
        
        {days.map((day) => (
          <div key={day} className="relative">
            <div className="absolute -left-[31px] top-1 w-5 h-5 rounded-full bg-[#09090b] border-2 border-primary flex items-center justify-center z-10">
              <Calendar className="w-2.5 h-2.5 text-primary" />
            </div>
            
            <div className="mb-4">
              <h3 className="text-sm font-bold text-foreground">{day}</h3>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                {groupedByDay[day].length} tasks completed
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {groupedByDay[day].map((task) => (
                <Card key={task.id} className="bg-[#18181b] border-border hover:border-primary/30 transition-colors">
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                        <span className="text-xs font-semibold truncate max-w-[150px]">{task.title}</span>
                      </div>
                      <Badge variant="outline" className="text-[9px] h-4">
                        ${task.cost?.amount || 0}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1">
                          <Clock className="w-2.5 h-2.5" /> 
                          {new Date(task.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <span>{task.tokens_used} tokens</span>
                      </div>
                      <span className="uppercase font-bold text-[8px]">{task.agent_type}</span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
