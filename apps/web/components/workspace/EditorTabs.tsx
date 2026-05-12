"use client"

import React from "react"
import { X, FileCode, FileJson, FileText, ChevronRight, ChevronLeft } from "lucide-react"
import { cn } from "@/lib/utils"

interface Tab {
  id: string
  name: string
  icon: any
  active: boolean
  modified?: boolean
}

const initialTabs: Tab[] = [
  { id: "1", name: "App.tsx", icon: FileCode, active: true, modified: true },
  { id: "2", name: "globals.css", icon: FileText, active: false },
  { id: "3", name: "package.json", icon: FileJson, active: false },
]

export function EditorTabs({ activeFile }: { activeFile: string | null }) {
  const fileName = activeFile ? activeFile.split('/').pop() : "Welcome"
  return (
    <div className="h-9 bg-[#09090b] border-b border-border flex items-center overflow-hidden shrink-0">
      <div className="flex items-center h-full overflow-x-auto no-scrollbar">
        <div
          className="group h-full flex items-center px-3 border-r border-border gap-2 cursor-pointer transition-colors min-w-[120px] max-w-[200px] bg-[#18181b] border-t-2 border-t-primary"
        >
          <FileCode className="w-4 h-4 text-primary" />
          <span className="text-xs truncate text-foreground">{fileName}</span>
          <div className="ml-auto flex items-center gap-1">
            <X className="w-3 h-3 opacity-0 group-hover:opacity-100 hover:bg-muted-foreground/20 rounded-sm transition-all" />
          </div>
        </div>
      </div>
      <div className="ml-auto flex items-center h-full px-2 gap-1 border-l border-border bg-[#09090b]">
        <button className="p-1 hover:bg-accent rounded transition-colors">
          <ChevronLeft className="w-4 h-4 text-muted-foreground" />
        </button>
        <button className="p-1 hover:bg-accent rounded transition-colors">
          <ChevronRight className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>
    </div>
  )
}
