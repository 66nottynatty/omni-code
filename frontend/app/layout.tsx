import "./globals.css"
import type { Metadata } from "next"
import { Toaster } from "sonner"

export const metadata: Metadata = {
  title: "OmniCode",
  description: "AI-powered code analysis and automation platform",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased overflow-hidden h-screen w-screen bg-background text-foreground">
        {children}
        <Toaster theme="dark" position="bottom-right" />
      </body>
    </html>
  )
}
