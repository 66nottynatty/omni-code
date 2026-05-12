"use client"

import React from "react"
import { 
  FolderIcon, 
  FileIcon, 
  ChevronRight, 
  ChevronDown, 
  MoreVertical,
  Plus,
  RefreshCw,
  Search,
  Filter
} from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"

export function ExplorerPanel({ tree, onFileSelect, onRefresh }: { tree: any[], onFileSelect: (path: string) => void, onRefresh?: () => void }) {
  return (
    <div className="flex flex-col h-full bg-[#09090b]">
      <div className="h-9 px-4 flex items-center justify-between shrink-0">
        <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Explorer</span>
        <div className="flex items-center gap-1">
          <Plus className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground cursor-pointer" />
          <RefreshCw 
            className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground cursor-pointer" 
            onClick={onRefresh}
          />
        </div>
      </div>
      <div className="px-4 py-2 shrink-0">
        <div className="relative">
          <Search className="absolute left-2 top-2 w-3.5 h-3.5 text-muted-foreground" />
          <Input 
            placeholder="Search files..." 
            className="h-8 pl-7 bg-[#18181b] border-border text-xs focus-visible:ring-primary/50"
          />
        </div>
      </div>
      <ScrollArea className="flex-1">
        <div className="py-2">
          {tree.map((item) => (
            <div 
              key={item.path} 
              className="flex items-center gap-1 px-4 py-1 hover:bg-accent/50 cursor-pointer text-sm"
              onClick={() => item.type === 'blob' && onFileSelect(item.path)}
            >
              {item.type === 'tree' ? (
                <FolderIcon className="w-4 h-4 text-blue-400 fill-blue-400/20" />
              ) : (
                <FileIcon className="w-4 h-4 text-muted-foreground" />
              )}
              <span className={item.type === 'tree' ? "font-medium" : ""}>{item.name}</span>
            </div>
          ))}
          {tree.length === 0 && (
            <div className="px-4 py-2 text-xs text-muted-foreground">Loading tree...</div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}

export function GitPanel() {
  return (
    <div className="flex flex-col h-full bg-[#09090b]">
      <div className="h-9 px-4 flex items-center justify-between shrink-0">
        <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Source Control</span>
        <div className="flex items-center gap-1">
          <Filter className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground cursor-pointer" />
          <MoreVertical className="w-3.5 h-3.5 text-muted-foreground hover:text-foreground cursor-pointer" />
        </div>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          <div className="space-y-2">
            <div className="text-[10px] font-bold text-muted-foreground uppercase">Changes</div>
            <div className="space-y-1">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center justify-between group p-1 hover:bg-accent/50 rounded cursor-pointer">
                  <div className="flex items-center gap-2 overflow-hidden">
                    <FileIcon className="w-4 h-4 shrink-0 text-muted-foreground" />
                    <span className="text-sm truncate">frontend/components/Editor.tsx</span>
                  </div>
                  <span className="text-[10px] font-bold text-yellow-500">M</span>
                </div>
              ))}
            </div>
          </div>
          <div className="space-y-2">
            <div className="text-[10px] font-bold text-muted-foreground uppercase">Commit History</div>
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex gap-2 relative">
                  <div className="w-2 h-2 rounded-full bg-primary mt-1.5 shrink-0" />
                  {i !== 3 && <div className="absolute left-[3px] top-4 w-px h-8 bg-border" />}
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-medium leading-none">feat: update UI layout</span>
                    <span className="text-[10px] text-muted-foreground">2 hours ago • agent-001</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </ScrollArea>
    </div>
  )
}

export function TasksPanel() {
  return (
    <div className="flex flex-col h-full bg-[#09090b]">
      <div className="h-9 px-4 flex items-center justify-between shrink-0">
        <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Agent Tasks</span>
        <Badge variant="outline" className="h-4 text-[9px] px-1 bg-green-500/10 text-green-500 border-green-500/20">Running</Badge>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="p-3 rounded-lg border border-border bg-[#18181b] space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {i === 1 ? (
                    <RefreshCw className="w-3 h-3 text-blue-400 animate-spin" />
                  ) : (
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  )}
                  <span className="text-xs font-semibold">{i === 1 ? "Analyzing codebase" : "File written"}</span>
                </div>
                <span className="text-[10px] text-muted-foreground">2m ago</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                {i === 1 
                  ? "Scanning project structure and identifying key components for the requested changes."
                  : "Successfully updated frontend/app/page.tsx with the new design tokens."}
              </p>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}

export function MemoryPanel() {
  return (
    <div className="flex flex-col h-full bg-[#09090b]">
      <div className="h-9 px-4 flex items-center justify-between shrink-0">
        <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Agent Memory</span>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          <div className="space-y-2">
            <div className="text-[10px] font-bold text-muted-foreground uppercase px-1">Learned Context</div>
            <div className="space-y-1">
              {[
                "Uses Tailwind CSS with a custom zinc palette.",
                "Primary language is TypeScript.",
                "State management uses React Context.",
                "API routes are located in /api/*."
              ].map((text, i) => (
                <div key={i} className="p-2 rounded border border-border bg-[#18181b] text-xs text-muted-foreground">
                  {text}
                </div>
              ))}
            </div>
          </div>
        </div>
      </ScrollArea>
    </div>
  )
}
