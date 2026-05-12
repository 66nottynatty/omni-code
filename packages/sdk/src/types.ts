export enum TaskStatus {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  BLOCKED = "blocked",
}

export enum TaskType {
  AGENT_RUN = "agent_run",
  REPO_INDEX = "repo_index",
  CODE_SEARCH = "code_search",
  EMBEDDING_UPDATE = "embedding_update",
}

export interface TaskCreate {
  workspace_id: number;
  task_type: string;
  payload?: Record<string, any>;
}

export interface TaskResponse {
  id: number;
  workspace_id: number;
  status: string;
  task_type: string;
  payload?: Record<string, any>;
  result?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface TaskLog {
  id: number;
  task_id: number;
  content: string;
  level: string;
  created_at: string;
}

export interface Skill {
  id: number;
  name: string;
  description: string;
  content: string;
  category: string;
  workspace_id?: number;
  is_global: boolean;
  created_at: string;
}

export interface SkillCreate {
  name: string;
  description: string;
  content: string;
  category: string;
  workspace_id?: number;
  is_global?: boolean;
}
