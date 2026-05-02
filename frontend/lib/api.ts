import axios from "axios"

// Create axios instance with default configuration
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    // Get token from cookie (set by NextAuth)
    const token = document.cookie
      .split("; ")
      .find((row) => row.startsWith("next-auth.session-token="))
      ?.split("=")[1]

    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - redirect to login
      if (typeof window !== "undefined") {
        window.location.href = "/"
      }
    }
    return Promise.reject(error)
  }
)

export default api

// Helper functions for API calls
export async function getTasks(workspaceId?: number, status?: string) {
  const params = new URLSearchParams()
  if (workspaceId) params.append("workspace_id", workspaceId.toString())
  if (status) params.append("status", status)

  const response = await api.get(`/api/tasks?${params.toString()}`)
  return response.data
}

export async function getTask(taskId: number) {
  const response = await api.get(`/api/tasks/${taskId}`)
  return response.data
}

export async function createTask(workspaceId: number, taskType: string, payload: object) {
  const response = await api.post("/api/tasks", {
    workspace_id: workspaceId,
    task_type: taskType,
    payload,
  })
  return response.data
}

export async function resolveBlocker(taskId: number, resolution: string) {
  const response = await api.post(`/api/tasks/${taskId}/resolve`, { resolution })
  return response.data
}

export async function getThreadHistory(threadId: number) {
  const response = await api.get(`/api/threads/${threadId}/history`)
  return response.data
}

export async function rollbackAction(actionId: number) {
  const response = await api.post(`/api/rollback/${actionId}`)
  return response.data
}

export async function getModels() {
  const response = await api.get("/api/models")
  return response.data
}

export async function acceptChange(changeId: number) {
  const response = await api.post(`/api/pending-changes/${changeId}/accept`)
  return response.data
}

export async function rejectChange(changeId: number) {
  const response = await api.post(`/api/pending-changes/${changeId}/reject`)
  return response.data
}

export async function checkHealth() {
  const response = await api.get("/health")
  return response.data
}

// Skills API helpers
export async function getSkills(workspaceId?: number, category?: string) {
  const params = new URLSearchParams()
  if (workspaceId) params.append('workspace_id', workspaceId.toString())
  if (category) params.append('category', category)

  const response = await api.get(`/api/skills?${params.toString()}`)
  return response.data
}

export async function getSkill(skillId: number) {
  const response = await api.get(`/api/skills/${skillId}`)
  return response.data
}

export async function createSkill(skill: {
  name: string
  description: string
  content: string
  category: string
  workspace_id?: number | null
  is_global?: boolean
}) {
  const response = await api.post("/api/skills", skill)
  return response.data
}

export async function updateSkill(skillId: number, skill: {
  name?: string
  description?: string
  content?: string
  category?: string
}) {
  const response = await api.put(`/api/skills/${skillId}`, skill)
  return response.data
}

export async function deleteSkill(skillId: number) {
  const response = await api.delete(`/api/skills/${skillId}`)
  return response.data
}

export async function searchSkills(query: string, workspaceId?: number) {
  const response = await api.post("/api/skills/search", {
    query,
    workspace_id: workspaceId,
    limit: 3
  })
  return response.data
}

export async function getSkillCategories(workspaceId?: number) {
  const params = new URLSearchParams()
  if (workspaceId) params.append('workspace_id', workspaceId.toString())

  const response = await api.get(`/api/skills/categories?${params.toString()}`)
  return response.data
}

export async function generateWorkspaceSkill(workspaceId: number) {
  const response = await api.post(`/api/workspaces/${workspaceId}/generate-skill`, {
    workspace_path: '/workspace'
  })
  return response.data
}

export async function analyzeWorkspace(workspaceId: number) {
  const response = await api.get(`/api/workspaces/${workspaceId}/analyze`)
  return response.data
}