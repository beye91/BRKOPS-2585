'use client';

import { useState, useEffect } from 'react';
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
} from 'lucide-react';
import Link from 'next/link';
import { useOperationsStore } from '@/store/operations';
import { useWebSocketStore } from '@/store/websocket';
import { operationsApi, mcpApi, adminApi } from '@/services/api';
import { Pipeline } from '@/components/Pipeline';
import { VoiceInput } from '@/components/VoiceInput';
import { Topology } from '@/components/Topology';
import { LogStream } from '@/components/LogStream';
import { AnalysisReport } from '@/components/AnalysisReport';
import { ApprovalPanel } from '@/components/ApprovalPanel';
import { cn, PIPELINE_STAGES } from '@/lib/utils';

export default function DemoPage() {
  const [activeTab, setActiveTab] = useState<'voice' | 'topology' | 'logs' | 'analysis'>('voice');
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [selectedUseCase, setSelectedUseCase] = useState<string>('ospf_configuration_change');

  const { currentOperation, setCurrentOperation, updateStage, setLoading, setError } = useOperationsStore();
  const { messages, connected } = useWebSocketStore();

  // Fetch use cases
  const { data: useCases } = useQuery({
    queryKey: ['useCases'],
    queryFn: () => adminApi.listUseCases().then((res) => res.data),
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

  // Process WebSocket messages
  useEffect(() => {
    if (messages.length === 0) return;

    const lastMessage = messages[messages.length - 1];

    if (lastMessage.job_id && currentOperation?.id === lastMessage.job_id) {
      switch (lastMessage.type) {
        case 'operation.stage_changed':
          updateStage(lastMessage.stage!, {
            status: lastMessage.status!,
            data: lastMessage.data,
          });
          break;
        case 'operation.completed':
        case 'operation.error':
          // Refresh operation state
          operationsApi.get(lastMessage.job_id).then((res) => {
            setCurrentOperation(res.data);
          });
          break;
      }
    }
  }, [messages, currentOperation?.id, updateStage, setCurrentOperation]);

  const handleStartOperation = async () => {
    if (!transcript.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const response = await operationsApi.start({
        text: transcript,
        use_case: selectedUseCase,
        demo_mode: true,
      });

      setCurrentOperation(response.data);
    } catch (error: any) {
      setError(error.response?.data?.detail || 'Failed to start operation');
    } finally {
      setLoading(false);
    }
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
        {/* Pipeline Visualization */}
        <div className="mb-8">
          <Pipeline
            stages={PIPELINE_STAGES}
            currentStage={currentOperation?.current_stage || ''}
            stagesData={currentOperation?.stages || {}}
            onAdvance={handleAdvance}
            isPaused={currentOperation?.status === 'paused'}
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
                  <VoiceInput
                    transcript={transcript}
                    setTranscript={setTranscript}
                    isRecording={isRecording}
                    setIsRecording={setIsRecording}
                    onStart={handleStartOperation}
                    isLoading={useOperationsStore.getState().isLoading}
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
                      currentOperation?.stages?.intent_parsing?.data?.target_devices || []
                    }
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
                    logs={currentOperation?.stages?.splunk_analysis?.data?.results || []}
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
                    analysis={currentOperation?.stages?.ai_validation?.data}
                    config={currentOperation?.stages?.config_generation?.data}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Side Panel */}
          <div className="space-y-6">
            {/* Current Operation Status */}
            {currentOperation && (
              <div className="p-4 bg-background-elevated rounded-xl border border-border">
                <h3 className="font-semibold mb-3">Current Operation</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Status</span>
                    <span className={cn(
                      'font-medium',
                      currentOperation.status === 'running' && 'text-primary',
                      currentOperation.status === 'completed' && 'text-success',
                      currentOperation.status === 'failed' && 'text-error',
                      currentOperation.status === 'paused' && 'text-warning'
                    )}>
                      {currentOperation.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Stage</span>
                    <span>{currentOperation.current_stage.replace(/_/g, ' ')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Use Case</span>
                    <span>{currentOperation.use_case_name}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Approval Panel - Now includes AI Advice (pre-deployment review) */}
            {isAwaitingApproval && (
              <ApprovalPanel
                analysis={aiAdvice}
                config={currentOperation?.stages?.config_generation?.data}
                onApprove={handleApprove}
              />
            )}

            {/* AI Advice Preview (when available but not yet at approval) */}
            {aiAdvice && !isAwaitingApproval && (
              <div className="p-4 bg-background-elevated rounded-xl border border-border">
                <h3 className="font-semibold mb-3">AI Advice</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Recommendation</span>
                    <span className={
                      aiAdvice.recommendation === 'APPROVE' ? 'text-success' :
                      aiAdvice.recommendation === 'REVIEW' ? 'text-warning' : 'text-error'
                    }>
                      {aiAdvice.recommendation}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-secondary">Risk Level</span>
                    <span className={
                      aiAdvice.risk_level === 'LOW' ? 'text-success' :
                      aiAdvice.risk_level === 'MEDIUM' ? 'text-warning' : 'text-error'
                    }>
                      {aiAdvice.risk_level}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Intent Preview */}
            {currentOperation?.stages?.intent_parsing?.data && (
              <div className="p-4 bg-background-elevated rounded-xl border border-border">
                <h3 className="font-semibold mb-3">Parsed Intent</h3>
                <pre className="text-xs overflow-x-auto bg-background p-3 rounded-lg">
                  {JSON.stringify(currentOperation.stages.intent_parsing.data, null, 2)}
                </pre>
              </div>
            )}

            {/* Config Preview */}
            {currentOperation?.stages?.config_generation?.data?.commands && (
              <div className="p-4 bg-background-elevated rounded-xl border border-border">
                <h3 className="font-semibold mb-3">Generated Config</h3>
                <pre className="text-xs font-mono overflow-x-auto bg-background p-3 rounded-lg text-primary">
                  {currentOperation.stages.config_generation.data.commands.join('\n')}
                </pre>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
