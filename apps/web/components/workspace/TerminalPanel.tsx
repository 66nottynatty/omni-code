"use client"
import React, { useEffect, useRef } from 'react'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import 'xterm/css/xterm.css'

export const TerminalPanel: React.FC = () => {
  const terminalRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<Terminal | null>(null)

  useEffect(() => {
    if (!terminalRef.current) return

    const term = new Terminal({
      theme: {
        background: '#1e1e1e'
      }
    })
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.open(terminalRef.current)
    fitAddon.fit()

    const socket = new WebSocket(`ws://${window.location.host}/api/terminal`)
    
    socket.onmessage = (event) => {
      term.write(event.data)
    }

    term.onData((data) => {
      socket.send(data)
    })

    xtermRef.current = term

    return () => {
      socket.close()
      term.dispose()
    }
  }, [])

  return (
    <div className="h-full bg-[#1e1e1e] p-2">
      <div ref={terminalRef} className="h-full w-full" />
    </div>
  )
}
