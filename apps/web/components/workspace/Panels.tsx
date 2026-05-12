"use client"

import React, { useEffect, useState } from "react"
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
import { useEditor } from "@/context/EditorContext"
import { useParams } from "next/navigation"

export function ExplorerPanel() {
  const { owner, repo } = useParams()
  const [tree, setTree] = useState<any[]>([])
  const { setActiveFile, setEditorContent, setEditorLanguage } = useEditor()

  useEffect(() => {
    fetch(`/api/repos/${owner}/${repo}/tree`)
      .then(res => res.json())
      .then(data => setTree(data.tree || []))
      .catch(() => setTree([]))
  }, [owner, repo])

  const handleFileClick = async (path: string) => {
    const res = await fetch(`/api/repos/${owner}/${repo}/file?path=${path}`)
    const data = await res.json()
    setActiveFile(path)
    setEditorContent(data.content)
    const ext = path.split('.').pop()
    setEditorLanguage(ext === 'tsx' ? 'typescript' : ext || 'text')
  }

  return (
    <div className="flex flex-col h-full bg-[#09090b]">
      <div className="h-9 px-4 flex items-center justify-between shrink-0">
        <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Explorer</span>
      </div>
      <ScrollArea className="flex-1">
        <div className="py-2">
          {tree.map((item: any) => (
            <div 
              key={item.path} 
              className="flex items-center gap-1 px-2 py-1 hover:bg-accent/50 cursor-pointer text-sm"
              onClick={() => item.type === 'blob' && handleFileClick(item.path)}
            >
              {item.type === 'tree' ? <FolderIcon className="w-4 h-4 text-blue-400" /> : <FileIcon className="w-4 h-4 text-muted-foreground" />}
              <span className="truncate">{item.path}</span>
            </div>
          ))}
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
      </div>
      <ScrollArea className="flex-1">
        <div className="p-4">
           <span className="text-xs text-muted-foreground">No pending changes</span>
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
      </div>
      <ScrollArea className="flex-1">
         <div className="p-4">
           <span className="text-xs text-muted-foreground">Waiting for task...</span>
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
        <div className="p-4">
           <span className="text-xs text-muted-foreground">Indexing repository...</span>
        </div>
      </ScrollArea>
    </div>
  )
}
