import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Operations API
export const operationsApi = {
  start: (data: { text?: string; audio_url?: string; use_case?: string; demo_mode?: boolean }) =>
    api.post('/operations/start', data),

  get: (id: string) =>
    api.get(`/operations/${id}`),

  list: (params?: { status?: string; limit?: number; offset?: number }) =>
    api.get('/operations', { params }),

  approve: (id: string, data: { approved: boolean; comment?: string }) =>
    api.post(`/operations/${id}/approve`, data),

  cancel: (id: string) =>
    api.delete(`/operations/${id}`),

  advance: (id: string) =>
    api.post(`/operations/${id}/advance`),

  rollback: (id: string, reason?: string) =>
    api.post(`/operations/${id}/rollback`, { confirm: true, reason }),
};

// Voice API
export const voiceApi = {
  transcribe: (file: File, language: string = 'en') => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/voice/transcribe', formData, {
      params: { language },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// MCP API
export const mcpApi = {
  listServers: () =>
    api.get('/mcp/servers'),

  getServer: (id: number) =>
    api.get(`/mcp/servers/${id}`),

  createServer: (data: any) =>
    api.post('/mcp/servers', data),

  updateServer: (id: number, data: any) =>
    api.put(`/mcp/servers/${id}`, data),

  testServer: (id: number) =>
    api.post(`/mcp/servers/${id}/test`),

  listTools: () =>
    api.get('/mcp/tools'),

  executeTool: (data: { server_id: number; tool_name: string; parameters?: any }) =>
    api.post('/mcp/execute', data),

  getCMLLabs: () =>
    api.get('/mcp/cml/labs'),

  getCMLTopology: (labId: string) =>
    api.get(`/mcp/cml/labs/${labId}/topology`),

  runSplunkQuery: (spl: string, earliest?: string, latest?: string) =>
    api.post('/mcp/splunk/query', null, { params: { spl, earliest, latest } }),
};

// CML Lab Management API
export const cmlLabApi = {
  // Check demo lab status
  getDemoLabStatus: () =>
    api.get('/mcp/cml/labs/demo-status'),

  // List all labs
  getLabs: () =>
    api.get('/mcp/cml/labs'),

  // Get specific lab status
  getLabStatus: (labId: string) =>
    api.get(`/mcp/cml/labs/${labId}/status`),

  // Get lab topology for visualization
  getTopology: (labId: string) =>
    api.get(`/mcp/cml/labs/${labId}/topology`),

  // Create lab from YAML
  createLab: (yaml: string, title?: string) =>
    api.post('/mcp/cml/labs/create', { yaml, title }),

  // Build demo lab (uses predefined topology)
  buildDemoLab: () =>
    api.post('/mcp/cml/labs/build-demo'),

  // Start lab
  startLab: (labId: string, waitForConvergence: boolean = true) =>
    api.post(`/mcp/cml/labs/${labId}/start`, null, {
      params: { wait_for_convergence: waitForConvergence },
    }),

  // Stop lab
  stopLab: (labId: string) =>
    api.post(`/mcp/cml/labs/${labId}/stop`),

  // Reset lab configurations to default
  resetLab: (labId: string) =>
    api.post(`/mcp/cml/labs/${labId}/reset`),

  // Delete lab
  deleteLab: (labId: string) =>
    api.delete(`/mcp/cml/labs/${labId}`),
};

// Notifications API
export const notificationsApi = {
  list: (params?: { channel?: string; status?: string; limit?: number }) =>
    api.get('/notifications', { params }),

  sendWebEx: (data: { room_id?: string; text?: string; markdown?: string }) =>
    api.post('/notifications/webex', data),

  createServiceNowTicket: (data: any) =>
    api.post('/notifications/servicenow', data),

  testWebEx: () =>
    api.post('/notifications/test/webex'),

  testServiceNow: () =>
    api.post('/notifications/test/servicenow'),
};

// Admin API
export const adminApi = {
  getConfig: () =>
    api.get('/admin/config'),

  getConfigVariable: (key: string) =>
    api.get(`/admin/config/${key}`),

  updateConfigVariable: (key: string, data: { value?: any; description?: string }) =>
    api.put(`/admin/config/${key}`, data),

  listUseCases: (includeInactive?: boolean) =>
    api.get('/admin/use-cases', { params: { include_inactive: includeInactive } }),

  getUseCase: (id: number) =>
    api.get(`/admin/use-cases/${id}`),

  createUseCase: (data: any) =>
    api.post('/admin/use-cases', data),

  updateUseCase: (id: number, data: any) =>
    api.put(`/admin/use-cases/${id}`, data),

  deleteUseCase: (id: number) =>
    api.delete(`/admin/use-cases/${id}`),

  listUsers: () =>
    api.get('/admin/users'),

  login: (username: string, password: string) =>
    api.post('/admin/login', { username, password }),
};

// Jobs API
export const jobsApi = {
  getStats: () =>
    api.get('/jobs/stats'),

  getQueue: () =>
    api.get('/jobs/queue'),

  getRecent: (limit?: number, status?: string) =>
    api.get('/jobs/recent', { params: { limit, status_filter: status } }),

  retry: (jobId: string) =>
    api.post(`/jobs/${jobId}/retry`),

  clearCompleted: (olderThanHours?: number) =>
    api.delete('/jobs/completed', { params: { older_than_hours: olderThanHours } }),
};

// Health API
export const healthApi = {
  check: () =>
    api.get('/health'),
};
