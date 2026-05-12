"use client"

import React, { useState, useEffect, useRef, useCallback } from "react"
import dynamic from "next/dynamic"
import { PanelGroup, Panel, PanelResizeHandle } from "react-resizable-panels"
import { Sparkles, GitBranch, FileCode, Terminal, MessageSquare, ChevronDown, Menu, Clock, History, Settings, ChevronRight } from "lucide-react"
import { Terminal as XTerm } from "xterm"
import { FitAddon } from "xterm-addon-fit"
import "xterm/css/xterm.css"

import { TopBar } from "@/components/workspace/TopBar"
import { SidebarRail } from "@/components/workspace/SidebarRail"
import { EditorTabs } from "@/components/workspace/EditorTabs"
import { ChatInterface } from "@/components/workspace/ChatInterface"
import { CommandPalette } from "@/components/workspace/CommandPalette"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"

// Dynamically import Monaco to avoid SSR issues
const MonacoEditor = dynamic(() => import("@/components/editor/MonacoEditor"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-[#09090b]">
      <div className="animate-pulse text-muted-foreground">Loading editor...</div>
    </div>
  )
})

interface FileNode {
  name: string
  path: string
  type: "file" | "dir"
  children?: FileNode[]
}

interface ActivityItem {
  id: string
  type: "task_start" | "task_complete" | "task_error" | "agent_log" | "system"
  message: string
  timestamp: string
  taskId?: string
}

interface OmniCodeWorkspaceProps {
  params?: {
    owner?: string
    repo?: string
  }
}

