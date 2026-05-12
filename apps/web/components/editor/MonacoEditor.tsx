"use client"

import React, { useEffect, useRef } from "react"
import Editor, { DiffEditor, OnMount, OnChange } from "@monaco-editor/react"
import type { editor } from "monaco-editor"

export interface MonacoEditorProps {
  value: string
  onChange: (value: string) => void
  language?: string
  readOnly?: boolean
  height?: string | number
}

export default function MonacoEditor({
  value,
  onChange,
  language = "typescript",
  readOnly = false,
  height = "100%"
}: MonacoEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null)

  const handleEditorMount: OnMount = (editor, monaco) => {
    editorRef.current = editor

    // Configure editor theme
    monaco.editor.defineTheme("omnicode-dark", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "comment", foreground: "6b7280", fontStyle: "italic" },
        { token: "keyword", foreground: "c084fc" },
        { token: "string", foreground: "22c55e" },
        { token: "number", foreground: "f59e0b" },
        { token: "type", foreground: "38bdf8" },
        { token: "function", foreground: "a78bfa" },
        { token: "variable", foreground: "e4e4e7" },
      ],
      colors: {
        "editor.background": "#09090b",
        "editor.foreground": "#e4e4e7",
        "editor.lineHighlightBackground": "#18181b",
        "editor.selectionBackground": "#3f3f46",
        "editorCursor.foreground": "#f4f4f5",
        "editorLineNumber.foreground": "#52525b",
        "editorLineNumber.activeForeground": "#a1a1aa",
        "editor.inactiveSelectionBackground": "#27272a",
        "editorIndentGuide.background": "#27272a",
        "editorIndentGuide.activeBackground": "#3f3f46",
        "scrollbar.shadow": "#000000",
        "scrollbarSlider.background": "#3f3f4666",
        "scrollbarSlider.hoverBackground": "#52525b88",
        "scrollbarSlider.activeBackground": "#71717a88",
      },
    })

    monaco.editor.setTheme("omnicode-dark")

    // Configure editor options
    editor.updateOptions({
      fontSize: 13,
      fontFamily: "Menlo, Monaco, 'Courier New', monospace",
      minimap: { enabled: true, scale: 1 },
      scrollBeyondLastLine: false,
      renderLineHighlight: "all",
      cursorBlinking: "smooth",
      cursorSmoothCaretAnimation: "on",
      smoothScrolling: true,
      padding: { top: 16, bottom: 16 },
      lineNumbers: "on",
      glyphMargin: false,
      folding: true,
      lineDecorationsWidth: 10,
      bracketPairColorization: { enabled: true },
      guides: {
        bracketPairs: true,
        indentation: true,
      },
      suggest: {
        showKeywords: true,
        showSnippets: true,
        showFunctions: true,
        showVariables: true,
      },
    })

    // Focus editor
    editor.focus()
  }

  const handleChange: OnChange = (newValue) => {
    if (newValue !== undefined) {
      onChange(newValue)
    }
  }

  // Auto-resize based on content (optional)
  const detectLanguage = (value: string): string => {
    // Simple language detection based on content patterns
    if (value.includes("import React") || value.includes("from 'react")) {
      return language === "typescript" ? "typescript" : "javascript"
    }
    if (value.includes("def ") || value.includes("import ")) {
      return "python"
    }
    if (value.includes("func ") && value.includes("package ")) {
      return "go"
    }
    if (value.includes("fn ") && value.includes("let ")) {
      return "rust"
    }
    return language
  }

  return (
    <div className="h-full w-full">
      <Editor
        height={height}
        language={detectLanguage(value)}
        value={value}
        onChange={handleChange}
        onMount={handleEditorMount}
        theme="vs-dark"
        options={{
          readOnly,
          automaticLayout: true,
          scrollBeyondLastLine: false,
          minimap: { enabled: true },
          fontSize: 13,
          fontFamily: "Menlo, Monaco, 'Courier New', monospace",
          tabSize: 2,
          insertSpaces: true,
          wordWrap: "on",
          lineNumbers: "on",
          renderWhitespace: "selection",
          bracketPairColorization: { enabled: true },
        }}
        loading={
          <div className="h-full w-full flex items-center justify-center bg-[#09090b]">
            <div className="text-muted-foreground animate-pulse">
              Loading editor...
            </div>
          </div>
        }
      />
    </div>
  )
}

export function MonacoDiffEditor({
  original,
  modified,
  language = "typescript",
  height = "100%"
}: {
  original: string
  modified: string
  language?: string
  height?: string | number
}) {
  return (
    <div className="h-full w-full">
      <DiffEditor
        height={height}
        language={language}
        original={original}
        modified={modified}
        theme="vs-dark"
        options={{
          renderSideBySide: true,
          readOnly: true,
          minimap: { enabled: false },
          fontSize: 13,
          fontFamily: "Menlo, Monaco, 'Courier New', monospace",
          automaticLayout: true,
        }}
        loading={
          <div className="h-full w-full flex items-center justify-center bg-[#09090b]">
            <div className="text-muted-foreground animate-pulse">
              Loading diff editor...
            </div>
          </div>
        }
      />
    </div>
  )
}
