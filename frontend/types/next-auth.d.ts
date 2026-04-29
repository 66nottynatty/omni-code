import NextAuth from "next-auth"
import type { NextAuthOptions } from "next-auth"
import { authOptions } from "@/lib/auth"

declare module "next-auth" {
  interface Session {
    accessToken?: string
    provider?: string
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string
    provider?: string
  }
}

export { authOptions }
