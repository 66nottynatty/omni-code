import "./globals.css"
import type { Metadata } from "next"

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
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  )
}
