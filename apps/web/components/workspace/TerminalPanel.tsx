"use client"
import React, { useEffect, useRef, useState } from 'react'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'

export const TerminalPanel: React.FC = () => {
  const terminalRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<Terminal | null>(null)
  const [sessionId] = useState(() => `session_${Date.now()}`)

  useEffect(() => {
    if (!terminalRef.current) return

    const term = new Terminal({
      theme: {
        background: '#1e1e1e',
        foreground: '#e4e4e7',
      },
      fontSize: 13,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
    })
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.open(terminalRef.current)
    fitAddon.fit()

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`${protocol}//${window.location.hostname}:8000/ws/terminal/${sessionId}`)
    
    socket.onmessage = (event) => {
      term.write(event.data)
    }

    term.onData((data) => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(data)
      }
    })

    xtermRef.current = term

    return () => {
      socket.close()
      term.dispose()
    }
  }, [sessionId])

  return (
    <div className="h-full bg-[#1e1e1e] p-2">
      <div ref={terminalRef} className="h-full w-full" />
    </div>
  )
}
