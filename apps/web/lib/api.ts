import { OmniCodeClient } from "@omnicode/sdk"

const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

function getToken() {
  if (typeof document === "undefined") return undefined
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("next-auth.session-token="))
    ?.split("=")[1]
}

export const client = new OmniCodeClient(baseUrl, getToken())

export async function getTasks(workspaceId?: number, status?: string) {
  return client.tasks.list({ workspace_id: workspaceId, status })
}

export async function getTask(taskId: number) {
  return client.tasks.get(taskId)
}

export async function createTask(workspaceId: number, taskType: string, payload: object) {
  return client.tasks.create({
    workspace_id: workspaceId,
    task_type: taskType,
    payload,
  })
}

export async function resolveBlocker(taskId: number, resolution: string) {
  return client.tasks.resolve(taskId, resolution)
}

export async function getThreadHistory(threadId: number) {
  return client.threads.getHistory(threadId)
}

export async function rollbackAction(actionId: number) {
  return client.rollback(actionId)
}

export async function getModels() {
  return client.models.list()
}

export async function acceptChange(changeId: number) {
  return client.changes.accept(changeId)
}

export async function rejectChange(changeId: number) {
  return client.changes.reject(changeId)
}

export async function checkHealth() {
  return client.health.check()
}

export async function getSkills(workspaceId?: number, category?: string) {
  return client.skills.list({ workspace_id: workspaceId, category })
}

export async function getSkill(skillId: number) {
  return client.skills.get(skillId)
}

export async function createSkill(skill: any) {
  return client.skills.create(skill)
}

export async function updateSkill(skillId: number, skill: any) {
  return client.skills.update(skillId, skill)
}

export async function deleteSkill(skillId: number) {
  return client.skills.delete(skillId)
}

export async function searchSkills(query: string, workspaceId?: number) {
  return client.skills.search(query, workspaceId)
}

export async function getSkillCategories(workspaceId?: number) {
  return client.skills.getCategories(workspaceId)
}

export async function generateWorkspaceSkill(workspaceId: number) {
  return client.workspaces.generateSkill(workspaceId)
}

export async function analyzeWorkspace(workspaceId: number) {
  return client.workspaces.analyze(workspaceId)
}

export async function getRepoTree(owner: string, repo: string, branch?: string) {
  return client.repos.getTree(owner, repo, branch)
}

export async function getRepoFile(owner: string, repo: string, path: string, branch?: string) {
  return client.repos.getFile(owner, repo, path, branch)
}

export async function indexRepo(owner: string, repo: string, branch?: string) {
  return client.repos.index(owner, repo, branch)
}

export async function decomposeTask(goal: string, context?: any) {
  return client.decompose(goal, context)
}

export async function runOrchestrator(prompt: string, workspaceId: number) {
  return client.orchestrator.run(prompt, workspaceId)
}

export async function previewOrchestrator(prompt: string, workspaceId: number) {
  return client.orchestrator.preview(prompt, workspaceId)
}

export async function getGraph(graphId: string) {
  return client.orchestrator.getGraph(graphId)
}

export function streamGraphLogs(graphId: string, onLog: (log: any) => void) {
  return client.orchestrator.streamGraphLogs(graphId, onLog)
}

export default client;

export async function pauseOrchestrator(graphId: string) {
  return fetch(`${baseUrl}/api/orchestrator/${graphId}/pause`, { method: 'POST' })
}

export async function resumeOrchestrator(graphId: string) {
  return fetch(`${baseUrl}/api/orchestrator/${graphId}/resume`, { method: 'POST' })
}

export async function cancelOrchestrator(graphId: string) {
  return fetch(`${baseUrl}/api/orchestrator/${graphId}/cancel`, { method: 'POST' })
}
