"use client"

import React, { useEffect, useRef } from 'react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

interface TerminalProps {
  sessionId: string;
}

export function Terminal({ sessionId }: TerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

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
    });
    
    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.open(terminalRef.current);
    
    // Initial fit
    setTimeout(() => {
      try {
        fitAddon.fit();
      } catch (e) {}
    }, 100);
    
    xtermRef.current = term;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/terminal/${sessionId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      term.write('\x1b[32mConnected to OmniCode terminal\x1b[0m\r\n\r\n');
      term.write('\x1b[90m$ \x1b[0m');
    };

    ws.onmessage = (event) => {
      term.write(event.data);
    };

    ws.onerror = () => {
      term.write('\r\n\x1b[31mConnection error. Is the server running?\x1b[0m\r\n');
    };

    ws.onclose = () => {
      term.write('\r\n\x1b[90mConnection closed\x1b[0m\r\n');
    };

    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data);
      }
    });

    const handleResize = () => {
      try {
        fitAddon.fit();
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'resize',
            cols: term.cols,
            rows: term.rows
          }));
        }
      } catch (e) {}
    };
    
    window.addEventListener('resize', handleResize);

    return () => {
      ws.close();
      term.dispose();
      window.removeEventListener('resize', handleResize);
    };
  }, [sessionId]);

  return (
    <div className="h-full w-full bg-[#09090b] p-2">
      <div ref={terminalRef} className="h-full w-full" />
    </div>
  );
}
