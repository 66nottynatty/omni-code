import axios, { AxiosInstance } from 'axios';
import { createParser } from 'eventsource-parser';
import { TaskCreate, TaskResponse, Skill, SkillCreate } from './types';

export class OmniCodeClient {
  private client: AxiosInstance;

  constructor(private baseUrl: string, private token?: string) {
    this.client = axios.create({
      baseURL: baseUrl,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  }

  setToken(token: string) {
    this.token = token;
    this.client.defaults.headers.Authorization = `Bearer ${token}`;
  }

  tasks = {
    create: async (data: TaskCreate): Promise<{ task_id: number; status: string }> => {
      const response = await this.client.post('/api/tasks', data);
      return response.data;
    },
    get: async (id: number): Promise<TaskResponse> => {
      const response = await this.client.get(`/api/tasks/${id}`);
      return response.data;
    },
    list: async (params?: any): Promise<TaskResponse[]> => {
      const response = await this.client.get('/api/tasks', { params });
      return response.data;
    },
    resolve: async (id: number, resolution: string): Promise<any> => {
      const response = await this.client.post(`/api/tasks/${id}/resolve`, { resolution });
      return response.data;
    },
    streamLogs: (id: number, onLog: (log: any) => void) => {
      const url = `${this.baseUrl}/api/tasks/${id}/logs/sse`;
      const abortController = new AbortController();
      
      (async () => {
        try {
          const response = await fetch(url, {
            headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
            signal: abortController.signal,
          });

          if (!response.body) return;

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          const parser = createParser({
            onEvent: (event) => {
              try {
                const data = JSON.parse(event.data);
                onLog(data);
              } catch (e) {
                onLog(event.data);
              }
            }
          });

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            parser.feed(decoder.decode(value));
          }
        } catch (error) {
          if ((error as Error).name !== 'AbortError') {
            console.error('Streaming error:', error);
          }
        }
      })();

      return () => abortController.abort();
    },
  };

  skills = {
    list: async (params?: any): Promise<Skill[]> => {
      const response = await this.client.get('/api/skills', { params });
      return response.data;
    },
    get: async (id: number): Promise<Skill> => {
      const response = await this.client.get(`/api/skills/${id}`);
      return response.data;
    },
    create: async (data: SkillCreate): Promise<Skill> => {
      const response = await this.client.post('/api/skills', data);
      return response.data;
    },
    update: async (id: number, data: Partial<SkillCreate>): Promise<Skill> => {
      const response = await this.client.put(`/api/skills/${id}`, data);
      return response.data;
    },
    delete: async (id: number): Promise<any> => {
      const response = await this.client.delete(`/api/skills/${id}`);
      return response.data;
    },
    search: async (query: string, workspaceId?: number, limit = 3): Promise<Skill[]> => {
      const response = await this.client.post('/api/skills/search', { query, workspace_id: workspaceId, limit });
      return response.data;
    },
    getCategories: async (workspaceId?: number): Promise<string[]> => {
      const response = await this.client.get('/api/skills/categories', { params: { workspace_id: workspaceId } });
      return response.data;
    },
  };

  threads = {
    getHistory: async (id: number): Promise<any[]> => {
      const response = await this.client.get(`/api/threads/${id}/history`);
      return response.data;
    },
    streamLogs: (id: number, onLog: (log: any) => void) => {
      const url = `${this.baseUrl}/api/threads/${id}/logs/sse`;
      const abortController = new AbortController();
      
      (async () => {
        try {
          const response = await fetch(url, {
            headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
            signal: abortController.signal,
          });

          if (!response.body) return;

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          const parser = createParser({
            onEvent: (event) => {
              try {
                const data = JSON.parse(event.data);
                onLog(data);
              } catch (e) {
                onLog(event.data);
              }
            }
          });

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            parser.feed(decoder.decode(value));
          }
        } catch (error) {
          if ((error as Error).name !== 'AbortError') {
            console.error('Streaming error:', error);
          }
        }
      })();

      return () => abortController.abort();
    },
  };

  changes = {
    accept: async (id: number): Promise<any> => {
      const response = await this.client.post(`/api/pending-changes/${id}/accept`);
      return response.data;
    },
    reject: async (id: number): Promise<any> => {
      const response = await this.client.post(`/api/pending-changes/${id}/reject`);
      return response.data;
    },
  };

  models = {
    list: async (): Promise<any[]> => {
      const response = await this.client.get('/api/models');
      return response.data;
    },
  };

  workspaces = {
    generateSkill: async (id: number): Promise<Skill> => {
      const response = await this.client.post(`/api/workspaces/${id}/generate-skill`, { workspace_path: '/workspace' });
      return response.data;
    },
    analyze: async (id: number): Promise<any> => {
      const response = await this.client.get(`/api/workspaces/${id}/analyze`);
      return response.data;
    },
  };

  health = {
    check: async (): Promise<any> => {
      const response = await this.client.get('/health');
      return response.data;
    },
  };

  orchestrator = {
    run: async (prompt: string, workspaceId: number): Promise<{ graph_id: string; status: string }> => {
      const response = await this.client.post('/api/orchestrator/run', { prompt, workspace_id: workspaceId });
      return response.data;
    },
    preview: async (prompt: string, workspaceId: number): Promise<any> => {
      const response = await this.client.post('/api/orchestrator/preview', { prompt, workspace_id: workspaceId });
      return response.data;
    },
    getGraph: async (graphId: string): Promise<any> => {
      const response = await this.client.get(`/api/orchestrator/${graphId}`);
      return response.data;
    },
    streamGraphLogs: (graphId: string, onLog: (log: any) => void) => {
      const url = `${this.baseUrl}/api/orchestrator/${graphId}/stream`;
      const abortController = new AbortController();
      
      (async () => {
        try {
          const response = await fetch(url, {
            headers: this.token ? { Authorization: `Bearer ${this.token}` } : {},
            signal: abortController.signal,
          });

          if (!response.body) return;

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          const parser = createParser({
            onEvent: (event) => {
              try {
                const data = JSON.parse(event.data);
                onLog(data);
              } catch (e) {
                onLog(event.data);
              }
            }
          });

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            parser.feed(decoder.decode(value));
          }
        } catch (error) {
          if ((error as Error).name !== 'AbortError') {
            console.error('Streaming error:', error);
          }
        }
      })();

      return () => abortController.abort();
    },
  };

  rollback = async (actionId: number): Promise<any> => {
    const response = await this.client.post(`/api/rollback/${actionId}`);
    return response.data;
  };

  repos = {
    getTree: async (owner: string, repo: string, branch: string = "main"): Promise<any[]> => {
      const response = await this.client.get(`/api/repos/${owner}/${repo}/tree`, { params: { branch } });
      return response.data;
    },
    getFile: async (owner: string, repo: string, path: string, branch: string = "main"): Promise<{ content: string; sha: string }> => {
      const response = await this.client.get(`/api/repos/${owner}/${repo}/file`, { params: { path, branch } });
      return response.data;
    },
    index: async (owner: string, repo: string, branch: string = "main"): Promise<any> => {
      const response = await this.client.post(`/api/repos/${owner}/${repo}/index`, null, { params: { branch } });
      return response.data;
    },
  };

  decompose = async (goal: string, context: any = {}): Promise<any> => {
    const response = await this.client.post('/api/decompose', { goal, context });
    return response.data;
  };
}
