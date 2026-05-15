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
import dynamic from "next/dynamic"
import { motion, AnimatePresence } from "framer-motion"
import { EditorProvider, useEditor } from "@/context/EditorContext"

const TerminalPanel = dynamic(
  () => import("@/components/workspace/TerminalPanel").then((mod) => mod.TerminalPanel),
  { ssr: false }
)

function WorkspaceContent({ params }: { params: { owner: string, repo: string } }) {
  const [activeTab, setActiveTab] = useState("explorer")
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const { editorContent, editorLanguage, setEditorContent, activeFile } = useEditor()

  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)
  
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setCommandPaletteOpen(true)
      }
      if (e.key === 'Escape') {
        setCommandPaletteOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleSendMessage = async (goal: string): Promise<any> => { console.log("goal:", goal) }
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
      case "explorer": return <ExplorerPanel />
      case "git": return <GitPanel />
      case "tasks": return <TasksPanel />
      case "memory": return <MemoryPanel />
      default: return <ExplorerPanel />
    }
  }

  return (
    <div className="h-screen w-full flex flex-col bg-[#09090b] text-foreground select-none">
      <TopBar 
        owner={params.owner} 
        repo={params.repo} 
        onCommandPalette={() => setCommandPaletteOpen(true)}
      />
      
      <div className="flex-1 flex overflow-hidden">
        <SidebarRail activeTab={activeTab} setActiveTab={handleTabChange} />
        
        <div className="flex-1 overflow-hidden">
          <PanelGroup direction="vertical">
            <Panel defaultSize={70}>
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
                    <EditorTabs activeFile={activeFile} />
                    <div className="flex-1">
                      <Editor
                        height="100%"
                        language={editorLanguage}
                        theme="vs-dark"
                        value={editorContent}
                        onChange={(val) => setEditorContent(val || "")}
                        options={{
                          minimap: { enabled: false },
                          fontSize: 13,
                          fontFamily: "var(--font-mono)",
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
              <TerminalPanel />
            </Panel>
          </PanelGroup>
        </div>
      </div>
      
      {commandPaletteOpen && (
        <CommandPalette
          onClose={() => setCommandPaletteOpen(false)}
          onDecompose={(goal: string) => {
            setCommandPaletteOpen(false)
            handleSendMessage(goal)
          }}
        />
      )}
    </div>
  )
}

export default function WorkspacePage({ 
  params,
  searchParams: _searchParams 
}: { 
  params: { owner: string, repo: string };
  searchParams: { [key: string]: string | string[] | undefined };
}) {
  return (
    <EditorProvider>
      <WorkspaceContent params={params} />
    </EditorProvider>
  )
}
