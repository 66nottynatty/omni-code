"use client"

import React, { useState, useRef, useEffect } from "react"
import { Send, Sparkles, User, Bot, Loader2, StopCircle } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { runOrchestrator, streamGraphLogs, getGraph } from "@/lib/api"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
  graphId?: string
  status?: "streaming" | "done" | "error"
}

interface ChatInterfaceProps {
  workspaceId?: number
}

export function ChatInterface({ workspaceId = 1 }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "Hello! I'm your OmniCode agent. Describe what you want to build or fix.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      status: "done"
    }
  ])
  const [input, setInput] = useState("")
  const [isRunning, setIsRunning] = useState(false)
  const [currentGraphId, setCurrentGraphId] = useState<string | null>(null)
  const stopRef = useRef<(() => void) | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isRunning) return

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      status: "done"
    }

    const assistantMsgId = (Date.now() + 1).toString()
    const assistantMsg: Message = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      status: "streaming"
    }

    setMessages(prev => [...prev, userMsg, assistantMsg])
    setInput("")
    setIsRunning(true)

    try {
      // Start the orchestrator
      const { graph_id } = await runOrchestrator(input, workspaceId)
      setCurrentGraphId(graph_id)

      // Stream real-time logs into the assistant message bubble
      const stop = streamGraphLogs(graph_id, (event) => {
        if (event.type === "token") {
          setMessages(prev => prev.map(m =>
            m.id === assistantMsgId
              ? { ...m, content: m.content + event.content }
              : m
          ))
        }

        if (event.type === "task_update") {
          setMessages(prev => prev.map(m =>
            m.id === assistantMsgId
              ? {
                  ...m,
                  content: m.content + `\n\n✅ **${event.task?.title}** — ${event.status}`
                }
              : m
          ))
        }

        if (event.type === "graph_update" && event.status === "completed") {
          setMessages(prev => prev.map(m =>
            m.id === assistantMsgId
              ? { ...m, status: "done", graphId: graph_id }
              : m
          ))
          setIsRunning(false)
          setCurrentGraphId(null)
          stop()
        }

        if (event.type === "graph_update" && event.status === "failed") {
          setMessages(prev => prev.map(m =>
            m.id === assistantMsgId
              ? { ...m, content: m.content + "\n\n❌ Task failed.", status: "error" }
              : m
          ))
          setIsRunning(false)
          stop()
        }
      })

      stopRef.current = stop
    } catch (err: any) {
      setMessages(prev => prev.map(m =>
        m.id === assistantMsgId
          ? { ...m, content: `Error: ${err.message}`, status: "error" }
          : m
      ))
      setIsRunning(false)
    }
  }

  const handleStop = () => {
    stopRef.current?.()
    setIsRunning(false)
    setCurrentGraphId(null)
  }

  return (
    <div className="flex flex-col h-full bg-[#09090b] border-l border-border">
      {/* Header */}
      <div className="h-12 px-4 flex items-center justify-between border-b border-border shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-primary" />
          <span className="text-sm font-semibold">Agent Chat</span>
        </div>
        <Badge variant="outline" className={cn(
          "h-5 text-[10px] gap-1.5 border-border bg-[#18181b]",
          isRunning && "border-yellow-500/30"
        )}>
          <div className={cn(
            "w-1.5 h-1.5 rounded-full",
            isRunning ? "bg-yellow-400 animate-pulse" : "bg-green-500"
          )} />
          {isRunning ? "Running" : "Ready"}
        </Badge>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-6">
          {messages.map((msg) => (
            <div key={msg.id} className={cn(
              "flex gap-3",
              msg.role === "user" ? "flex-row-reverse" : "flex-row"
            )}>
              <div className={cn(
                "w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5",
                msg.role === "user" ? "bg-primary" : "bg-[#18181b] border border-border"
              )}>
                {msg.role === "user"
                  ? <User className="w-3.5 h-3.5 text-primary-foreground" />
                  : <Bot className="w-3.5 h-3.5 text-muted-foreground" />
                }
              </div>
              <div className={cn(
                "max-w-[80%] rounded-xl px-4 py-2.5 text-sm",
                msg.role === "user"
                  ? "bg-primary text-primary-foreground rounded-tr-sm"
                  : "bg-[#18181b] border border-border rounded-tl-sm"
              )}>
                <p className="whitespace-pre-wrap leading-relaxed">
                  {msg.content}
                  {msg.status === "streaming" && (
                    <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-current animate-pulse rounded-sm" />
                  )}
                </p>
                <p className="text-[10px] mt-1 opacity-40">{msg.timestamp}</p>
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="p-4 border-t border-border shrink-0">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder="Describe what to build..."
            rows={1}
            disabled={isRunning}
            className="flex-1 resize-none bg-[#18181b] border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground disabled:opacity-50"
          />
          {isRunning ? (
            <Button size="icon" variant="destructive" onClick={handleStop} className="shrink-0 h-9 w-9">
              <StopCircle className="w-4 h-4" />
            </Button>
          ) : (
            <Button size="icon" onClick={handleSend} disabled={!input.trim()} className="shrink-0 h-9 w-9">
              <Send className="w-4 h-4" />
            </Button>
          )}
        </div>
        <p className="text-[10px] text-muted-foreground mt-1.5 text-center">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
