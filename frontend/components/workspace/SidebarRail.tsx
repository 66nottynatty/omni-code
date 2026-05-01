"use client"

import React from "react"
import { 
  Files, 
  GitBranch, 
  Terminal, 
  Database, 
  Search,
  LayoutGrid,
  UserCircle
} from "lucide-react"
import { cn } from "@/lib/utils"

interface SidebarRailProps {
  activeTab: string
  setActiveTab: (tab: string) => void
}

const items = [
  { id: "explorer", icon: Files, label: "Explorer" },
  { id: "search", icon: Search, label: "Search" },
  { id: "git", icon: GitBranch, label: "Source Control" },
  { id: "tasks", icon: Terminal, label: "Agent Tasks" },
  { id: "memory", icon: Database, label: "Agent Memory" },
  { id: "extensions", icon: LayoutGrid, label: "Extensions" },
]

export function SidebarRail({ activeTab, setActiveTab }: SidebarRailProps) {
  return (
    <div className="w-12 bg-[#09090b] border-r border-border flex flex-col items-center py-4 gap-4">
      {items.map((item) => (
        <button
          key={item.id}
          onClick={() => setActiveTab(item.id)}
          title={item.label}
          className={cn(
            "p-2 rounded-md transition-colors relative group",
            activeTab === item.id 
              ? "text-primary bg-primary/10" 
              : "text-muted-foreground hover:text-foreground hover:bg-accent"
          )}
        >
          <item.icon className="w-5 h-5" />
          {activeTab === item.id && (
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-primary rounded-r-full" />
          )}
        </button>
      ))}
      
      <div className="mt-auto flex flex-col gap-4">
        <button title="Profile" className="p-2 text-muted-foreground hover:text-foreground transition-colors">
          <UserCircle className="w-5 h-5" />
        </button>
      </div>
    </div>
  )
}
