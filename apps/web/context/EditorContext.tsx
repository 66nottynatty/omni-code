"use client"
import React, { createContext, useContext, useState } from 'react'

interface EditorContextType {
  editorContent: string
  setEditorContent: (content: string) => void
  editorLanguage: string
  setEditorLanguage: (lang: string) => void
  activeFile: string | null
  setActiveFile: (path: string | null) => void
}

const EditorContext = createContext<EditorContextType | undefined>(undefined)

export const EditorProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [editorContent, setEditorContent] = useState("")
  const [editorLanguage, setEditorLanguage] = useState("typescript")
  const [activeFile, setActiveFile] = useState<string | null>(null)

  return (
    <EditorContext.Provider value={{
      editorContent, setEditorContent,
      editorLanguage, setEditorLanguage,
      activeFile, setActiveFile
    }}>
      {children}
    </EditorContext.Provider>
  )
}

export const useEditor = () => {
  const context = useContext(EditorContext)
  if (!context) throw new Error("useEditor must be used within EditorProvider")
  return context
}
