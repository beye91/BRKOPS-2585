'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import {
  Mic,
  MicOff,
  Play,
  Pause,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Network,
  FileText,
  Terminal,
  Activity,
  ArrowLeft,
  Eye,
  History,
} from 'lucide-react';
import Link from 'next/link';
import { useOperationsStore, Operation } from '@/store/operations';
import { useWebSocketStore } from '@/store/websocket';
import { operationsApi, mcpApi, adminApi } from '@/services/api';
import { Pipeline } from '@/components/Pipeline';
import { VoiceInput } from '@/components/VoiceInput';
import { Topology } from '@/components/Topology';
import { LogStream } from '@/components/LogStream';
import { AnalysisReport } from '@/components/AnalysisReport';
import { ApprovalPanel } from '@/components/ApprovalPanel';
import { OperationHistoryPanel } from '@/components/OperationHistoryPanel';
import { OperationDetailModal } from '@/components/OperationDetailModal';
import { cn, PIPELINE_STAGES } from '@/lib/utils';
import { useConfigValue } from '@/lib/configProvider';

interface ProtocolMismatch {
  message: string;
  suggested_use_case: string;
  suggested_display_name: string;
  current_display_name: string;
  confidence: number;
  matched_keywords?: string[];
}

export default function DemoPage() {
  const [activeTab, setActiveTab] = useState<'voice' | 'topology' | 'logs' | 'analysis'>('voice');
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [selectedUseCase, setSelectedUseCase] = useState<string>('ospf_configuration_change');
  const [selectedLab, setSelectedLab] = useState<string | null>(null);
  const [viewingHistoryOp, setViewingHistoryOp] = useState<Operation | null>(null);
  const [showDetailModal, setShowDetailModal] = useState(false);
  const [protocolMismatch, setProtocolMismatch] = useState<ProtocolMismatch | null>(null);

  const { currentOperation, setCurrentOperation, updateStage, setLoading, setError, isLoading } = useOperationsStore();
  const { messages, connected, subscribe } = useWebSocketStore();

  // Dynamic config: polling interval (default 3000ms)
  const pollingInterval = useConfigValue('ui.polling_interval_ms', 3000);

  // Determine which operation to display (live or history)
  const displayOperation = viewingHistoryOp || currentOperation;

  // Fetch use cases
  const { data: useCases } = useQuery({
    queryKey: ['useCases'],
    queryFn: () => adminApi.listUseCases().then((res) => res.data),
  });

  // Fetch CML labs
  const { data: labs } = useQuery({
    queryKey: ['cml-labs'],
    queryFn: () => mcpApi.getCMLLabs().then((res) => res.data.labs || []),
  });

  // Fetch most recent active operation on page load
  useEffect(() => {
    const fetchActiveOperation = async () => {
      try {
        const response = await operationsApi.list();
        const operations = response.data;
        // Find the most recent running/paused/queued operation
        const activeOp = operations.find(
          (op: any) => ['running', 'paused', 'queued'].includes(op.status)
        );
        if (activeOp) {
          // Fetch full details
          const fullOp = await operationsApi.get(activeOp.id);
          setCurrentOperation(fullOp.data);
          // Set transcript from the operation
          if (fullOp.data.input_text) {
            setTranscript(fullOp.data.input_text);
          }
        }
      } catch (error) {
        console.error('Failed to fetch active operation:', error);
      }
    };
    fetchActiveOperation();
  }, [setCurrentOperation]);

  // Track processed WebSocket message index
  const lastProcessedIndex = useRef(0);

  // Process WebSocket messages - handle ALL new messages since last processed
  useEffect(() => {
    if (messages.length === 0) return;
    if (lastProcessedIndex.current >= messages.length) return;

    const newMessages = messages.slice(lastProcessedIndex.current);
    lastProcessedIndex.current = messages.length;

    for (const msg of newMessages) {
      if (msg.job_id && currentOperation?.id === msg.job_id) {
        switch (msg.type) {
          case 'operation.stage_changed':
            updateStage(msg.stage!, {
              status: msg.status!,
              data: msg.data,
            });
            break;
          case 'operation.completed':
          case 'operation.error':
            operationsApi.get(msg.job_id).then((res) => {
              setCurrentOperation(res.data);
            });
            break;
        }
      }
    }
  }, [messages, currentOperation?.id, updateStage, setCurrentOperation]);

  // Polling fallback: refresh operation state every 3s while running
  useEffect(() => {
    if (!currentOperation?.id) return;
    if (currentOperation.status !== 'running' && currentOperation.status !== 'paused') return;

    const interval = setInterval(async () => {
      try {
        const res = await operationsApi.get(currentOperation.id);
        setCurrentOperation(res.data);
      } catch (err) {
        console.error('Poll refresh failed:', err);
      }
    }, pollingInterval);

    return () => clearInterval(interval);
  }, [currentOperation?.id, currentOperation?.status, setCurrentOperation, pollingInterval]);

  const handleStartOperation = async (forceMode = false) => {
    if (!transcript.trim()) return;

    setLoading(true);
    setError(null);
    setProtocolMismatch(null);

    try {
      const response = await operationsApi.start({
        text: transcript,
        use_case: selectedUseCase,
        lab_id: selectedLab,
        force: forceMode,
      });

      setCurrentOperation(response.data);
      // Subscribe to WebSocket updates for this operation
      if (response.data?.id) {
        subscribe(response.data.id);
      }
    } catch (error: any) {
      // Handle protocol mismatch error
      if (error.response?.status === 400 && error.response?.data?.detail?.error === 'PROTOCOL_MISMATCH') {
        const data = error.response.data.detail;
        setProtocolMismatch({
          message: data.message,
          suggested_use_case: data.suggested_use_case,
          suggested_display_name: data.suggested_display_name,
          current_display_name: data.current_display_name,
          confidence: data.confidence,
          matched_keywords: data.matched_keywords,
        });
      } else {
        const detail = error.response?.data?.detail;
        const errorMessage = typeof detail === 'string' ? detail : detail?.message || 'Failed to start operation';
        setError(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSwitchUseCase = (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    if (!protocolMismatch) return;
    setSelectedUseCase(protocolMismatch.suggested_use_case);
    setProtocolMismatch(null);
    // Retry with suggested use case
    setTimeout(() => handleStartOperation(false), 100);
  };

  const handleForceUseCase = (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    setProtocolMismatch(null);
    // Force continue with current use case
    handleStartOperation(true);
  };

  const handleCancelMismatch = (e?: React.MouseEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    setProtocolMismatch(null);
  };

  const handleAdvance = async () => {
    if (!currentOperation) return;

    try {
      await operationsApi.advance(currentOperation.id);
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to advance operation');
    }
  };

  const handleApprove = async (approved: boolean, comment?: string) => {
    if (!currentOperation) return;

    try {
      await operationsApi.approve(currentOperation.id, { approved, comment });
      // Refresh operation
      const response = await operationsApi.get(currentOperation.id);
      setCurrentOperation(response.data);
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to submit approval');
    }
  };

  const handleRefreshOperation = async () => {
    const opToRefresh = viewingHistoryOp || currentOperation;
    if (!opToRefresh) return;

    try {
      const response = await operationsApi.get(opToRefresh.id);
      if (viewingHistoryOp) {
        setViewingHistoryOp(response.data);
      } else {
        setCurrentOperation(response.data);
      }
    } catch (error: any) {
      console.error('Failed to refresh operation:', error);
    }
  };

  const tabs = [
    { id: 'voice', label: 'Voice Input', icon: Mic },
    { id: 'topology', label: 'Topology', icon: Network },
    { id: 'logs', label: 'Logs', icon: Terminal },
    { id: 'analysis', label: 'Analysis', icon: FileText },
  ];

  const isAwaitingApproval = currentOperation?.current_stage === 'human_decision' &&
    currentOperation?.status === 'paused';

  // Get AI advice for display in approval panel
  const aiAdvice = currentOperation?.stages?.ai_advice?.data;

  // Handler for selecting an operation from history
  const handleSelectHistoryOperation = (operation: Operation) => {
    setViewingHistoryOp(operation);
    // Set transcript from the historical operation
    if (operation.input_text) {
      setTranscript(operation.input_text);
    }
  };

  // Handler to return to live operation
  const handleBackToLive = () => {
    setViewingHistoryOp(null);
    // Restore transcript from current operation if exists
    if (currentOperation?.input_text) {
      setTranscript(currentOperation.input_text);
    }
  };

  // Check if viewing history
  const isViewingHistory = viewingHistoryOp !== null;

  return (
    <div className="min-h-screen relative">
      {/* Background Image */}
      <div
        className="fixed inset-0 z-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: 'url(/bg.jpg)' }}
      />
      <div className="fixed inset-0 z-0 bg-[#0A0E14]/80" />

      {/* Content container - positioned above background */}
      <div className="relative z-10">
        {/* Header */}
        <header className="border-b border-border bg-background-elevated/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="p-2 rounded-lg hover:bg-background-elevated transition-colors">
              <ArrowLeft className="w-5 h-5 text-text-secondary" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-text-primary">Demo Dashboard</h1>
              <p className="text-sm text-text-secondary">AI-Driven Network Operations</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Use Case Selector */}
            <select
              value={selectedUseCase}
              onChange={(e) => setSelectedUseCase(e.target.value)}
              className="px-3 py-2 bg-background-elevated border border-border rounded-lg text-sm focus:outline-none focus:border-primary"
            >
              {useCases?.map((uc: any) => (
                <option key={uc.id} value={uc.name}>
                  {uc.display_name}
                </option>
              ))}
            </select>

            {/* Lab Selector */}
            <select
              value={selectedLab || ''}
              onChange={(e) => setSelectedLab(e.target.value || null)}
              className="px-3 py-2 bg-background-elevated border border-border rounded-lg text-sm focus:outline-none focus:border-primary"
            >
              <option value="">Use case default lab</option>
              {labs?.map((lab: any) => (
                <option key={lab.id} value={lab.id}>
                  {lab.lab_title || lab.title || lab.id} ({lab.node_count || 0} devices)
                </option>
              ))}
            </select>

            {/* Connection Status */}
            <div className={cn(
              'flex items-center gap-2 px-3 py-1.5 rounded-full text-sm',
              connected ? 'bg-success/20 text-success' : 'bg-error/20 text-error'
            )}>
              <div className={cn('w-2 h-2 rounded-full', connected ? 'bg-success animate-pulse' : 'bg-error')} />
              {connected ? 'Live' : 'Offline'}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* History Viewing Banner */}
        {isViewingHistory && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 flex items-center justify-between p-3 bg-warning/10 border border-warning/20 rounded-lg"
          >
            <div className="flex items-center gap-2">
              <History className="w-5 h-5 text-warning" />
              <span className="text-sm font-medium text-warning">
                Viewing Historical Operation: {viewingHistoryOp?.use_case_name?.replace(/_/g, ' ')}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowDetailModal(true)}
                className="flex items-center gap-1 px-3 py-1.5 bg-background hover:bg-background-elevated rounded-lg text-sm transition-colors"
              >
                <Eye className="w-4 h-4" />
                View Details
              </button>
              <button
                onClick={handleBackToLive}
                className="flex items-center gap-1 px-3 py-1.5 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Live
              </button>
            </div>
          </motion.div>
        )}

        {/* Pipeline Visualization */}
        <div className="mb-8">
          <Pipeline
            stages={PIPELINE_STAGES}
            currentStage={displayOperation?.current_stage || ''}
            stagesData={displayOperation?.stages || {}}
            onAdvance={isViewingHistory ? undefined : handleAdvance}
            isPaused={displayOperation?.status === 'paused'}
            operationId={displayOperation?.id}
            onRefresh={handleRefreshOperation}
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg transition-colors',
                activeTab === tab.id
                  ? 'bg-primary text-white'
                  : 'bg-background-elevated text-text-secondary hover:text-text-primary'
              )}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2">
            <AnimatePresence mode="wait">
              {activeTab === 'voice' && (
                <motion.div
                  key="voice"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                >
                  {/* Protocol Mismatch Warning */}
                  {protocolMismatch && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="mb-4 p-4 bg-background-elevated border border-amber-500/30 rounded-xl"
                    >
                      <div className="space-y-3">
                        <div className="flex items-start gap-3">
                          <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                          <div className="flex-1">
                            <p className="font-semibold text-amber-500">Protocol Mismatch Detected</p>
                            <p className="text-sm text-text-secondary mt-1">{protocolMismatch.message}</p>
                            <p className="text-sm text-text-secondary mt-1">
                              Suggested: <strong className="text-text-primary">{protocolMismatch.suggested_display_name}</strong>
                              {' '}({Math.round(protocolMismatch.confidence)}% confidence)
                            </p>
                            {protocolMismatch.matched_keywords && protocolMismatch.matched_keywords.length > 0 && (
                              <p className="text-xs text-text-muted mt-1">
                                Matched keywords: {protocolMismatch.matched_keywords.join(', ')}
                              </p>
                            )}
                          </div>
                        </div>
                        <div className="flex gap-2 pt-2">
                          <button
                            type="button"
                            onClick={handleSwitchUseCase}
                            className="px-4 py-2 bg-primary hover:bg-primary-hover text-white rounded-lg text-sm font-medium transition-colors"
                          >
                            Switch to {protocolMismatch.suggested_display_name}
                          </button>
                          <button
                            type="button"
                            onClick={handleForceUseCase}
                            className="px-4 py-2 bg-background hover:bg-border text-text-secondary rounded-lg text-sm font-medium transition-colors"
                          >
                            Continue with {protocolMismatch.current_display_name}
                          </button>
                          <button
                            type="button"
                            onClick={handleCancelMismatch}
                            className="px-4 py-2 bg-transparent hover:bg-background-elevated text-text-secondary rounded-lg text-sm font-medium transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    </motion.div>
                  )}

                  <VoiceInput
                    transcript={transcript}
                    setTranscript={setTranscript}
                    isRecording={isRecording}
                    setIsRecording={setIsRecording}
                    onStart={handleStartOperation}
                    isLoading={isLoading}
                  />
                </motion.div>
              )}

              {activeTab === 'topology' && (
                <motion.div
                  key="topology"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="h-[600px]"
                >
                  <Topology
                    affectedDevices={
                      displayOperation?.stages?.intent_parsing?.data?.target_devices || []
                    }
                    labId={selectedLab}
                  />
                </motion.div>
              )}

              {activeTab === 'logs' && (
                <motion.div
                  key="logs"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                >
                  <LogStream
                    logs={displayOperation?.stages?.splunk_analysis?.data?.results || []}
                    operationStatus={displayOperation?.status}
                    operationStage={displayOperation?.current_stage}
                  />
                </motion.div>
              )}

              {activeTab === 'analysis' && (
                <motion.div
                  key="analysis"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                >
                  <AnalysisReport
                    analysis={displayOperation?.stages?.ai_validation?.data}
                    config={displayOperation?.stages?.config_generation?.data}
                    operationStatus={displayOperation?.status}
                    operationStage={displayOperation?.current_stage}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Side Panel */}
          <div className="space-y-6">
            {/* Current Operation Status */}
            {displayOperation && (
              <div className="p-4 bg-background-elevated rounded-xl border border-border">
                <h3 className="font-semibold mb-3">
                  {isViewingHistory ? 'Historical Operation' : 'Current Operation'}
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Status</span>
                    <span className={cn(
                      'font-medium',
                      displayOperation.status === 'running' && 'text-primary',
                      displayOperation.status === 'completed' && 'text-success',
                      displayOperation.status === 'failed' && 'text-error',
                      displayOperation.status === 'paused' && 'text-warning'
                    )}>
                      {displayOperation.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Stage</span>
                    <span>{displayOperation.current_stage.replace(/_/g, ' ')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Use Case</span>
                    <span>{displayOperation.use_case_name}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Approval Panel - Only show for live operations awaiting approval */}
            {isAwaitingApproval && !isViewingHistory && (
              <ApprovalPanel
                analysis={aiAdvice}
                config={currentOperation?.stages?.config_generation?.data}
                onApprove={handleApprove}
              />
            )}

            {/* AI Advice Preview (when available but not yet at approval) */}
            {displayOperation?.stages?.ai_advice?.data && !(isAwaitingApproval && !isViewingHistory) && (
              <div className="p-4 bg-background-elevated rounded-xl border border-border">
                <h3 className="font-semibold mb-3">AI Advice</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Recommendation</span>
                    <span className={
                      displayOperation.stages.ai_advice.data.recommendation === 'APPROVE' ? 'text-success' :
                      displayOperation.stages.ai_advice.data.recommendation === 'REVIEW' ? 'text-warning' : 'text-error'
                    }>
                      {displayOperation.stages.ai_advice.data.recommendation}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Risk Level</span>
                    <span className={
                      displayOperation.stages.ai_advice.data.risk_level === 'LOW' ? 'text-success' :
                      displayOperation.stages.ai_advice.data.risk_level === 'MEDIUM' ? 'text-warning' : 'text-error'
                    }>
                      {displayOperation.stages.ai_advice.data.risk_level}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Intent Preview */}
            {displayOperation?.stages?.intent_parsing?.data && (
              <div className="p-4 bg-background-elevated rounded-xl border border-border">
                <h3 className="font-semibold mb-3">Parsed Intent</h3>
                <pre className="text-xs overflow-x-auto bg-background p-3 rounded-lg">
                  {JSON.stringify(displayOperation.stages.intent_parsing.data, null, 2)}
                </pre>
              </div>
            )}

            {/* Config Preview */}
            {displayOperation?.stages?.config_generation?.data?.commands && (
              <div className="p-4 bg-background-elevated rounded-xl border border-border">
                <h3 className="font-semibold mb-3">Generated Config</h3>
                <pre className="text-xs font-mono overflow-x-auto bg-background p-3 rounded-lg text-primary">
                  {displayOperation.stages.config_generation.data.commands.join('\n')}
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* Operations History Panel */}
        <div className="mt-8">
          <OperationHistoryPanel
            onSelectOperation={handleSelectHistoryOperation}
            currentOperationId={viewingHistoryOp?.id || currentOperation?.id}
            limit={10}
          />
        </div>
      </main>

      {/* Operation Detail Modal */}
      <AnimatePresence>
        {showDetailModal && viewingHistoryOp && (
          <OperationDetailModal
            operation={viewingHistoryOp}
            onClose={() => setShowDetailModal(false)}
          />
        )}
      </AnimatePresence>
      </div>
    </div>
  );
}