export default function WorkspacePage({ params }: OmniCodeWorkspaceProps) {
  const [activePanel, setActivePanel] = useState<"editor" | "terminal" | "chat">("editor")
  const [activeFile, setActiveFile] = useState<string | null>(null)
  const [fileTree, setFileTree] = useState<FileNode[]>([])
  const [currentContent, setCurrentContent] = useState<string>("")
  const [isIndexing, setIsIndexing] = useState(false)
  const [showCommandPalette, setShowCommandPalette] = useState(false)
  const [activityStream, setActivityStream] = useState<ActivityItem[]>([])
  const [selectedTask, setSelectedTask] = useState<string | null>(null)
  const [terminalSessionId] = useState(() => `session_${Date.now()}`)
  
  const terminalRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<XTerm | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)

  const owner = params?.owner || "example"
  const repo = params?.repo || "project"

  // Initialize terminal
  useEffect(() => {
    if (!terminalRef.current) return

    const term = new XTerm({
      theme: {
        background: '#09090b',
        foreground: '#e4e4e7',
        cursor: '#f4f4f5',
        selectionBackground: '#3f3f46',
        black: '#18181b',
        red: '#ef4444',
        green: '#22c55e',
        yellow: '#eab308',
        blue: '#3b82f6',
        magenta: '#a855f7',
        cyan: '#06b6d4',
        white: '#e4e4e7',
      },
      fontSize: 13,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      cursorBlink: true,
      cursorStyle: 'bar',
      scrollback: 10000,
    })

    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.open(terminalRef.current)
    fitAddon.fit()

    xtermRef.current = term

    // Connect to WebSocket terminal
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/terminal/${terminalSessionId}`
    
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      term.write('\x1b[32mConnected to OmniCode terminal\x1b[0m\r\n\r\n')
      term.write('\x1b[90m$ \x1b[0m')
    }

    ws.onmessage = (event) => {
      term.write(event.data)
    }

    ws.onerror = () => {
      term.write('\r\n\x1b[31mConnection error. Is the server running?\x1b[0m\r\n')
    }

    ws.onclose = () => {
      term.write('\r\n\x1b[90mConnection closed\x1b[0m\r\n')
    }

    // Handle terminal input
    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data)
      }
    })

    // Handle resize
    const handleResize = () => {
      try {
        fitAddon.fit()
        // Send resize event to server
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'resize',
            cols: term.cols,
            rows: term.rows
          }))
        }
      } catch (e) {
        // Terminal may not be visible
      }
    }

    window.addEventListener('resize', handleResize)

    // Initial resize
    setTimeout(handleResize, 100)

    return () => {
      window.removeEventListener('resize', handleResize)
      ws.close()
      term.dispose()
    }
  }, [terminalSessionId])

  // Initialize SSE activity stream
  useEffect(() => {
    // Connect to activity stream via SSE
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const eventSource = new EventSource(`${baseUrl}/api/stream/default`)
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'task_update' || data.type === 'agent_log') {
          const newItem: ActivityItem = {
            id: `${Date.now()}`,
            type: data.type === 'task_update' ? 'agent_log' : 'agent_log',
            message: data.message || data.task?.title || 'Task update',
            timestamp: new Date().toISOString(),
            taskId: data.task_id
          }
          setActivityStream(prev => [newItem, ...prev].slice(0, 100))
        }
      } catch (e) {
        // Ignore parse errors
      }
    }

    eventSource.onerror = () => {
      // Reconnect on error
      setTimeout(() => {
        eventSource.close()
      }, 5000)
    }

    return () => {
      eventSource.close()
    }
  }, [])

  // Fetch file tree
  useEffect(() => {
    async function fetchTree() {
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const res = await fetch(`${baseUrl}/api/repos/${owner}/${repo}/tree`)
        if (res.ok) {
          const data = await res.json()
          const files = data.files || []
          
          // Build tree structure
          const tree = buildFileTree(files)
          setFileTree(tree)
        }
      } catch (e) {
        // Use sample tree on error
        setFileTree(sampleFileTree)
      }
    }

    fetchTree()
  }, [owner, repo])

  // Load file content
  const loadFile = useCallback(async (path: string) => {
    setActiveFile(path)
    
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${baseUrl}/api/repos/${owner}/${repo}/file?path=${encodeURIComponent(path)}`)
      if (res.ok) {
        const data = await res.json()
        setCurrentContent(data.content)
      }
    } catch (e) {
      setCurrentContent('// Unable to load file content')
    }
  }, [owner, repo])

  // Run decomposition
  const runDecomposition = useCallback(async (goal: string) => {
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const res = await fetch(`${baseUrl}/api/decompose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal, context: { workspace_id: 1 } })
      })
      
      if (res.ok) {
        const graph = await res.json()
        
        // Add to activity stream
        const newItem: ActivityItem = {
          id: `decompose_${Date.now()}`,
          type: 'system',
          message: `Decomposed: ${graph.subtasks?.length || 0} subtasks`,
          timestamp: new Date().toISOString()
        }
        setActivityStream(prev => [newItem, ...prev].slice(0, 100))
        
        return graph
      }
    } catch (e) {
      console.error('Decomposition failed:', e)
    }
    return null
  }, [])

  // Index repository
  const startIndexing = useCallback(async () => {
    setIsIndexing(true)
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      await fetch(`${baseUrl}/api/repos/${owner}/${repo}/index`, {
        method: 'POST'
      })
    } catch (e) {
      console.error('Indexing failed:', e)
    }
    setTimeout(() => setIsIndexing(false), 3000)
  }, [owner, repo])

  // Command palette keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setShowCommandPalette(true)
      }
      if (e.key === 'Escape') {
        setShowCommandPalette(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <div className="h-screen w-screen flex flex-col bg-background overflow-hidden">
      <TopBar 
        owner={owner} 
        repo={repo} 
        onCommandPalette={() => setShowCommandPalette(true)} 
      />
      
      <div className="flex-1 flex overflow-hidden">
        <SidebarRail 
          fileTree={fileTree}
          onFileSelect={loadFile}
          activeFile={activeFile}
        />
        
        <div className="flex-1 flex flex-col overflow-hidden">
          <EditorTabs activeFile={activeFile} />
          
          <PanelGroup direction="vertical" className="flex-1">
            <Panel defaultSize={65} minSize={30}>
              <div className="h-full w-full flex flex-col">
                <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-[#09090b]">
                  <FileCode className="w-4 h-4 text-primary" />
                  <span className="text-sm font-medium">{activeFile || 'No file selected'}</span>
                  <div className="ml-auto flex items-center gap-2">
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => runDecomposition('Analyze and improve the current file')}
                    >
                      <Sparkles className="w-4 h-4 mr-1" />
                      Analyze
                    </Button>
                    {isIndexing ? (
                      <Badge variant="outline" className="animate-pulse">Indexing...</Badge>
                    ) : (
                      <Button variant="ghost" size="sm" onClick={startIndexing}>
                        <GitBranch className="w-4 h-4 mr-1" />
                        Index
                      </Button>
                    )}
                  </div>
                </div>
                
                <div className="flex-1 overflow-hidden">
                  <MonacoEditor
                    value={currentContent}
                    onChange={setCurrentContent}
                    language={getLanguage(activeFile || '')}
                  />
                </div>
              </div>
            </Panel>
            
            <PanelResizeHandle className="h-1 bg-border hover:bg-primary/50 transition-colors cursor-row-resize" />
            
            <Panel defaultSize={35} minSize={20}>
              <div className="h-full flex flex-col">
                <div className="flex items-center gap-2 px-4 py-2 border-b border-border bg-[#09090b]">
                  <div className="flex gap-1">
                    <button
                      onClick={() => setActivePanel("editor")}
                      className={cn(
                        "px-3 py-1 text-xs rounded transition-colors",
                        activePanel === "editor" ? "bg-primary/20 text-primary" : "hover:bg-muted"
                      )}
                    >
                      Files
                    </button>
                    <button
                      onClick={() => setActivePanel("terminal")}
                      className={cn(
                        "px-3 py-1 text-xs rounded transition-colors",
                        activePanel === "terminal" ? "bg-primary/20 text-primary" : "hover:bg-muted"
                      )}
                    >
                      Terminal
                    </button>
                    <button
                      onClick={() => setActivePanel("chat")}
                      className={cn(
                        "px-3 py-1 text-xs rounded transition-colors",
                        activePanel === "chat" ? "bg-primary/20 text-primary" : "hover:bg-muted"
                      )}
                    >
                      Chat
                    </button>
                  </div>
                  
                  <div className="ml-auto flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px]">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-500 mr-1.5" />
                      Connected
                    </Badge>
                  </div>
                </div>
                
                {activePanel === "terminal" ? (
                  <div ref={terminalRef} className="flex-1 bg-[#09090b] p-2" />
                ) : activePanel === "chat" ? (
                  <ChatInterface />
                ) : (
                  <ScrollArea className="flex-1 p-4">
                    <div className="space-y-3">
                      <h3 className="text-sm font-semibold text-muted-foreground">Activity Stream</h3>
                      {activityStream.map((item) => (
                        <div key={item.id} className="flex items-start gap-2 text-sm">
                          <div className={cn(
                            "w-2 h-2 rounded-full mt-1.5",
                            item.type === 'task_start' ? 'bg-blue-500' :
                            item.type === 'task_complete' ? 'bg-green-500' :
                            item.type === 'task_error' ? 'bg-red-500' :
                            'bg-muted-foreground'
                          )} />
                          <div>
                            <p className="text-foreground">{item.message}</p>
                            <p className="text-[10px] text-muted-foreground">
                              {new Date(item.timestamp).toLocaleTimeString()}
                            </p>
                          </div>
                        </div>
                      ))}
                      {activityStream.length === 0 && (
                        <p className="text-sm text-muted-foreground">No activity yet</p>
                      )}
                    </div>
                  </ScrollArea>
                )}
              </div>
            </Panel>
          </PanelGroup>
        </div>
      </div>
      
      {showCommandPalette && (
        <CommandPalette 
          onClose={() => setShowCommandPalette(false)}
          onDecompose={runDecomposition}
        />
      )}
    </div>
  )
}

// Helper functions
function buildFileTree(files: any[]): FileNode[] {
  const root: FileNode[] = []
  const dirs: Record<string, FileNode> = {}

  for (const file of files) {
    const parts = file.path.split('/')
    let current = root
    let currentPath = ''

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      currentPath += (currentPath ? '/' : '') + part

      if (i === parts.length - 1) {
        // Leaf node
        current.push({
          name: part,
          path: file.path,
          type: file.type === 'tree' ? 'dir' : 'file'
        })
      } else {
        // Directory
        if (!dirs[currentPath]) {
          const dirNode: FileNode = {
            name: part,
            path: currentPath,
            type: 'dir',
            children: []
          }
          dirs[currentPath] = dirNode
          current.push(dirNode)
        }
        current = dirs[currentPath].children || []
      }
    }
  }

  return root
}

function getLanguage(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase()
  const langMap: Record<string, string> = {
    'ts': 'typescript',
    'tsx': 'typescript',
    'js': 'javascript',
    'jsx': 'javascript',
    'py': 'python',
    'go': 'go',
    'rs': 'rust',
    'java': 'java',
    'json': 'json',
    'md': 'markdown',
    'css': 'css',
    'html': 'html',
  }
  return langMap[ext || ''] || 'plaintext'
}

// Sample file tree for demo
const sampleFileTree: FileNode[] = [
  {
    name: "src",
    path: "src",
    type: "dir",
    children: [
      {
        name: "components",
        path: "src/components",
        type: "dir",
        children: [
          { name: "Button.tsx", path: "src/components/Button.tsx", type: "file" },
          { name: "Card.tsx", path: "src/components/Card.tsx", type: "file" },
        ]
      },
      {
        name: "hooks",
        path: "src/hooks",
        type: "dir",
        children: [
          { name: "useAuth.ts", path: "src/hooks/useAuth.ts", type: "file" },
        ]
      },
      { name: "App.tsx", path: "src/App.tsx", type: "file" },
      { name: "index.tsx", path: "src/index.tsx", type: "file" },
    ]
  },
  {
    name: "package.json",
    path: "package.json",
    type: "file"
  },
  {
    name: "README.md",
    path: "README.md",
    type: "file"
  }
]