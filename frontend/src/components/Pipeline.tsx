'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic,
  Brain,
  FileCode,
  Upload,
  Timer,
  Search,
  Activity,
  Bell,
  UserCheck,
  CheckCircle2,
  Loader2,
  Circle,
  XCircle,
  ChevronRight,
  Lightbulb,
  ShieldCheck,
  Database,
} from 'lucide-react';
import { cn, calculateStageDuration, formatStageDuration, getDurationColor } from '@/lib/utils';
import { StageDetailModal } from './StageDetailModal';
import { AlertBanner } from './AlertBanner';

interface Stage {
  key: string;
  name: string;
  description: string;
}

interface StageData {
  status: string;
  data?: any;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

interface PipelineProps {
  stages: Stage[];
  currentStage: string;
  stagesData: Record<string, StageData>;
  onAdvance?: () => void;
  isPaused?: boolean;
  operationId?: string;
  onRefresh?: () => void;
}

const stageIcons: Record<string, any> = {
  voice_input: Mic,
  intent_parsing: Brain,
  config_generation: FileCode,
  ai_advice: Lightbulb,
  human_decision: UserCheck,
  baseline_collection: Database,
  cml_deployment: Upload,
  monitoring: Timer,
  splunk_analysis: Search,
  ai_validation: ShieldCheck,
  notifications: Bell,
};

export function Pipeline({ stages, currentStage, stagesData, onAdvance, isPaused, operationId, onRefresh }: PipelineProps) {
  const currentIndex = stages.findIndex((s) => s.key === currentStage);
  const [selectedStage, setSelectedStage] = useState<string | null>(null);

  const handleStageClick = (stageKey: string) => {
    const stageData = stagesData[stageKey];
    // Only allow clicking on stages that have some data
    if (stageData && (stageData.status === 'completed' || stageData.status === 'failed' || stageData.data)) {
      setSelectedStage(stageKey);
    }
  };

  const selectedStageInfo = selectedStage ? stages.find((s) => s.key === selectedStage) : null;
  const selectedStageData = selectedStage ? stagesData[selectedStage] : null;

  // Check if waiting for human approval
  const isAwaitingApproval = currentStage === 'human_decision' && isPaused;

  return (
    <>
      <div className="bg-background-elevated rounded-xl border border-border p-6">
        {/* Error Alert Banner */}
        {(() => {
          const failedStage = stages.find(s => stagesData[s.key]?.status === 'failed');
          if (!failedStage) return null;

          return (
            <div className="mb-4">
              <AlertBanner
                severity="critical"
                title={`PIPELINE FAILED - ${failedStage.name}`}
                message="Click the stage circle for error details"
                onAction={() => handleStageClick(failedStage.key)}
                actionLabel="View Error"
              />
            </div>
          );
        })()}

        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Pipeline Progress</h2>
          <div className="flex items-center gap-3">
            {isAwaitingApproval && (
              <div className="flex items-center gap-2 px-3 py-1.5 bg-warning/20 text-warning rounded-lg text-sm animate-pulse">
                <UserCheck className="w-4 h-4" />
                Awaiting Approval
              </div>
            )}
            {isPaused && onAdvance && !isAwaitingApproval && (
              <button
                onClick={onAdvance}
                className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
                Advance to Next Stage
              </button>
            )}
          </div>
        </div>

        <div className="relative">
          {/* Progress bar background */}
          <div className="absolute top-5 left-0 right-0 h-1 bg-border rounded-full" />

          {/* Progress bar filled */}
          <motion.div
            className="absolute top-5 left-0 h-1 bg-primary rounded-full"
            initial={{ width: 0 }}
            animate={{
              width: `${Math.max(0, ((currentIndex + 1) / stages.length) * 100)}%`,
            }}
            transition={{ duration: 0.5 }}
          />

          {/* Stages */}
          <div className="relative flex justify-between">
            {stages.map((stage, index) => {
              const Icon = stageIcons[stage.key] || Circle;
              const stageData = stagesData[stage.key];
              const status = stageData?.status || 'pending';
              const isActive = stage.key === currentStage;
              const isPast = index < currentIndex;
              const isClickable = stageData && (status === 'completed' || status === 'failed' || stageData.data);
              const duration = calculateStageDuration(stageData || {});

              return (
                <div
                  key={stage.key}
                  className="flex flex-col items-center"
                  style={{ width: `${100 / stages.length}%` }}
                >
                  {/* Stage Circle */}
                  <motion.div
                    className={cn(
                      'relative rounded-full flex items-center justify-center z-10 transition-all',
                      status === 'failed' && 'w-14 h-14 bg-error glow-critical shake',  // Larger + animated for failed
                      status === 'completed' && 'w-10 h-10 bg-success',
                      status === 'running' && 'w-10 h-10 bg-primary',
                      status === 'pending' && 'w-10 h-10 bg-background-elevated border-2 border-border',
                      isClickable && 'cursor-pointer hover:ring-2 hover:ring-primary hover:ring-offset-2 hover:ring-offset-background-elevated'
                    )}
                    initial={{ scale: 1 }}
                    animate={status === 'failed' ? { scale: [1, 1.1, 1] } : isActive ? { scale: [1, 1.1, 1] } : { scale: 1 }}
                    transition={{ repeat: status === 'failed' || isActive ? Infinity : 0, duration: 1.5 }}
                    onClick={() => handleStageClick(stage.key)}
                    whileHover={isClickable ? { scale: 1.1 } : {}}
                    whileTap={isClickable ? { scale: 0.95 } : {}}
                  >
                    {status === 'completed' && (
                      <CheckCircle2 className="w-5 h-5 text-white" />
                    )}
                    {status === 'running' && (
                      <Loader2 className="w-5 h-5 text-white animate-spin" />
                    )}
                    {status === 'failed' && (
                      <XCircle className="w-5 h-5 text-white" />
                    )}
                    {status === 'pending' && (
                      <Icon className="w-5 h-5 text-text-muted" />
                    )}

                    {/* Pulse effect for active stage */}
                    {isActive && status === 'running' && (
                      <div className="absolute inset-0 rounded-full bg-primary animate-ping opacity-25" />
                    )}

                    {/* Special indicator for human decision awaiting */}
                    {stage.key === 'human_decision' && isAwaitingApproval && (
                      <div className="absolute -top-1 -right-1 w-3 h-3 bg-warning rounded-full animate-pulse" />
                    )}
                  </motion.div>

                  {/* Stage Label */}
                  <span
                    className={cn(
                      'mt-2 text-xs text-center font-medium',
                      isActive ? 'text-primary' : isPast ? 'text-text-primary' : 'text-text-muted'
                    )}
                  >
                    {stage.name}
                  </span>

                  {/* Duration Badge */}
                  {status === 'completed' && duration !== null && (
                    <motion.span
                      initial={{ opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={cn(
                        'mt-1 text-[10px] font-mono px-1.5 py-0.5 rounded',
                        getDurationColor(duration),
                        'bg-background'
                      )}
                    >
                      {formatStageDuration(duration)}
                    </motion.span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Current Stage Details */}
        {currentStage && (
          <motion.div
            key={currentStage}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 p-4 bg-background rounded-lg border border-border"
          >
            <div className="flex items-center gap-3">
              {(() => {
                const Icon = stageIcons[currentStage] || Circle;
                return <Icon className="w-5 h-5 text-primary" />;
              })()}
              <div>
                <h3 className="font-medium">
                  {stages.find((s) => s.key === currentStage)?.name}
                </h3>
                <p className="text-sm text-text-secondary">
                  {stages.find((s) => s.key === currentStage)?.description}
                </p>
              </div>
            </div>

            {stagesData[currentStage]?.error && (
              <div className="mt-3 p-3 bg-error/10 border border-error/20 rounded-lg">
                <p className="text-sm text-error">{stagesData[currentStage].error}</p>
              </div>
            )}

            {/* Tip for clickable stages */}
            <p className="mt-3 text-xs text-text-muted">
              Click on completed stages to view details
            </p>
          </motion.div>
        )}
      </div>

      {/* Stage Detail Modal */}
      <AnimatePresence>
        {selectedStage && selectedStageInfo && selectedStageData && (
          <StageDetailModal
            stage={selectedStageInfo}
            stageData={selectedStageData}
            onClose={() => setSelectedStage(null)}
            operationId={operationId}
            rollbackCommands={stagesData.config_generation?.data?.rollback_commands || []}
            rollbackStatus={stagesData.rollback}
            onRollbackComplete={() => {
              onRefresh?.();
              setSelectedStage(null);
            }}
          />
        )}
      </AnimatePresence>
    </>
  );
}
