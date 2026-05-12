"use client"

import React, { useState, useEffect } from "react"
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels"
import Editor from "@monaco-editor/react"
import { TopBar } from "@/components/workspace/TopBar"
import { SidebarRail } from "@/components/workspace/SidebarRail"
import { 
  ExplorerPanel, 
  GitPanel, 
  TasksPanel, 
  MemoryPanel 
} from "@/components/workspace/Panels"
import { ChatInterface } from "@/components/workspace/ChatInterface"
import { EditorTabs } from "@/components/workspace/EditorTabs"
import { CommandPalette } from "@/components/workspace/CommandPalette"
import { Terminal } from "@/components/workspace/Terminal"
import { motion, AnimatePresence } from "framer-motion"
import { getRepoTree, getRepoFile, indexRepo } from "@/lib/api"

export default function WorkspacePage({ params }: { params: { owner: string, repo: string } }) {
  const [activeTab, setActiveTab] = useState("explorer")
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [tree, setTree] = useState<any[]>([])
  const [currentFile, setCurrentFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>("")
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    async function loadTree() {
      try {
        const data = await getRepoTree(params.owner, params.repo)
        setTree(data)
      } catch (error) {
        console.error("Failed to load tree", error)
      }
    }
    loadTree()
  }, [params.owner, params.repo])

  const handleRefresh = async () => {
    try {
      await indexRepo(params.owner, params.repo)
      // Reload tree after indexing starts
      const data = await getRepoTree(params.owner, params.repo)
      setTree(data)
    } catch (error) {
      console.error("Failed to trigger indexing", error)
    }
  }

  const handleFileSelect = async (path: string) => {
    setCurrentFile(path)
    setIsLoading(true)
    try {
      const data = await getRepoFile(params.owner, params.repo, path)
      setFileContent(data.content)
    } catch (error) {
      console.error("Failed to load file", error)
      setFileContent("// Failed to load file")
    } finally {
      setIsLoading(false)
    }
  }

  const handleTabChange = (tab: string) => {
    if (activeTab === tab && isSidebarOpen) {
      setIsSidebarOpen(false)
    } else {
      setActiveTab(tab)
      setIsSidebarOpen(true)
    }
  }

  const renderSidebarContent = () => {
    switch (activeTab) {
      case "explorer": return <ExplorerPanel onFileSelect={handleFileSelect} tree={tree} onRefresh={handleRefresh} />
      case "git": return <GitPanel />
      case "tasks": return <TasksPanel />
      case "memory": return <MemoryPanel />
      default: return <ExplorerPanel onFileSelect={handleFileSelect} tree={tree} onRefresh={handleRefresh} />
    }
  }

  return (
    <div className="h-screen w-full flex flex-col bg-[#09090b] text-foreground select-none">
      <TopBar owner={params.owner} repo={params.repo} />
      
      <div className="flex-1 flex overflow-hidden">
        <SidebarRail activeTab={activeTab} setActiveTab={handleTabChange} />
        
        <div className="flex-1 overflow-hidden">
          <PanelGroup direction="vertical">
            <Panel defaultSize={70} minSize={30}>
              <PanelGroup direction="horizontal">
                {isSidebarOpen && (
                  <>
                    <Panel defaultSize={20} minSize={15} maxSize={40}>
                      <div className="h-full border-r border-border bg-[#09090b]">
                        <AnimatePresence mode="wait">
                          <motion.div
                            key={activeTab}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -10 }}
                            transition={{ duration: 0.15 }}
                            className="h-full"
                          >
                            {renderSidebarContent()}
                          </motion.div>
                        </AnimatePresence>
                      </div>
                    </Panel>
                    <PanelResizeHandle className="w-px bg-border hover:bg-primary/50 transition-colors" />
                  </>
                )}
                
                <Panel defaultSize={50} minSize={30}>
                  <div className="h-full flex flex-col">
                    <EditorTabs activeFile={currentFile} />
                    <div className="flex-1 relative">
                      {isLoading && (
                        <div className="absolute inset-0 bg-[#09090b]/50 z-10 flex items-center justify-center">
                          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-primary" />
                        </div>
                      )}
                      <Editor
                        height="100%"
                        path={currentFile || "welcome.ts"}
                        defaultLanguage="typescript"
                        theme="vs-dark"
                        value={fileContent || `// Welcome to OmniCode\n// Select a file to start editing`}
                        options={{
                          minimap: { enabled: false },
                          fontSize: 13,
                          fontFamily: "var(--font-mono)",
                          lineNumbers: "on",
                          roundedSelection: false,
                          scrollBeyondLastLine: false,
                          readOnly: false,
                          padding: { top: 10 },
                          cursorSmoothCaretAnimation: "on",
                          smoothScrolling: true,
                          automaticLayout: true,
                        }}
                      />
                    </div>
                  </div>
                </Panel>

                <PanelResizeHandle className="w-px bg-border hover:bg-primary/50 transition-colors" />

                <Panel defaultSize={30} minSize={20} maxSize={50}>
                  <ChatInterface />
                </Panel>
              </PanelGroup>
            </Panel>
            
            <PanelResizeHandle className="h-px bg-border hover:bg-primary/50 transition-colors" />
            
            <Panel defaultSize={30} minSize={10}>
              <div className="h-full flex flex-col bg-[#09090b]">
                <div className="h-9 px-4 flex items-center bg-[#18181b] border-b border-border text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  Terminal
                </div>
                <div className="flex-1">
                  <Terminal sessionId="default-session" />
                </div>
              </div>
            </Panel>
          </PanelGroup>
        </div>
      </div>
      
      <CommandPalette />
      
      {/* Footer / Status Bar */}
      <div className="h-6 bg-primary flex items-center justify-between px-3 shrink-0 text-primary-foreground text-[10px]">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 cursor-pointer hover:bg-white/10 px-1 rounded transition-colors">
            <span className="font-bold">main*</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span>0 errors</span>
            <span>0 warnings</span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 cursor-pointer hover:bg-white/10 px-1 rounded transition-colors">
            <span>TypeScript JSX</span>
          </div>
          <div className="flex items-center gap-1.5 cursor-pointer hover:bg-white/10 px-1 rounded transition-colors">
            <span>UTF-8</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span>Ln 1, Col 1</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-white/50" />
            <span>Agent Idle</span>
          </div>
        </div>
      </div>
    </div>
  )
}
