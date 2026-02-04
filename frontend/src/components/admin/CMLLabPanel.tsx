'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Server,
  Play,
  Square,
  RefreshCw,
  Plus,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Network,
  Upload,
  RotateCcw,
} from 'lucide-react';
import { cmlLabApi } from '@/services/api';
import { cn } from '@/lib/utils';

interface CMLLabNode {
  id: string;
  label: string;
  node_definition: string;
  state: string;
}

interface DemoLabStatus {
  exists: boolean;
  lab_id: string | null;
  title: string;
  state: string;
  node_count: number;
  nodes: CMLLabNode[];
  management_ips: Record<string, string>;
}

interface CMLLabPanelProps {
  showToast: (message: string, type: 'success' | 'error') => void;
}

export default function CMLLabPanel({ showToast }: CMLLabPanelProps) {
  const queryClient = useQueryClient();
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [yamlContent, setYamlContent] = useState('');

  // Query for demo lab status
  const { data: demoLabStatus, isLoading, refetch } = useQuery<DemoLabStatus>({
    queryKey: ['demo-lab-status'],
    queryFn: () => cmlLabApi.getDemoLabStatus().then((res) => res.data),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Build demo lab mutation
  const buildDemoMutation = useMutation({
    mutationFn: () => cmlLabApi.buildDemoLab(),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['demo-lab-status'] });
      showToast('Demo lab created successfully', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to create demo lab', 'error');
    },
  });

  // Start lab mutation
  const startLabMutation = useMutation({
    mutationFn: (labId: string) => cmlLabApi.startLab(labId, false),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-lab-status'] });
      showToast('Lab start initiated', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to start lab', 'error');
    },
  });

  // Stop lab mutation
  const stopLabMutation = useMutation({
    mutationFn: (labId: string) => cmlLabApi.stopLab(labId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-lab-status'] });
      showToast('Lab stopped successfully', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to stop lab', 'error');
    },
  });

  // Delete lab mutation
  const deleteLabMutation = useMutation({
    mutationFn: (labId: string) => cmlLabApi.deleteLab(labId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-lab-status'] });
      showToast('Lab deleted successfully', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to delete lab', 'error');
    },
  });

  // Reset lab mutation
  const resetLabMutation = useMutation({
    mutationFn: (labId: string) => cmlLabApi.resetLab(labId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-lab-status'] });
      showToast('Lab reset to default configuration', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to reset lab', 'error');
    },
  });

  // Create lab from YAML mutation
  const createLabMutation = useMutation({
    mutationFn: (yaml: string) => cmlLabApi.createLab(yaml),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['demo-lab-status'] });
      setShowCreateModal(false);
      setYamlContent('');
      showToast('Lab created successfully', 'success');
    },
    onError: (error: any) => {
      showToast(error.response?.data?.detail || 'Failed to create lab', 'error');
    },
  });

  const getStateColor = (state: string) => {
    switch (state?.toUpperCase()) {
      case 'STARTED':
      case 'BOOTED':
        return 'bg-success';
      case 'STOPPED':
      case 'DEFINED_ON_CORE':
        return 'bg-warning';
      case 'NOT_FOUND':
      case 'ERROR':
        return 'bg-error';
      default:
        return 'bg-text-muted';
    }
  };

  const getStateLabel = (state: string) => {
    switch (state?.toUpperCase()) {
      case 'STARTED':
        return 'Running';
      case 'STOPPED':
        return 'Stopped';
      case 'DEFINED_ON_CORE':
        return 'Defined';
      case 'NOT_FOUND':
        return 'Not Found';
      case 'NO_CML_SERVER':
        return 'No CML Server';
      case 'BOOTED':
        return 'Booting';
      default:
        return state || 'Unknown';
    }
  };

  const isLabRunning = demoLabStatus?.state?.toUpperCase() === 'STARTED';
  const isLabStopped = ['STOPPED', 'DEFINED_ON_CORE'].includes(demoLabStatus?.state?.toUpperCase() || '');
  const isPending = buildDemoMutation.isPending || startLabMutation.isPending || stopLabMutation.isPending || deleteLabMutation.isPending || resetLabMutation.isPending;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="space-y-6"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">CML Lab Management</h2>
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-1.5 bg-background border border-border rounded-lg text-sm hover:border-primary"
        >
          <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Demo Lab Status Card */}
      <div className="bg-background-elevated rounded-xl border border-border p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Network className="w-6 h-6 text-primary" />
            <div>
              <h3 className="font-semibold">BRKOPS-2585 OSPF Demo Lab</h3>
              <p className="text-sm text-text-secondary">
                4 Cat8000v routers in full mesh topology
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div
              className={cn(
                'w-3 h-3 rounded-full',
                getStateColor(demoLabStatus?.state || 'NOT_FOUND')
              )}
            />
            <span className="text-sm font-medium">
              {getStateLabel(demoLabStatus?.state || 'NOT_FOUND')}
            </span>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
        ) : demoLabStatus?.exists ? (
          <>
            {/* Lab Info */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="p-3 bg-background rounded-lg">
                <span className="text-xs text-text-muted block">Lab ID</span>
                <p className="font-mono text-sm truncate">{demoLabStatus.lab_id}</p>
              </div>
              <div className="p-3 bg-background rounded-lg">
                <span className="text-xs text-text-muted block">Nodes</span>
                <p className="text-lg font-semibold">{demoLabStatus.node_count}</p>
              </div>
              <div className="p-3 bg-background rounded-lg">
                <span className="text-xs text-text-muted block">State</span>
                <p className="font-medium">{getStateLabel(demoLabStatus.state)}</p>
              </div>
              <div className="p-3 bg-background rounded-lg">
                <span className="text-xs text-text-muted block">Platform</span>
                <p className="font-medium">Cat8000v</p>
              </div>
            </div>

            {/* Node Status Table */}
            {demoLabStatus.nodes.length > 0 && (
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-text-secondary mb-3">Node Status</h4>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-text-muted border-b border-border">
                        <th className="pb-2">Node</th>
                        <th className="pb-2">Type</th>
                        <th className="pb-2">State</th>
                        <th className="pb-2">Management IP</th>
                      </tr>
                    </thead>
                    <tbody>
                      {demoLabStatus.nodes.map((node) => (
                        <tr key={node.id} className="border-b border-border/50 last:border-0">
                          <td className="py-2 font-medium">{node.label}</td>
                          <td className="py-2 text-text-secondary">{node.node_definition}</td>
                          <td className="py-2">
                            <span className={cn(
                              'inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded',
                              node.state === 'BOOTED' ? 'bg-success/20 text-success' :
                              node.state === 'STARTED' ? 'bg-success/20 text-success' :
                              node.state === 'STOPPED' ? 'bg-warning/20 text-warning' :
                              'bg-text-muted/20 text-text-muted'
                            )}>
                              {node.state === 'BOOTED' || node.state === 'STARTED' ? (
                                <CheckCircle2 className="w-3 h-3" />
                              ) : node.state === 'STOPPED' ? (
                                <XCircle className="w-3 h-3" />
                              ) : (
                                <AlertCircle className="w-3 h-3" />
                              )}
                              {node.state}
                            </span>
                          </td>
                          <td className="py-2 font-mono text-text-secondary">
                            {demoLabStatus.management_ips[node.label] || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-3">
              {isLabStopped && (
                <button
                  onClick={() => demoLabStatus.lab_id && startLabMutation.mutate(demoLabStatus.lab_id)}
                  disabled={isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-success text-white rounded-lg hover:bg-success/90 disabled:opacity-50"
                >
                  {startLabMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4" />
                  )}
                  Start Lab
                </button>
              )}

              {isLabRunning && (
                <button
                  onClick={() => demoLabStatus.lab_id && stopLabMutation.mutate(demoLabStatus.lab_id)}
                  disabled={isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-warning text-white rounded-lg hover:bg-warning/90 disabled:opacity-50"
                >
                  {stopLabMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Square className="w-4 h-4" />
                  )}
                  Stop Lab
                </button>
              )}

              {isLabRunning && (
                <button
                  onClick={() => {
                    if (confirm('Reset all router configurations to default?')) {
                      demoLabStatus.lab_id && resetLabMutation.mutate(demoLabStatus.lab_id);
                    }
                  }}
                  disabled={isPending}
                  className="flex items-center gap-2 px-4 py-2 border border-yellow-500 text-yellow-500 rounded-lg hover:bg-yellow-500/10 disabled:opacity-50"
                >
                  {resetLabMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <RotateCcw className="w-4 h-4" />
                  )}
                  Reset Lab
                </button>
              )}

              <button
                onClick={() => {
                  if (confirm('Are you sure you want to delete this lab? This action cannot be undone.')) {
                    demoLabStatus.lab_id && deleteLabMutation.mutate(demoLabStatus.lab_id);
                  }
                }}
                disabled={isPending}
                className="flex items-center gap-2 px-4 py-2 bg-error text-white rounded-lg hover:bg-error/90 disabled:opacity-50"
              >
                {deleteLabMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Trash2 className="w-4 h-4" />
                )}
                Delete Lab
              </button>
            </div>
          </>
        ) : (
          /* Lab Not Found */
          <div className="text-center py-8">
            <Server className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <h4 className="font-semibold mb-2">Demo Lab Not Found</h4>
            <p className="text-sm text-text-secondary mb-6">
              The BRKOPS-2585 OSPF demo lab has not been created yet.
            </p>
            <button
              onClick={() => buildDemoMutation.mutate()}
              disabled={buildDemoMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover disabled:opacity-50 mx-auto"
            >
              {buildDemoMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Plus className="w-4 h-4" />
              )}
              Build Demo Lab
            </button>
          </div>
        )}
      </div>

      {/* Create Lab Section */}
      <div className="bg-background-elevated rounded-xl border border-border p-6">
        <h3 className="font-semibold mb-4">Create New Lab</h3>
        <p className="text-sm text-text-secondary mb-4">
          Upload a CML topology YAML file to create a custom lab, or use the predefined demo topology.
        </p>
        <div className="flex gap-3">
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-background border border-border rounded-lg hover:border-primary"
          >
            <Upload className="w-4 h-4" />
            Upload YAML
          </button>
          <button
            onClick={() => buildDemoMutation.mutate()}
            disabled={buildDemoMutation.isPending || demoLabStatus?.exists}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover disabled:opacity-50"
          >
            {buildDemoMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Network className="w-4 h-4" />
            )}
            Build Demo Lab
          </button>
        </div>
      </div>

      {/* Lab Features Info */}
      <div className="bg-background-elevated rounded-xl border border-border p-6">
        <h3 className="font-semibold mb-4">Demo Lab Features</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div className="p-3 bg-background rounded-lg">
            <span className="font-medium block mb-1">OSPF Routing</span>
            <p className="text-text-secondary">Full mesh Area 0, point-to-point links</p>
          </div>
          <div className="p-3 bg-background rounded-lg">
            <span className="font-medium block mb-1">Model Driven Telemetry</span>
            <p className="text-text-secondary">CPU, memory, interfaces, OSPF data to Splunk</p>
          </div>
          <div className="p-3 bg-background rounded-lg">
            <span className="font-medium block mb-1">Syslog</span>
            <p className="text-text-secondary">Forwarding to 198.18.134.22:514</p>
          </div>
          <div className="p-3 bg-background rounded-lg">
            <span className="font-medium block mb-1">SNMP</span>
            <p className="text-text-secondary">OSPF traps, community: public/private</p>
          </div>
          <div className="p-3 bg-background rounded-lg">
            <span className="font-medium block mb-1">NETCONF/YANG</span>
            <p className="text-text-secondary">Enabled for programmatic management</p>
          </div>
          <div className="p-3 bg-background rounded-lg">
            <span className="font-medium block mb-1">Management IPs</span>
            <p className="text-text-secondary">198.18.1.201-204 via bridge1</p>
          </div>
        </div>
      </div>

      {/* Create Lab Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowCreateModal(false)} />
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="relative bg-background-elevated rounded-xl border border-border p-6 w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto"
          >
            <h3 className="text-lg font-semibold mb-4">Create Lab from YAML</h3>
            <p className="text-sm text-text-secondary mb-4">
              Paste your CML topology YAML content below to create a new lab.
            </p>
            <textarea
              value={yamlContent}
              onChange={(e) => setYamlContent(e.target.value)}
              placeholder="lab:
  title: My Lab
  description: Lab description
nodes:
  - id: n0
    label: router-1
    ..."
              className="w-full h-64 px-4 py-3 bg-background border border-border rounded-lg font-mono text-sm resize-none focus:outline-none focus:border-primary"
            />
            <div className="flex gap-3 mt-4">
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setYamlContent('');
                }}
                className="flex-1 px-4 py-2 border border-border rounded-lg hover:bg-background"
              >
                Cancel
              </button>
              <button
                onClick={() => yamlContent && createLabMutation.mutate(yamlContent)}
                disabled={!yamlContent || createLabMutation.isPending}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover disabled:opacity-50"
              >
                {createLabMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                Create Lab
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </motion.div>
  );
}
