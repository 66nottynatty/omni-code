"use client"

import React, { useState, useEffect, useRef } from "react"
import { Search, Sparkles, GitBranch, Terminal, Settings, FileCode, Layers } from "lucide-react"
import { Command } from "cmdk"
import { cn } from "@/lib/utils"

interface CommandPaletteProps {
  onClose: () => void
  onDecompose: (goal: string) => Promise<any>
}

export function CommandPalette({ onClose, onDecompose }: CommandPaletteProps) {
  const [search, setSearch] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [decomposedResult, setDecomposedResult] = useState<any>(null)

  // Close on escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose()
      }
    }
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [onClose])

  const handleDecompose = async (goal: string) => {
    setIsLoading(true)
    try {
      const result = await onDecompose(goal)
      setDecomposedResult(result)
      setTimeout(onClose, 1500)
    } catch (e) {
      console.error("Decomposition failed:", e)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50">
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      <div className="absolute top-[20%] left-1/2 -translate-x-1/2 w-full max-w-xl">
        <Command className="bg-[#18181b] border border-border rounded-xl shadow-2xl overflow-hidden">
          <div className="flex items-center gap-2 px-4 border-b border-border">
            <Search className="w-4 h-4 text-muted-foreground" />
            <Command.Input
              placeholder="Type a command or search..."
              className="flex-1 bg-transparent border-none outline-none text-sm py-3 text-foreground placeholder:text-muted-foreground"
              value={search}
              onValueChange={setSearch}
              autoFocus
            />
            <kbd className="px-2 py-0.5 text-[10px] bg-muted rounded">ESC</kbd>
          </div>
          
          <Command.List className="p-2 max-h-[300px] overflow-y-auto">
            <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
              No results found.
            </Command.Empty>
            
            <Command.Group heading="Actions" className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-muted-foreground">
              <Command.Item 
                className="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer hover:bg-muted data-[selected=true]:bg-muted"
                onSelect={() => handleDecompose("Analyze codebase structure and identify improvements")}
              >
                <Sparkles className="w-4 h-4 text-primary" />
                <span>Smart Decompose</span>
              </Command.Item>
              
              <Command.Item 
                className="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer hover:bg-muted data-[selected=true]:bg-muted"
                onSelect={() => handleDecompose("Add comprehensive unit tests for the codebase")}
              >
                <Layers className="w-4 h-4 text-blue-500" />
                <span>Generate Tests</span>
              </Command.Item>
              
              <Command.Item 
                className="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer hover:bg-muted data-[selected=true]:bg-muted"
                onSelect={() => handleDecompose("Review code for security vulnerabilities")}
              >
                <FileCode className="w-4 h-4 text-red-500" />
                <span>Security Review</span>
              </Command.Item>
              
              <Command.Item 
                className="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer hover:bg-muted data-[selected=true]:bg-muted"
                onSelect={() => handleDecompose("Optimize database queries and add indexes")}
              >
                <GitBranch className="w-4 h-4 text-green-500" />
                <span>Database Optimization</span>
              </Command.Item>
            </Command.Group>
            
            <Command.Separator />
            
            <Command.Group heading="Quick Actions" className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:text-muted-foreground">
              <Command.Item className="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer hover:bg-muted data-[selected=true]:bg-muted">
                <Terminal className="w-4 h-4 text-muted-foreground" />
                <span>Open Terminal</span>
              </Command.Item>
              
              <Command.Item className="flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer hover:bg-muted data-[selected=true]:bg-muted">
                <Settings className="w-4 h-4 text-muted-foreground" />
                <span>Settings</span>
              </Command.Item>
            </Command.Group>
          </Command.List>
          
          {isLoading && (
            <div className="p-4 border-t border-border">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="animate-spin w-4 h-4 border-2 border-primary border-t-transparent rounded-full" />
                Decomposing task...
              </div>
            </div>
          )}
          
          {decomposedResult && (
            <div className="p-4 border-t border-border">
              <div className="text-sm">
                <p className="text-green-500 font-medium">✓ Decomposition complete!</p>
                <p className="text-muted-foreground mt-1">
                  {decomposedResult.subtasks?.length || 0} subtasks created
                </p>
              </div>
            </div>
          )}
        </Command>
      </div>
    </div>
  )
}