import { getServerSession } from "next-auth"
import { signIn, signOut } from "next-auth/react"
import { authOptions } from "@/lib/auth"
import { Button } from "@/components/ui/button"

export default async function HomePage() {
  const session = await getServerSession(authOptions)

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="text-center space-y-6">
        <h1 className="text-5xl font-bold text-slate-900">OmniCode</h1>
        <p className="text-xl text-slate-600 max-w-md mx-auto">
          AI-powered code analysis and automation platform
        </p>
        
        <div className="flex gap-4 justify-center">
          {session ? (
            <>
              <a href="/repos">
                <Button size="lg">View Repositories</Button>
              </a>
              <Button 
                variant="outline" 
                size="lg" 
                onClick={() => signOut()}
              >
                Sign Out
              </Button>
            </>
          ) : (
            <a href="/api/auth/signin">
              <Button size="lg">Sign in with GitHub</Button>
            </a>
          )}
        </div>
        
        {session && (
          <p className="text-sm text-slate-500">
            Signed in as {session.user?.email || session.user?.name}
          </p>
        )}
      </div>
    </div>
  )
}
