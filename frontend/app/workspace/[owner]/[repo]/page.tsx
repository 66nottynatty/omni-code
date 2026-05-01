"use client"

import React, { useState } from "react"
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
import { motion, AnimatePresence } from "framer-motion"

export default function WorkspacePage({ params }: { params: { owner: string, repo: string } }) {
  const [activeTab, setActiveTab] = useState("explorer")
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

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
      <TopBar owner={params.owner} repo={params.repo} />
      
      <div className="flex-1 flex overflow-hidden">
        <SidebarRail activeTab={activeTab} setActiveTab={handleTabChange} />
        
        <div className="flex-1 overflow-hidden">
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
                <EditorTabs />
                <div className="flex-1">
                  <Editor
                    height="100%"
                    defaultLanguage="typescript"
                    theme="vs-dark"
                    value={`import React from "react"

export default function App() {
  return (
    <div className="min-h-screen bg-slate-900 text-white p-8">
      <h1 className="text-4xl font-bold">Hello OmniCode</h1>
      <p className="mt-4 text-slate-400">
        This is a premium dark theme IDE experience.
      </p>
    </div>
  )
}
`}
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
