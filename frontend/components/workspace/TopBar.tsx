"use client"

import React from "react"
import { 
  Play, 
  Settings, 
  Share2, 
  MoreHorizontal, 
  Github, 
  Terminal,
  Cpu
} from "lucide-react"
import { Button } from "@/components/ui/button"

export function TopBar({ owner, repo }: { owner: string, repo: string }) {
  return (
    <div className="h-12 border-b border-border bg-[#09090b] flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded bg-primary/20 flex items-center justify-center border border-primary/30">
          <Cpu className="w-5 h-5 text-primary" />
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground font-medium">{owner}</span>
          <span className="text-muted-foreground">/</span>
          <span className="text-foreground font-semibold">{repo}</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" className="h-8 gap-2 text-xs">
          <Play className="w-3.5 h-3.5 fill-green-500 text-green-500" />
          Run
        </Button>
        <div className="w-px h-4 bg-border mx-1" />
        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
          <Share2 className="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
          <Github className="w-4 h-4" />
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
          <Settings className="w-4 h-4" />
        </Button>
        <Button variant="outline" size="sm" className="h-8 gap-2 text-xs border-border bg-[#18181b]">
          Deploy
        </Button>
      </div>
    </div>
  )
}
