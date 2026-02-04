'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Mic,
  Activity,
  Network,
  FileText,
  Bell,
  Settings,
  Play,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ChevronRight
} from 'lucide-react';
import Link from 'next/link';
import { useOperationsStore } from '@/store/operations';
import { useWebSocketStore } from '@/store/websocket';

export default function HomePage() {
  const { currentOperation, recentOperations } = useOperationsStore();
  const { connected } = useWebSocketStore();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-background-elevated/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
              <Network className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-text-primary">BRKOPS-2585</h1>
              <p className="text-sm text-text-secondary">AI-Driven Network Operations</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
              connected ? 'bg-success/20 text-success' : 'bg-error/20 text-error'
            }`}>
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-success animate-pulse' : 'bg-error'}`} />
              {connected ? 'Connected' : 'Disconnected'}
            </div>

            <Link
              href="/admin"
              className="p-2 rounded-lg hover:bg-background-elevated transition-colors"
            >
              <Settings className="w-5 h-5 text-text-secondary" />
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h2 className="text-4xl font-bold mb-4">
            <span className="text-text-primary">From </span>
            <span className="text-error">Chaos</span>
            <span className="text-text-primary"> to </span>
            <span className="text-success">Control</span>
          </h2>
          <p className="text-text-secondary text-lg max-w-2xl mx-auto">
            Voice-driven network configuration with automated testing,
            AI-powered analysis, and human-in-the-loop approval.
          </p>
        </motion.div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <Link href="/demo">
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="p-6 rounded-xl bg-background-elevated border border-border hover:border-primary transition-all cursor-pointer group"
            >
              <div className="w-12 h-12 rounded-lg bg-primary/20 flex items-center justify-center mb-4 group-hover:bg-primary/30 transition-colors">
                <Play className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Start Demo</h3>
              <p className="text-text-secondary text-sm">
                Launch the voice-driven network operations demo
              </p>
              <div className="flex items-center gap-1 mt-4 text-primary text-sm">
                Launch Demo <ChevronRight className="w-4 h-4" />
              </div>
            </motion.div>
          </Link>

          <Link href="/demo?tab=topology">
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="p-6 rounded-xl bg-background-elevated border border-border hover:border-primary transition-all cursor-pointer group"
            >
              <div className="w-12 h-12 rounded-lg bg-success/20 flex items-center justify-center mb-4 group-hover:bg-success/30 transition-colors">
                <Network className="w-6 h-6 text-success" />
              </div>
              <h3 className="text-lg font-semibold mb-2">View Topology</h3>
              <p className="text-text-secondary text-sm">
                Interactive network topology from CML
              </p>
              <div className="flex items-center gap-1 mt-4 text-success text-sm">
                View Network <ChevronRight className="w-4 h-4" />
              </div>
            </motion.div>
          </Link>

          <Link href="/admin">
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="p-6 rounded-xl bg-background-elevated border border-border hover:border-primary transition-all cursor-pointer group"
            >
              <div className="w-12 h-12 rounded-lg bg-warning/20 flex items-center justify-center mb-4 group-hover:bg-warning/30 transition-colors">
                <Settings className="w-6 h-6 text-warning" />
              </div>
              <h3 className="text-lg font-semibold mb-2">Admin Panel</h3>
              <p className="text-text-secondary text-sm">
                Configure MCP servers, use cases, and settings
              </p>
              <div className="flex items-center gap-1 mt-4 text-warning text-sm">
                Open Settings <ChevronRight className="w-4 h-4" />
              </div>
            </motion.div>
          </Link>
        </div>

        {/* Pipeline Overview */}
        <div className="mb-12">
          <h3 className="text-xl font-semibold mb-6">Pipeline Stages</h3>
          <div className="grid grid-cols-9 gap-2">
            {[
              { name: 'Voice Input', icon: Mic },
              { name: 'Intent Parse', icon: FileText },
              { name: 'Config Gen', icon: FileText },
              { name: 'CML Deploy', icon: Network },
              { name: 'Monitor', icon: Activity },
              { name: 'Splunk Query', icon: FileText },
              { name: 'AI Analysis', icon: Activity },
              { name: 'Notify', icon: Bell },
              { name: 'Approve', icon: CheckCircle2 },
            ].map((stage, index) => (
              <div key={stage.name} className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-background-elevated border border-border flex items-center justify-center mb-2">
                  <stage.icon className="w-5 h-5 text-text-secondary" />
                </div>
                <span className="text-xs text-text-secondary text-center">{stage.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Operations */}
        <div>
          <h3 className="text-xl font-semibold mb-6">Recent Operations</h3>
          {recentOperations.length === 0 ? (
            <div className="text-center py-12 bg-background-elevated rounded-xl border border-border">
              <Activity className="w-12 h-12 text-text-muted mx-auto mb-4" />
              <p className="text-text-secondary">No recent operations</p>
              <p className="text-text-muted text-sm mt-1">Start a demo to see operations here</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentOperations.map((op) => (
                <div
                  key={op.id}
                  className="p-4 bg-background-elevated rounded-lg border border-border flex items-center justify-between"
                >
                  <div className="flex items-center gap-4">
                    {op.status === 'completed' && <CheckCircle2 className="w-5 h-5 text-success" />}
                    {op.status === 'running' && <Activity className="w-5 h-5 text-primary animate-pulse" />}
                    {op.status === 'failed' && <XCircle className="w-5 h-5 text-error" />}
                    {op.status === 'pending' && <AlertTriangle className="w-5 h-5 text-warning" />}
                    <div>
                      <p className="font-medium">{op.use_case_name}</p>
                      <p className="text-sm text-text-secondary truncate max-w-md">{op.input_text}</p>
                    </div>
                  </div>
                  <div className="text-sm text-text-muted">
                    {op.current_stage}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-border mt-12 py-6">
        <div className="max-w-7xl mx-auto px-4 text-center text-text-muted text-sm">
          BRKOPS-2585 | Cisco Live Demo Platform | Powered by CML & Splunk MCP Servers
        </div>
      </footer>
    </div>
  );
}
