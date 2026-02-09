'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Settings,
  Server,
  Brain,
  Bell,
  FileText,
  Users,
  ChevronRight,
  ArrowLeft,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Plus,
  Edit2,
  Trash2,
  TestTube,
  Save,
  Loader2,
  X,
  Eye,
  EyeOff,
  AlertCircle,
  Network,
} from 'lucide-react';
import Link from 'next/link';
import { adminApi, mcpApi, notificationsApi } from '@/services/api';
import { cn } from '@/lib/utils';
import CMLLabPanel from '@/components/admin/CMLLabPanel';

type TabId = 'mcp' | 'cml-labs' | 'llm' | 'use-cases' | 'notifications' | 'pipeline' | 'users';

// Toast notification component
function Toast({ message, type, onClose }: { message: string; type: 'success' | 'error'; onClose: () => void }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 50 }}
      className={cn(
        'fixed bottom-4 right-4 px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 z-50',
        type === 'success' ? 'bg-success text-white' : 'bg-error text-white'
      )}
    >
      {type === 'success' ? (
        <CheckCircle2 className="w-5 h-5" />
      ) : (
        <AlertCircle className="w-5 h-5" />
      )}
      {message}
      <button onClick={onClose} className="ml-2">
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  );
}

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<TabId>('mcp');
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const queryClient = useQueryClient();

  const showToast = (message: string, type: 'success' | 'error') => {
    setToast({ message, type });
  };

  const tabs: { id: TabId; label: string; icon: any }[] = [
    { id: 'mcp', label: 'MCP Servers', icon: Server },
    { id: 'cml-labs', label: 'CML Labs', icon: Network },
    { id: 'llm', label: 'LLM Config', icon: Brain },
    { id: 'use-cases', label: 'Use Cases', icon: FileText },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'pipeline', label: 'Pipeline', icon: Settings },
    { id: 'users', label: 'Users', icon: Users },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-background-elevated/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="p-2 rounded-lg hover:bg-background-elevated transition-colors">
              <ArrowLeft className="w-5 h-5 text-text-secondary" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-text-primary">Admin Panel</h1>
              <p className="text-sm text-text-secondary">Configuration Management</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex gap-6">
          {/* Sidebar */}
          <div className="w-64 shrink-0">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-left',
                    activeTab === tab.id
                      ? 'bg-primary text-white'
                      : 'text-text-secondary hover:bg-background-elevated hover:text-text-primary'
                  )}
                >
                  <tab.icon className="w-5 h-5" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1">
            <AnimatePresence mode="wait">
              {activeTab === 'mcp' && <MCPServersTab key="mcp" showToast={showToast} />}
              {activeTab === 'cml-labs' && <CMLLabPanel key="cml-labs" showToast={showToast} />}
              {activeTab === 'llm' && <LLMConfigTab key="llm" showToast={showToast} />}
              {activeTab === 'use-cases' && <UseCasesTab key="use-cases" showToast={showToast} />}
              {activeTab === 'notifications' && <NotificationsTab key="notifications" showToast={showToast} />}
              {activeTab === 'pipeline' && <PipelineTab key="pipeline" showToast={showToast} />}
              {activeTab === 'users' && <UsersTab key="users" showToast={showToast} />}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <Toast
            message={toast.message}
            type={toast.type}
            onClose={() => setToast(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// Modal Component
function Modal({ isOpen, onClose, title, children }: { isOpen: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="relative bg-background-elevated rounded-xl border border-border p-6 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">{title}</h3>
          <button onClick={onClose} className="p-1 hover:bg-background rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        {children}
      </motion.div>
    </div>
  );
}

// MCP Servers Tab
function MCPServersTab({ showToast }: { showToast: (msg: string, type: 'success' | 'error') => void }) {
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingServer, setEditingServer] = useState<any | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    type: 'cml',
    endpoint: '',
    is_active: true,
    auth_config: {
      host: '',
      username: '',
      password: '',
      token: '',
    },
  });

  const { data: servers, isLoading } = useQuery({
    queryKey: ['mcp-servers'],
    queryFn: () => mcpApi.listServers().then((res) => res.data),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => mcpApi.createServer(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
      setShowAddModal(false);
      resetForm();
      showToast('MCP Server created successfully', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to create server', 'error');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => mcpApi.updateServer(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
      setEditingServer(null);
      resetForm();
      showToast('MCP Server updated successfully', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to update server', 'error');
    },
  });

  const [testingServerId, setTestingServerId] = useState<number | null>(null);
  const [deletingServerId, setDeletingServerId] = useState<number | null>(null);

  const testMutation = useMutation({
    mutationFn: (id: number) => {
      setTestingServerId(id);
      return mcpApi.testServer(id);
    },
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
      const data = response.data;
      if (data.success) {
        showToast(`Connection test successful (${data.tools_count} tools found)`, 'success');
      } else {
        showToast(data.message || 'Connection test failed', 'error');
      }
      setTestingServerId(null);
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Connection test failed', 'error');
      setTestingServerId(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => {
      setDeletingServerId(id);
      return mcpApi.deleteServer(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mcp-servers'] });
      showToast('MCP Server deleted successfully', 'success');
      setDeletingServerId(null);
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to delete server', 'error');
      setDeletingServerId(null);
    },
  });

  const resetForm = () => {
    setFormData({
      name: '',
      type: 'cml',
      endpoint: '',
      is_active: true,
      auth_config: {
        host: '',
        username: '',
        password: '',
        token: '',
      },
    });
  };

  const handleEdit = (server: any) => {
    setEditingServer(server);
    setFormData({
      name: server.name,
      type: server.type,
      endpoint: server.endpoint,
      is_active: server.is_active,
      auth_config: server.auth_config || {
        host: '',
        username: '',
        password: '',
        token: '',
      },
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingServer) {
      updateMutation.mutate({ id: editingServer.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const isModalOpen = showAddModal || editingServer !== null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">MCP Servers</h2>
        <button
          onClick={() => {
            resetForm();
            setShowAddModal(true);
          }}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover"
        >
          <Plus className="w-4 h-4" />
          Add Server
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
        </div>
      ) : (
        <div className="space-y-4">
          {servers?.length === 0 && (
            <div className="text-center py-12 text-text-secondary">
              No MCP servers configured. Click "Add Server" to get started.
            </div>
          )}
          {servers?.map((server: any) => (
            <div
              key={server.id}
              className="p-4 bg-background-elevated rounded-xl border border-border"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      'w-3 h-3 rounded-full',
                      server.health_status === 'healthy' ? 'bg-success' : 'bg-error'
                    )}
                  />
                  <h3 className="font-semibold">{server.name}</h3>
                  <span className="text-xs px-2 py-1 bg-primary/20 text-primary rounded">
                    {server.type.toUpperCase()}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => testMutation.mutate(server.id)}
                    disabled={testingServerId === server.id}
                    className="flex items-center gap-2 px-3 py-1.5 bg-background border border-border rounded-lg text-sm hover:border-primary"
                  >
                    {testingServerId === server.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <TestTube className="w-4 h-4" />
                    )}
                    Test
                  </button>
                  <button
                    onClick={() => handleEdit(server)}
                    className="p-2 hover:bg-background rounded-lg"
                  >
                    <Edit2 className="w-4 h-4 text-text-secondary" />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Are you sure you want to delete "${server.name}"?`)) {
                        deleteMutation.mutate(server.id);
                      }
                    }}
                    disabled={deletingServerId === server.id}
                    className="p-2 hover:bg-background rounded-lg"
                  >
                    {deletingServerId === server.id ? (
                      <Loader2 className="w-4 h-4 animate-spin text-error" />
                    ) : (
                      <Trash2 className="w-4 h-4 text-error" />
                    )}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-text-muted">Endpoint:</span>
                  <p className="font-mono text-text-secondary">{server.endpoint}</p>
                </div>
                <div>
                  <span className="text-text-muted">Status:</span>
                  <p className={server.is_active ? 'text-success' : 'text-error'}>
                    {server.is_active ? 'Active' : 'Inactive'}
                  </p>
                </div>
                <div>
                  <span className="text-text-muted">Tools:</span>
                  <p>{server.available_tools?.length || 0} available</p>
                </div>
                <div>
                  <span className="text-text-muted">Last Check:</span>
                  <p className="text-text-secondary">
                    {server.last_health_check
                      ? new Date(server.last_health_check).toLocaleString()
                      : 'Never'}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add/Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setShowAddModal(false);
          setEditingServer(null);
          resetForm();
        }}
        title={editingServer ? 'Edit MCP Server' : 'Add MCP Server'}
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Server Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., CML Primary"
              className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Server Type
            </label>
            <select
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
            >
              <option value="cml">CML (Cisco Modeling Labs)</option>
              <option value="splunk">Splunk</option>
              <option value="custom">Custom</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Endpoint URL
            </label>
            <input
              type="url"
              value={formData.endpoint}
              onChange={(e) => setFormData({ ...formData, endpoint: e.target.value })}
              placeholder="http://mcp-server:8080"
              className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
              required
            />
          </div>

          {/* CML Auth Fields */}
          {formData.type === 'cml' && (
            <>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  CML Host
                </label>
                <input
                  type="text"
                  value={formData.auth_config.host}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      auth_config: { ...formData.auth_config, host: e.target.value },
                    })
                  }
                  placeholder="cml.example.com"
                  className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    Username
                  </label>
                  <input
                    type="text"
                    value={formData.auth_config.username}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        auth_config: { ...formData.auth_config, username: e.target.value },
                      })
                    }
                    className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    Password
                  </label>
                  <input
                    type="password"
                    value={formData.auth_config.password}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        auth_config: { ...formData.auth_config, password: e.target.value },
                      })
                    }
                    className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
                  />
                </div>
              </div>
            </>
          )}

          {/* Splunk Auth Fields */}
          {formData.type === 'splunk' && (
            <>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  Splunk Host
                </label>
                <input
                  type="text"
                  value={formData.auth_config.host}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      auth_config: { ...formData.auth_config, host: e.target.value },
                    })
                  }
                  placeholder="splunk.example.com"
                  className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text-secondary mb-2">
                  API Token
                </label>
                <input
                  type="password"
                  value={formData.auth_config.token}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      auth_config: { ...formData.auth_config, token: e.target.value },
                    })
                  }
                  className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
                />
              </div>
            </>
          )}

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="rounded"
            />
            <label htmlFor="is_active" className="text-sm">
              Server is active
            </label>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={() => {
                setShowAddModal(false);
                setEditingServer(null);
                resetForm();
              }}
              className="flex-1 px-4 py-2 border border-border rounded-lg hover:bg-background"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || updateMutation.isPending}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover disabled:opacity-50"
            >
              {(createMutation.isPending || updateMutation.isPending) && (
                <Loader2 className="w-4 h-4 animate-spin" />
              )}
              {editingServer ? 'Update Server' : 'Create Server'}
            </button>
          </div>
        </form>
      </Modal>
    </motion.div>
  );
}

// LLM Config Tab
function LLMConfigTab({ showToast }: { showToast: (msg: string, type: 'success' | 'error') => void }) {
  const queryClient = useQueryClient();
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});
  const [hasChanges, setHasChanges] = useState(false);

  const { data: config, isLoading } = useQuery({
    queryKey: ['config'],
    queryFn: () => adminApi.getConfig().then((res) => res.data),
  });

  const llmConfig = config?.find((c: any) => c.category === 'llm')?.variables || [];

  // Initialize form values from config
  useEffect(() => {
    if (llmConfig.length > 0 && Object.keys(formValues).length === 0) {
      const values: Record<string, string> = {};
      llmConfig.forEach((v: any) => {
        values[v.key] = typeof v.value === 'string' ? v.value : JSON.stringify(v.value);
      });
      setFormValues(values);
    }
  }, [llmConfig]);

  const updateMutation = useMutation({
    mutationFn: async (updates: { key: string; value: any }[]) => {
      await Promise.all(
        updates.map((u) =>
          adminApi.updateConfigVariable(u.key, { value: u.value })
        )
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] });
      setHasChanges(false);
      showToast('LLM configuration saved successfully', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to save configuration', 'error');
    },
  });

  const handleChange = (key: string, value: string) => {
    setFormValues({ ...formValues, [key]: value });
    setHasChanges(true);
  };

  const handleSave = () => {
    const updates = Object.entries(formValues).map(([key, value]) => {
      // Try to parse as JSON for non-string values
      let parsedValue: any = value;
      try {
        parsedValue = JSON.parse(value);
      } catch {
        parsedValue = value;
      }
      return { key, value: parsedValue };
    });
    updateMutation.mutate(updates);
  };

  const toggleShowSecret = (key: string) => {
    setShowSecrets({ ...showSecrets, [key]: !showSecrets[key] });
  };

  // Additional API key fields that need to be added
  const apiKeyFields = [
    { key: 'openai_api_key', label: 'OpenAI API Key', placeholder: 'sk-...' },
    { key: 'anthropic_api_key', label: 'Anthropic API Key', placeholder: 'sk-ant-...' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">LLM Configuration</h2>
        {hasChanges && (
          <span className="text-sm text-warning">Unsaved changes</span>
        )}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
        </div>
      ) : (
        <div className="bg-background-elevated rounded-xl border border-border p-6 space-y-6">
          {/* API Keys Section */}
          <div className="border-b border-border pb-6">
            <h3 className="text-sm font-semibold text-text-secondary mb-4 uppercase tracking-wider">
              API Keys
            </h3>
            <div className="space-y-4">
              {apiKeyFields.map((field) => (
                <div key={field.key}>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    {field.label}
                  </label>
                  <div className="relative">
                    <input
                      type={showSecrets[field.key] ? 'text' : 'password'}
                      value={formValues[field.key] || ''}
                      onChange={(e) => handleChange(field.key, e.target.value)}
                      placeholder={field.placeholder}
                      className="w-full px-4 py-2 pr-10 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
                    />
                    <button
                      type="button"
                      onClick={() => toggleShowSecret(field.key)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary"
                    >
                      {showSecrets[field.key] ? (
                        <EyeOff className="w-4 h-4" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Model Settings */}
          <div>
            <h3 className="text-sm font-semibold text-text-secondary mb-4 uppercase tracking-wider">
              Model Settings
            </h3>
            <div className="space-y-4">
              {llmConfig.map((variable: any) => (
                <div key={variable.key}>
                  <label className="block text-sm font-medium text-text-secondary mb-2">
                    {variable.key.replace('llm.', '').replace(/_/g, ' ').toUpperCase()}
                  </label>
                  <div className="relative">
                    <input
                      type={variable.is_secret && !showSecrets[variable.key] ? 'password' : 'text'}
                      value={formValues[variable.key] ?? ''}
                      onChange={(e) => handleChange(variable.key, e.target.value)}
                      className="w-full px-4 py-2 pr-10 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
                    />
                    {variable.is_secret && (
                      <button
                        type="button"
                        onClick={() => toggleShowSecret(variable.key)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary"
                      >
                        {showSecrets[variable.key] ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    )}
                  </div>
                  {variable.description && (
                    <p className="text-xs text-text-muted mt-1">{variable.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={handleSave}
            disabled={updateMutation.isPending || !hasChanges}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover disabled:opacity-50"
          >
            {updateMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Changes
          </button>
        </div>
      )}
    </motion.div>
  );
}

// Use Cases Tab
function UseCasesTab({ showToast }: { showToast: (msg: string, type: 'success' | 'error') => void }) {
  const queryClient = useQueryClient();
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingUseCase, setEditingUseCase] = useState<any | null>(null);

  const { data: useCases, isLoading } = useQuery({
    queryKey: ['use-cases'],
    queryFn: () => adminApi.listUseCases(true).then((res) => res.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminApi.deleteUseCase(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['use-cases'] });
      showToast('Use case deleted', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to delete use case', 'error');
    },
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Use Cases</h2>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover"
        >
          <Plus className="w-4 h-4" />
          Add Use Case
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
        </div>
      ) : (
        <div className="space-y-4">
          {useCases?.map((uc: any) => (
            <div
              key={uc.id}
              className="p-4 bg-background-elevated rounded-xl border border-border"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <h3 className="font-semibold">{uc.display_name}</h3>
                  {!uc.is_active && (
                    <span className="text-xs px-2 py-0.5 bg-warning/20 text-warning rounded">
                      Inactive
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setEditingUseCase(uc)}
                    className="p-2 hover:bg-background rounded-lg"
                  >
                    <Edit2 className="w-4 h-4 text-text-secondary" />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm('Are you sure you want to delete this use case?')) {
                        deleteMutation.mutate(uc.id);
                      }
                    }}
                    className="p-2 hover:bg-background rounded-lg"
                  >
                    <Trash2 className="w-4 h-4 text-error" />
                  </button>
                </div>
              </div>
              <p className="text-sm text-text-secondary mb-3">{uc.description}</p>
              <div className="flex flex-wrap gap-2 mb-2">
                {uc.trigger_keywords?.map((keyword: string) => (
                  <span
                    key={keyword}
                    className="text-xs px-2 py-1 bg-background rounded"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-2 text-xs text-text-muted">
                <Brain className="w-3 h-3" />
                <span>
                  LLM: {uc.llm_provider
                    ? `${uc.llm_provider.charAt(0).toUpperCase() + uc.llm_provider.slice(1)}${uc.llm_model ? ` (${uc.llm_model})` : ''}`
                    : 'Global Default'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Use Case Modal */}
      <UseCaseModal
        isOpen={showAddModal || editingUseCase !== null}
        onClose={() => {
          setShowAddModal(false);
          setEditingUseCase(null);
        }}
        useCase={editingUseCase}
        showToast={showToast}
      />
    </motion.div>
  );
}

// Use Case Modal Component
function UseCaseModal({
  isOpen,
  onClose,
  useCase,
  showToast,
}: {
  isOpen: boolean;
  onClose: () => void;
  useCase: any | null;
  showToast: (msg: string, type: 'success' | 'error') => void;
}) {
  const queryClient = useQueryClient();
  const LLM_PROVIDERS = [
    { value: '', label: 'Global Default' },
    { value: 'openai', label: 'OpenAI' },
    { value: 'anthropic', label: 'Anthropic' },
  ];

  const LLM_MODELS: Record<string, { value: string; label: string }[]> = {
    '': [{ value: '', label: 'Global Default' }],
    openai: [
      { value: '', label: 'Default (from config)' },
      { value: 'gpt-4-turbo-preview', label: 'GPT-4 Turbo' },
      { value: 'gpt-4o', label: 'GPT-4o' },
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
      { value: 'gpt-4', label: 'GPT-4' },
      { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
    ],
    anthropic: [
      { value: '', label: 'Default (from config)' },
      { value: 'claude-opus-4-6', label: 'Claude Opus 4.6' },
      { value: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet 4.5' },
      { value: 'claude-haiku-4-5-20251001', label: 'Claude Haiku 4.5' },
      { value: 'claude-3-sonnet-20240229', label: 'Claude 3 Sonnet' },
      { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku' },
    ],
  };

  const SPLUNK_QUERY_TYPES = [
    { value: 'general', label: 'General Logs' },
    { value: 'ospf_events', label: 'OSPF Events' },
    { value: 'authentication_events', label: 'Authentication Events' },
    { value: 'config_changes', label: 'Configuration Changes' },
  ];

  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    trigger_keywords: '',
    intent_prompt: '',
    config_prompt: '',
    analysis_prompt: '',
    convergence_wait_seconds: 45,
    llm_provider: '',
    llm_model: '',
    explanation_template: '',
    impact_description: '',
    splunk_query_type: 'general',
    pre_checks: [] as string[],
    post_checks: [] as string[],
    risk_factors: [] as string[],
    mitigation_steps: [] as string[],
    affected_services: [] as string[],
    ospf_config_strategy: 'dual',
    servicenow_enabled: false,
    is_active: true,
  });

  useEffect(() => {
    if (useCase) {
      const rp = useCase.risk_profile || {};
      setFormData({
        name: useCase.name || '',
        display_name: useCase.display_name || '',
        description: useCase.description || '',
        trigger_keywords: useCase.trigger_keywords?.join(', ') || '',
        intent_prompt: useCase.intent_prompt || '',
        config_prompt: useCase.config_prompt || '',
        analysis_prompt: useCase.analysis_prompt || '',
        convergence_wait_seconds: useCase.convergence_wait_seconds || 45,
        llm_provider: useCase.llm_provider || '',
        llm_model: useCase.llm_model || '',
        explanation_template: useCase.explanation_template || '',
        impact_description: useCase.impact_description || '',
        splunk_query_type: useCase.splunk_query_config?.query_type || 'general',
        pre_checks: useCase.pre_checks || [],
        post_checks: useCase.post_checks || [],
        risk_factors: rp.risk_factors || [],
        mitigation_steps: rp.mitigation_steps || [],
        affected_services: rp.affected_services || [],
        ospf_config_strategy: useCase.ospf_config_strategy || 'dual',
        servicenow_enabled: useCase.servicenow_enabled ?? false,
        is_active: useCase.is_active ?? true,
      });
    } else {
      setFormData({
        name: '',
        display_name: '',
        description: '',
        trigger_keywords: '',
        intent_prompt: '',
        config_prompt: '',
        analysis_prompt: '',
        convergence_wait_seconds: 45,
        llm_provider: '',
        llm_model: '',
        explanation_template: '',
        impact_description: '',
        splunk_query_type: 'general',
        pre_checks: [],
        post_checks: [],
        risk_factors: [],
        mitigation_steps: [],
        affected_services: [],
        ospf_config_strategy: 'dual',
        servicenow_enabled: false,
        is_active: true,
      });
    }
  }, [useCase]);

  const createMutation = useMutation({
    mutationFn: (data: any) => adminApi.createUseCase(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['use-cases'] });
      onClose();
      showToast('Use case created successfully', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to create use case', 'error');
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) => adminApi.updateUseCase(useCase.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['use-cases'] });
      onClose();
      showToast('Use case updated successfully', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to update use case', 'error');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const { splunk_query_type, risk_factors, mitigation_steps, affected_services, ...rest } = formData;
    const data = {
      ...rest,
      trigger_keywords: formData.trigger_keywords.split(',').map((k) => k.trim()).filter(Boolean),
      llm_provider: formData.llm_provider || null,
      llm_model: formData.llm_model || null,
      explanation_template: formData.explanation_template || null,
      impact_description: formData.impact_description || null,
      servicenow_enabled: formData.servicenow_enabled,
      splunk_query_config: { query_type: splunk_query_type },
      pre_checks: formData.pre_checks.length > 0 ? formData.pre_checks : null,
      post_checks: formData.post_checks.length > 0 ? formData.post_checks : null,
      risk_profile: (risk_factors.length > 0 || mitigation_steps.length > 0 || affected_services.length > 0)
        ? { risk_factors, mitigation_steps, affected_services }
        : null,
    };
    if (useCase) {
      updateMutation.mutate(data);
    } else {
      createMutation.mutate(data);
    }
  };

  // Helper for list editors (add/remove items)
  const updateList = (field: 'pre_checks' | 'post_checks' | 'risk_factors' | 'mitigation_steps' | 'affected_services', index: number, value: string) => {
    const list = [...formData[field]];
    list[index] = value;
    setFormData({ ...formData, [field]: list });
  };
  const addToList = (field: 'pre_checks' | 'post_checks' | 'risk_factors' | 'mitigation_steps' | 'affected_services') => {
    setFormData({ ...formData, [field]: [...formData[field], ''] });
  };
  const removeFromList = (field: 'pre_checks' | 'post_checks' | 'risk_factors' | 'mitigation_steps' | 'affected_services', index: number) => {
    const list = formData[field].filter((_: string, i: number) => i !== index);
    setFormData({ ...formData, [field]: list });
  };

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={useCase ? 'Edit Use Case' : 'Add Use Case'}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Name (ID)
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="ospf_configuration_change"
              className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Display Name
            </label>
            <input
              type="text"
              value={formData.display_name}
              onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              placeholder="OSPF Configuration Change"
              className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-text-secondary mb-2">
            Description
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            rows={2}
            className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-text-secondary mb-2">
            Trigger Keywords (comma-separated)
          </label>
          <input
            type="text"
            value={formData.trigger_keywords}
            onChange={(e) => setFormData({ ...formData, trigger_keywords: e.target.value })}
            placeholder="ospf, routing, area"
            className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-text-secondary mb-2">
            Intent Prompt
          </label>
          <textarea
            value={formData.intent_prompt}
            onChange={(e) => setFormData({ ...formData, intent_prompt: e.target.value })}
            rows={3}
            className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary font-mono text-sm"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-text-secondary mb-2">
            Config Prompt
          </label>
          <textarea
            value={formData.config_prompt}
            onChange={(e) => setFormData({ ...formData, config_prompt: e.target.value })}
            rows={3}
            className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary font-mono text-sm"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-text-secondary mb-2">
            Analysis Prompt
          </label>
          <textarea
            value={formData.analysis_prompt}
            onChange={(e) => setFormData({ ...formData, analysis_prompt: e.target.value })}
            rows={3}
            className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary font-mono text-sm"
            required
          />
        </div>

        {/* LLM Provider/Model Selection */}
        <div className="border-t border-border pt-4">
          <h4 className="text-sm font-semibold text-text-secondary mb-3 uppercase tracking-wider flex items-center gap-2">
            <Brain className="w-4 h-4" />
            LLM Configuration
          </h4>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                LLM Provider
              </label>
              <select
                value={formData.llm_provider}
                onChange={(e) => setFormData({ ...formData, llm_provider: e.target.value, llm_model: '' })}
                className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
              >
                {LLM_PROVIDERS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
              <p className="text-xs text-text-muted mt-1">
                Leave as "Global Default" to use the system-wide LLM setting
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Model
              </label>
              <select
                value={formData.llm_model}
                onChange={(e) => setFormData({ ...formData, llm_model: e.target.value })}
                className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
                disabled={!formData.llm_provider}
              >
                {(LLM_MODELS[formData.llm_provider] || LLM_MODELS['']).map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
              <p className="text-xs text-text-muted mt-1">
                {formData.llm_provider ? 'Select a specific model or use provider default' : 'Select a provider first'}
              </p>
            </div>
          </div>
        </div>

        {/* Pipeline Configuration */}
        <div className="border-t border-border pt-4">
          <h4 className="text-sm font-semibold text-text-secondary mb-3 uppercase tracking-wider flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Pipeline Configuration
          </h4>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Explanation Template
              </label>
              <input
                type="text"
                value={formData.explanation_template}
                onChange={(e) => setFormData({ ...formData, explanation_template: e.target.value })}
                placeholder="Change OSPF area to {{new_area}} on {{device_count}} device(s)"
                className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-sm"
              />
              <p className="text-xs text-text-muted mt-1">
                Variables: {'{{device_count}}'}, {'{{new_area}}'}, {'{{cve_id}}'}, etc.
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Impact Description
              </label>
              <input
                type="text"
                value={formData.impact_description}
                onChange={(e) => setFormData({ ...formData, impact_description: e.target.value })}
                placeholder="Brief OSPF neighbor flap during area transition"
                className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-sm"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Splunk Query Type
              </label>
              <select
                value={formData.splunk_query_type}
                onChange={(e) => setFormData({ ...formData, splunk_query_type: e.target.value })}
                className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
              >
                {SPLUNK_QUERY_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            {/* Pre-Checks List Editor */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Pre-Deployment Checks
              </label>
              {formData.pre_checks.map((check: string, i: number) => (
                <div key={i} className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={check}
                    onChange={(e) => updateList('pre_checks', i, e.target.value)}
                    className="flex-1 px-3 py-1.5 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-sm"
                    placeholder="e.g., Verify OSPF neighbor state"
                  />
                  <button type="button" onClick={() => removeFromList('pre_checks', i)} className="p-1.5 text-error hover:bg-background rounded">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button type="button" onClick={() => addToList('pre_checks')} className="text-xs text-primary hover:underline flex items-center gap-1">
                <Plus className="w-3 h-3" /> Add check
              </button>
            </div>

            {/* Post-Checks List Editor */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Post-Deployment Checks
              </label>
              {formData.post_checks.map((check: string, i: number) => (
                <div key={i} className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={check}
                    onChange={(e) => updateList('post_checks', i, e.target.value)}
                    className="flex-1 px-3 py-1.5 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-sm"
                    placeholder="e.g., Verify routing table convergence"
                  />
                  <button type="button" onClick={() => removeFromList('post_checks', i)} className="p-1.5 text-error hover:bg-background rounded">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button type="button" onClick={() => addToList('post_checks')} className="text-xs text-primary hover:underline flex items-center gap-1">
                <Plus className="w-3 h-3" /> Add check
              </button>
            </div>

            {/* ServiceNow Integration Toggle */}
            <div className="border-t border-border pt-4 mt-4">
              <div className="flex items-center gap-3 mb-2">
                <input
                  type="checkbox"
                  id="servicenow_enabled"
                  checked={formData.servicenow_enabled}
                  onChange={(e) => setFormData({ ...formData, servicenow_enabled: e.target.checked })}
                  className="rounded"
                />
                <label htmlFor="servicenow_enabled" className="text-sm font-medium">
                  Enable ServiceNow Ticket Creation
                </label>
              </div>
              <p className="text-xs text-text-muted ml-6">
                Automatically create ServiceNow incidents when AI validation detects issues or recommends rollback.
              </p>
            </div>

            {/* Risk Factors */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Risk Factors
              </label>
              {formData.risk_factors.map((factor: string, i: number) => (
                <div key={i} className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={factor}
                    onChange={(e) => updateList('risk_factors', i, e.target.value)}
                    className="flex-1 px-3 py-1.5 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-sm"
                    placeholder="e.g., OSPF neighbor adjacency reset"
                  />
                  <button type="button" onClick={() => removeFromList('risk_factors', i)} className="p-1.5 text-error hover:bg-background rounded">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button type="button" onClick={() => addToList('risk_factors')} className="text-xs text-primary hover:underline flex items-center gap-1">
                <Plus className="w-3 h-3" /> Add factor
              </button>
            </div>

            {/* Mitigation Steps */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Mitigation Steps
              </label>
              {formData.mitigation_steps.map((step: string, i: number) => (
                <div key={i} className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={step}
                    onChange={(e) => updateList('mitigation_steps', i, e.target.value)}
                    className="flex-1 px-3 py-1.5 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-sm"
                    placeholder="e.g., Ensure backup paths exist"
                  />
                  <button type="button" onClick={() => removeFromList('mitigation_steps', i)} className="p-1.5 text-error hover:bg-background rounded">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button type="button" onClick={() => addToList('mitigation_steps')} className="text-xs text-primary hover:underline flex items-center gap-1">
                <Plus className="w-3 h-3" /> Add step
              </button>
            </div>

            {/* Affected Services */}
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Affected Services
              </label>
              {formData.affected_services.map((svc: string, i: number) => (
                <div key={i} className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={svc}
                    onChange={(e) => updateList('affected_services', i, e.target.value)}
                    className="flex-1 px-3 py-1.5 bg-background border border-border rounded-lg focus:outline-none focus:border-primary text-sm"
                    placeholder="e.g., OSPF routing"
                  />
                  <button type="button" onClick={() => removeFromList('affected_services', i)} className="p-1.5 text-error hover:bg-background rounded">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button type="button" onClick={() => addToList('affected_services')} className="text-xs text-primary hover:underline flex items-center gap-1">
                <Plus className="w-3 h-3" /> Add service
              </button>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-2">
              Convergence Wait (seconds)
            </label>
            <input
              type="number"
              value={formData.convergence_wait_seconds}
              onChange={(e) =>
                setFormData({ ...formData, convergence_wait_seconds: parseInt(e.target.value) })
              }
              className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-text-secondary mb-2">
            OSPF Configuration Strategy
          </label>
          <select
            value={formData.ospf_config_strategy || 'dual'}
            onChange={(e) => setFormData({ ...formData, ospf_config_strategy: e.target.value })}
            className="w-full px-4 py-2 bg-background border border-border rounded-lg focus:outline-none focus:border-primary"
          >
            <option value="dual">Dual Mode (Recommended) - Both network statements and interface commands</option>
            <option value="network_only">Network Statements Only (Legacy)</option>
            <option value="interface_only">Interface Commands Only (Modern)</option>
          </select>
          <p className="text-xs text-text-muted mt-1">
            Dual mode provides maximum compatibility and enables smooth migration from network statements to modern interface-level configuration.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <input
            type="checkbox"
            id="uc_is_active"
            checked={formData.is_active}
            onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
            className="rounded"
          />
          <label htmlFor="uc_is_active" className="text-sm">
            Active
          </label>
        </div>

        <div className="flex gap-3 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-border rounded-lg hover:bg-background"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={createMutation.isPending || updateMutation.isPending}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover disabled:opacity-50"
          >
            {(createMutation.isPending || updateMutation.isPending) && (
              <Loader2 className="w-4 h-4 animate-spin" />
            )}
            {useCase ? 'Update' : 'Create'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// Notifications Tab
function NotificationsTab({ showToast }: { showToast: (msg: string, type: 'success' | 'error') => void }) {
  const queryClient = useQueryClient();
  const [formValues, setFormValues] = useState({
    webex_webhook_url: '',
    servicenow_instance: '',
    servicenow_username: '',
    servicenow_password: '',
  });
  const [hasChanges, setHasChanges] = useState(false);

  const { data: config } = useQuery({
    queryKey: ['config'],
    queryFn: () => adminApi.getConfig().then((res) => res.data),
  });

  useEffect(() => {
    if (config) {
      const notificationConfig = config.find((c: any) => c.category === 'notifications')?.variables || [];
      const values: any = { ...formValues };
      notificationConfig.forEach((v: any) => {
        const key = v.key.replace('notifications.', '');
        if (key in values) {
          values[key] = typeof v.value === 'string' ? v.value : JSON.stringify(v.value);
        }
      });
      setFormValues(values);
    }
  }, [config]);

  const testWebExMutation = useMutation({
    mutationFn: () => notificationsApi.testWebEx(),
    onSuccess: () => showToast('WebEx test message sent successfully', 'success'),
    onError: (error: any) => showToast(error.response?.data?.detail || 'WebEx test failed', 'error'),
  });

  const testServiceNowMutation = useMutation({
    mutationFn: () => notificationsApi.testServiceNow(),
    onSuccess: () => showToast('ServiceNow test successful', 'success'),
    onError: (error: any) => showToast(error.response?.data?.detail || 'ServiceNow test failed', 'error'),
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const updates = Object.entries(formValues).map(([key, value]) => ({
        key: `notifications.${key}`,
        value,
      }));
      await Promise.all(
        updates.map((u) => adminApi.updateConfigVariable(u.key, { value: u.value }))
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] });
      setHasChanges(false);
      showToast('Notification settings saved', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to save settings', 'error');
    },
  });

  const handleChange = (key: string, value: string) => {
    setFormValues({ ...formValues, [key]: value });
    setHasChanges(true);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Notifications</h2>
        {hasChanges && <span className="text-sm text-warning">Unsaved changes</span>}
      </div>

      {/* WebEx */}
      <div className="bg-background-elevated rounded-xl border border-border p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">WebEx Configuration</h3>
          <button
            onClick={() => testWebExMutation.mutate()}
            disabled={testWebExMutation.isPending}
            className="flex items-center gap-2 px-3 py-1.5 bg-background border border-border rounded-lg text-sm hover:border-primary"
          >
            {testWebExMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : testWebExMutation.isSuccess ? (
              <CheckCircle2 className="w-4 h-4 text-success" />
            ) : testWebExMutation.isError ? (
              <XCircle className="w-4 h-4 text-error" />
            ) : (
              <TestTube className="w-4 h-4" />
            )}
            Test Connection
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-text-muted mb-2">Webhook URL</label>
            <input
              type="text"
              value={formValues.webex_webhook_url}
              onChange={(e) => handleChange('webex_webhook_url', e.target.value)}
              placeholder="https://webexapis.com/v1/webhooks/incoming/..."
              className="w-full px-4 py-2 bg-background border border-border rounded-lg"
            />
          </div>
        </div>
      </div>

      {/* ServiceNow */}
      <div className="bg-background-elevated rounded-xl border border-border p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold">ServiceNow Configuration</h3>
          <button
            onClick={() => testServiceNowMutation.mutate()}
            disabled={testServiceNowMutation.isPending}
            className="flex items-center gap-2 px-3 py-1.5 bg-background border border-border rounded-lg text-sm hover:border-primary"
          >
            {testServiceNowMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : testServiceNowMutation.isSuccess ? (
              <CheckCircle2 className="w-4 h-4 text-success" />
            ) : testServiceNowMutation.isError ? (
              <XCircle className="w-4 h-4 text-error" />
            ) : (
              <TestTube className="w-4 h-4" />
            )}
            Test Connection
          </button>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-text-muted mb-2">Instance</label>
            <input
              type="text"
              value={formValues.servicenow_instance}
              onChange={(e) => handleChange('servicenow_instance', e.target.value)}
              placeholder="your-instance.service-now.com"
              className="w-full px-4 py-2 bg-background border border-border rounded-lg"
            />
          </div>
          <div>
            <label className="block text-sm text-text-muted mb-2">Username</label>
            <input
              type="text"
              value={formValues.servicenow_username}
              onChange={(e) => handleChange('servicenow_username', e.target.value)}
              className="w-full px-4 py-2 bg-background border border-border rounded-lg"
            />
          </div>
          <div className="col-span-2">
            <label className="block text-sm text-text-muted mb-2">Password</label>
            <input
              type="password"
              value={formValues.servicenow_password}
              onChange={(e) => handleChange('servicenow_password', e.target.value)}
              className="w-full px-4 py-2 bg-background border border-border rounded-lg"
            />
          </div>
        </div>
      </div>

      <button
        onClick={() => saveMutation.mutate()}
        disabled={saveMutation.isPending || !hasChanges}
        className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover disabled:opacity-50"
      >
        {saveMutation.isPending ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Save className="w-4 h-4" />
        )}
        Save Changes
      </button>
    </motion.div>
  );
}

// Pipeline Tab
function PipelineTab({ showToast }: { showToast: (msg: string, type: 'success' | 'error') => void }) {
  const queryClient = useQueryClient();
  const [formValues, setFormValues] = useState({
    convergence_wait_seconds: '45',
    mcp_timeout_seconds: '60',
    max_retries: '3',
    demo_mode: true,
    auto_advance: false,
  });
  const [hasChanges, setHasChanges] = useState(false);

  const { data: config, isLoading } = useQuery({
    queryKey: ['config'],
    queryFn: () => adminApi.getConfig().then((res) => res.data),
  });

  useEffect(() => {
    if (config) {
      const pipelineConfig = config.find((c: any) => c.category === 'pipeline')?.variables || [];
      const values: any = { ...formValues };
      pipelineConfig.forEach((v: any) => {
        const key = v.key.replace('pipeline.', '');
        if (key in values) {
          if (typeof v.value === 'boolean') {
            values[key] = v.value;
          } else {
            values[key] = String(v.value);
          }
        }
      });
      setFormValues(values);
    }
  }, [config]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const updates = Object.entries(formValues).map(([key, value]) => {
        let parsedValue: any = value;
        if (typeof value === 'string' && !isNaN(Number(value))) {
          parsedValue = Number(value);
        }
        return { key: `pipeline.${key}`, value: parsedValue };
      });
      await Promise.all(
        updates.map((u) => adminApi.updateConfigVariable(u.key, { value: u.value }))
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config'] });
      setHasChanges(false);
      showToast('Pipeline settings saved', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to save settings', 'error');
    },
  });

  const handleChange = (key: string, value: any) => {
    setFormValues({ ...formValues, [key]: value });
    setHasChanges(true);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Pipeline Configuration</h2>
        {hasChanges && <span className="text-sm text-warning">Unsaved changes</span>}
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
        </div>
      ) : (
        <div className="bg-background-elevated rounded-xl border border-border p-6 space-y-6">
          <div>
            <label className="block text-sm text-text-muted mb-2">
              Convergence Wait (seconds)
            </label>
            <input
              type="number"
              value={formValues.convergence_wait_seconds}
              onChange={(e) => handleChange('convergence_wait_seconds', e.target.value)}
              className="w-full px-4 py-2 bg-background border border-border rounded-lg"
            />
            <p className="text-xs text-text-muted mt-1">
              How long to wait after config push for network convergence
            </p>
          </div>

          <div>
            <label className="block text-sm text-text-muted mb-2">
              MCP Timeout (seconds)
            </label>
            <input
              type="number"
              value={formValues.mcp_timeout_seconds}
              onChange={(e) => handleChange('mcp_timeout_seconds', e.target.value)}
              className="w-full px-4 py-2 bg-background border border-border rounded-lg"
            />
          </div>

          <div>
            <label className="block text-sm text-text-muted mb-2">
              Max Retry Attempts
            </label>
            <input
              type="number"
              value={formValues.max_retries}
              onChange={(e) => handleChange('max_retries', e.target.value)}
              className="w-full px-4 py-2 bg-background border border-border rounded-lg"
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="demo-mode"
              checked={formValues.demo_mode}
              onChange={(e) => handleChange('demo_mode', e.target.checked)}
              className="rounded"
            />
            <label htmlFor="demo-mode" className="text-sm">
              Enable Demo Mode (step-by-step advancement)
            </label>
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="auto-advance"
              checked={formValues.auto_advance}
              onChange={(e) => handleChange('auto_advance', e.target.checked)}
              className="rounded"
            />
            <label htmlFor="auto-advance" className="text-sm">
              Auto-advance through stages without pausing
            </label>
          </div>

          <button
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending || !hasChanges}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover disabled:opacity-50"
          >
            {saveMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Save className="w-4 h-4" />
            )}
            Save Changes
          </button>
        </div>
      )}
    </motion.div>
  );
}

// Users Tab
function UsersTab({ showToast }: { showToast: (msg: string, type: 'success' | 'error') => void }) {
  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: () => adminApi.listUsers().then((res) => res.data),
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Users</h2>
        <button className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover">
          <Plus className="w-4 h-4" />
          Add User
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
        </div>
      ) : (
        <div className="bg-background-elevated rounded-xl border border-border overflow-hidden">
          <table className="w-full">
            <thead className="border-b border-border">
              <tr className="text-left text-sm text-text-muted">
                <th className="px-4 py-3">Username</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users?.map((user: any) => (
                <tr key={user.id} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 font-medium">{user.username}</td>
                  <td className="px-4 py-3 text-text-secondary">{user.email}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 bg-primary/20 text-primary text-xs rounded">
                      {user.role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={user.is_active ? 'text-success' : 'text-error'}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button className="p-1 hover:bg-background rounded">
                      <Edit2 className="w-4 h-4 text-text-secondary" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </motion.div>
  );
}
