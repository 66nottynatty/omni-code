import { getServerSession } from "next-auth"
import { authOptions } from "@/lib/auth"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface GitHubRepo {
  id: number
  name: string
  full_name: string
  description: string | null
  html_url: string
  stargazers_count: number
  forks_count: number
  language: string | null
  private: boolean
  updated_at: string
}

async function fetchGitHubRepos(accessToken: string): Promise<GitHubRepo[]> {
  const response = await fetch("https://api.github.com/user/repos?per_page=100&sort=updated", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      Accept: "application/vnd.github.v3+json",
    },
    next: { revalidate: 60 },
  })

  if (!response.ok) {
    throw new Error("Failed to fetch repositories")
  }

  return response.json()
}

export default async function ReposPage() {
  const session = await getServerSession(authOptions)
  
  if (!session?.accessToken) {
    return (
      <div className="container mx-auto py-10">
        <Card className="max-w-md mx-auto">
          <CardHeader>
            <CardTitle>Authentication Required</CardTitle>
            <CardDescription>
              Please sign in with GitHub to view your repositories.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <a
              href="/api/auth/signin"
              className="inline-flex items-center justify-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Sign in with GitHub
            </a>
          </CardContent>
        </Card>
      </div>
    )
  }

  let repos: GitHubRepo[] = []
  let error: string | null = null

  try {
    repos = await fetchGitHubRepos(session.accessToken as string)
  } catch (e) {
    error = e instanceof Error ? e.message : "An error occurred"
  }

  return (
    <div className="container mx-auto py-10">
      <h1 className="text-3xl font-bold mb-6">Your Repositories</h1>
      
      {error ? (
        <Card className="max-w-md mx-auto">
          <CardHeader>
            <CardTitle className="text-destructive">Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      ) : repos.length === 0 ? (
        <Card className="max-w-md mx-auto">
          <CardHeader>
            <CardTitle>No Repositories</CardTitle>
            <CardDescription>
              You don&apos;t have any repositories yet. Create one on GitHub to get started.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {repos.map((repo) => (
            <a
              key={repo.id}
              href={repo.html_url}
              target="_blank"
              rel="noopener noreferrer"
              className="block"
            >
              <Card className="h-full transition-shadow hover:shadow-lg">
                <CardHeader>
                  <CardTitle className="text-lg truncate">{repo.name}</CardTitle>
                  <CardDescription className="flex items-center gap-2">
                    {repo.private ? (
                      <span className="px-2 py-0.5 text-xs bg-muted rounded">Private</span>
                    ) : (
                      <span className="px-2 py-0.5 text-xs bg-primary text-primary-foreground rounded">Public</span>
                    )}
                    {repo.language && (
                      <span className="text-xs">{repo.language}</span>
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {repo.description || "No description provided"}
                  </p>
                  <div className="flex items-center gap-4 mt-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M8 .25a.75.75 0 01.673.418l1.88 1.376 2.456.49a.75.75 0 01.416 1.279l-1.776 1.732a.75.75 0 01-.215.071l-2.352-.362a.75.75 0 01-.39-.242l-1.268-1.38a.75.75 0 01-.239-.67V.25a.75.75 0 01.75-.75z"/>
                        <path d="M8 1.5a.75.75 0 01.75.75v1.5H12a.75.75 0 010 1.5H8.75A.75.75 0 018 3.25v-1.5A.75.75 0 018 1.5zM4.5 3.25a.75.75 0 01.75-.75H8a.75.75 0 010 1.5H5.25A.75.75 0 014.5 3.25zm0 2.5a.75.75 0 01.75-.75H8a.75.75 0 010 1.5H5.25A.75.75 0 014.5 5.75zm0 2.5a.75.75 0 01.75-.75H8a.75.75 0 010 1.5H5.25A.75.75 0 014.5 8.25z"/>
                      </svg>
                      {repo.stargazers_count}
                    </span>
                    <span className="flex items-center gap-1">
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75v-.878a2.25 2.25 0 111.5 0v.878a2.25 2.25 0 01-2.25 2.25h-1.5v2.128a2.251 2.251 0 11-1.5 0V8.37h-1.5A2.251 2.251 0 013.5 6.12v-.878a2.25 2.25 0 111.5 0zM5 3.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm6.75.75a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm1.75-.75a.75.75 0 11-1.5 0 .75.75 0 011.5 0z"/>
                      </svg>
                      {repo.forks_count}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
