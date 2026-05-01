"use client"

import React, { useState } from "react"
import { 
  Send, 
  Plus, 
  Paperclip, 
  Mic, 
  Sparkles,
  User,
  Bot,
  ChevronRight,
  Clock
} from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { motion, AnimatePresence } from "framer-motion"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
}

const initialMessages: Message[] = [
  {
    id: "1",
    role: "assistant",
    content: "Hello! I'm your OmniCode agent. How can I help you today?",
    timestamp: "10:00 AM"
  },
  {
    id: "2",
    role: "user",
    content: "Can you help me implement the new dashboard layout?",
    timestamp: "10:01 AM"
  },
  {
    id: "3",
    role: "assistant",
    content: "I've analyzed the project requirements. I'll start by creating the modular components for the dashboard. Would you like me to use Framer Motion for animations?",
    timestamp: "10:01 AM"
  }
]

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [input, setInput] = useState("")

  const handleSend = () => {
    if (!input.trim()) return
    const newMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    setMessages([...messages, newMessage])
    setInput("")
    
    // Simulate assistant response
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "I'm on it! I'll start implementing that right away.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
      setMessages(prev => [...prev, assistantMessage])
    }, 1000)
  }

  return (
    <div className="flex flex-col h-full bg-[#09090b] border-l border-border">
      <div className="h-12 px-4 flex items-center justify-between border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary" />
          <span className="text-sm font-semibold">Agent Chat</span>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="h-5 text-[10px] gap-1.5 border-border bg-[#18181b]">
            <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
            GPT-4o
          </Badge>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <Clock className="w-4 h-4 text-muted-foreground" />
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          <AnimatePresence initial={false}>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  "flex gap-3",
                  message.role === "user" ? "flex-row-reverse" : "flex-row"
                )}
              >
                <div className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center shrink-0 border",
                  message.role === "assistant" 
                    ? "bg-primary/10 border-primary/20 text-primary" 
                    : "bg-muted border-border text-muted-foreground"
                )}>
                  {message.role === "assistant" ? <Bot className="w-4 h-4" /> : <User className="w-4 h-4" />}
                </div>
                <div className={cn(
                  "flex flex-col gap-1 max-w-[85%]",
                  message.role === "user" ? "items-end" : "items-start"
                )}>
                  <div className={cn(
                    "rounded-2xl px-4 py-2 text-sm leading-relaxed",
                    message.role === "assistant" 
                      ? "bg-[#18181b] border border-border text-foreground" 
                      : "bg-primary text-primary-foreground"
                  )}>
                    {message.content}
                  </div>
                  <span className="text-[10px] text-muted-foreground px-1">{message.timestamp}</span>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </ScrollArea>

      <div className="p-4 bg-[#09090b] border-t border-border">
        <div className="relative bg-[#18181b] rounded-xl border border-border p-2 focus-within:ring-1 focus-within:ring-primary/50 transition-all shadow-lg">
          <textarea
            placeholder="Ask agent to do something..."
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            className="w-full bg-transparent border-none focus:ring-0 text-sm resize-none px-2 py-1 max-h-32 min-h-[40px]"
          />
          <div className="flex items-center justify-between mt-2 px-1">
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                <Plus className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                <Paperclip className="w-4 h-4" />
              </Button>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-foreground">
                <Mic className="w-4 h-4" />
              </Button>
            </div>
            <Button 
              size="sm" 
              className="h-8 w-8 rounded-lg p-0" 
              disabled={!input.trim()}
              onClick={handleSend}
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
        <div className="mt-2 flex items-center justify-center gap-4">
          <span className="text-[10px] text-muted-foreground">Press Enter to send, Shift+Enter for new line</span>
        </div>
      </div>
    </div>
  )
}
