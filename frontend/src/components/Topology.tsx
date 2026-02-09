'use client';

import { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useQuery } from '@tanstack/react-query';
import { Loader2, RefreshCw, AlertCircle } from 'lucide-react';
import { mcpApi } from '@/services/api';
import { cn } from '@/lib/utils';

interface TopologyProps {
  affectedDevices?: string[];
  labId?: string | null;
}

// Custom node component
function DeviceNode({ data }: { data: any }) {
  const isAffected = data.isAffected;
  const isRouter = data.type?.includes('router') || data.type?.includes('iosv');
  const isSwitch = data.type?.includes('switch');

  return (
    <div
      className={cn(
        'px-4 py-2 rounded-lg border-2 min-w-[100px] text-center transition-all',
        isAffected
          ? 'bg-primary/20 border-primary shadow-glow-primary animate-pulse'
          : data.state === 'BOOTED'
          ? 'bg-success/20 border-success'
          : 'bg-background-elevated border-border'
      )}
    >
      <div className="text-xs text-text-muted mb-1">
        {isRouter ? '🔀' : isSwitch ? '🔄' : '📦'}
      </div>
      <div className="font-medium text-sm">{data.label}</div>
      <div className="text-xs text-text-muted">{data.type}</div>
      {data.state && (
        <div
          className={cn(
            'text-xs mt-1 px-2 py-0.5 rounded-full inline-block',
            data.state === 'BOOTED' ? 'bg-success/20 text-success' : 'bg-warning/20 text-warning'
          )}
        >
          {data.state}
        </div>
      )}
    </div>
  );
}

const nodeTypes = {
  device: DeviceNode,
};

// Resolve a readable label for a CML lab
function getLabLabel(lab: any): string {
  const title = lab.title || lab.lab_title;
  const nodeCount = lab.node_count ?? lab.nodes?.length;

  let label: string;
  if (title && !/^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(title)) {
    // Title exists and doesn't look like a UUID
    label = title;
  } else if (lab.id && !/^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(lab.id)) {
    label = lab.id;
  } else {
    label = `Lab ${(lab.id || '').substring(0, 8)}`;
  }

  if (nodeCount != null) {
    label += ` (${nodeCount} node${nodeCount !== 1 ? 's' : ''})`;
  }
  return label;
}

export function Topology({ affectedDevices = [], labId }: TopologyProps) {
  const [selectedLab, setSelectedLab] = useState<string | null>(null);

  // Use provided labId prop, otherwise use internal state
  const activeLabId = labId || selectedLab;
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // Fetch labs
  const { data: labsData, isLoading: labsLoading, error: labsError, refetch: refetchLabs } = useQuery({
    queryKey: ['cml-labs'],
    queryFn: () => mcpApi.getCMLLabs().then((res) => res.data.labs || []),
    retry: 1,
  });

  // Fetch topology for selected lab
  const { data: topologyData, isLoading: topologyLoading, refetch: refetchTopology } = useQuery({
    queryKey: ['cml-topology', activeLabId],
    queryFn: () => mcpApi.getCMLTopology(activeLabId!).then((res) => res.data),
    enabled: !!activeLabId,
    retry: 1,
  });

  // Auto-select first lab (only if no labId prop provided)
  useEffect(() => {
    if (!labId && labsData && labsData.length > 0 && !selectedLab) {
      setSelectedLab(labsData[0].id);
    }
  }, [labId, labsData, selectedLab]);

  // Update nodes and edges when topology changes
  useEffect(() => {
    if (!topologyData) return;

    // Create nodes
    const newNodes: Node[] = topologyData.nodes.map((node: any, index: number) => ({
      id: node.id,
      type: 'device',
      position: {
        x: node.x || (index % 4) * 200 + 100,
        y: node.y || Math.floor(index / 4) * 150 + 100,
      },
      data: {
        label: node.label,
        type: node.type,
        state: node.state,
        isAffected: affectedDevices.some(
          (d) => d.toLowerCase() === node.label.toLowerCase()
        ),
      },
    }));

    // Create edges with validation
    const newEdges: Edge[] = topologyData.links
      .filter((link: any) => {
        // Filter invalid links
        if (!link.source || !link.target) {
          console.warn('Skipping link with missing endpoints:', link);
          return false;
        }
        return true;
      })
      .map((link: any) => ({
        id: link.id,
        source: link.source,
        target: link.target,
        label: `${link.interface_a || ''} - ${link.interface_b || ''}`,
        style: { stroke: '#3A4554' },
        labelStyle: { fill: '#8B95A5', fontSize: 10 },
      }));

    // Log edge count for debugging
    console.log(`Topology: ${newNodes.length} nodes, ${newEdges.length} edges`);

    setNodes(newNodes);
    setEdges(newEdges);
  }, [topologyData, affectedDevices, setNodes, setEdges]);

  if (labsLoading) {
    return (
      <div className="h-full bg-background-elevated rounded-xl border border-border flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  if (labsError) {
    return (
      <div className="h-full bg-background-elevated rounded-xl border border-border flex flex-col items-center justify-center gap-4">
        <AlertCircle className="w-12 h-12 text-error" />
        <p className="text-text-secondary">Failed to load CML labs</p>
        <p className="text-sm text-text-muted">Make sure CML MCP server is configured</p>
        <button
          onClick={() => refetchLabs()}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary-hover"
        >
          <RefreshCw className="w-4 h-4" />
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="h-full bg-background-elevated rounded-xl border border-border overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-4">
          <h2 className="font-semibold">Network Topology</h2>
          {!labId && labsData && labsData.length > 0 && (
            <select
              value={selectedLab || ''}
              onChange={(e) => setSelectedLab(e.target.value)}
              className="px-3 py-1.5 bg-background border border-border rounded-lg text-sm"
            >
              {labsData.map((lab: any) => (
                <option key={lab.id} value={lab.id}>
                  {getLabLabel(lab)}
                </option>
              ))}
            </select>
          )}
        </div>
        <button
          onClick={() => refetchTopology()}
          className="p-2 hover:bg-background rounded-lg transition-colors"
        >
          <RefreshCw className={cn('w-4 h-4 text-text-secondary', topologyLoading && 'animate-spin')} />
        </button>
      </div>

      {/* React Flow Canvas */}
      <div className="h-[calc(100%-60px)] relative">
        {/* Warning if links are incomplete */}
        {topologyData?.links && edges.length < topologyData.links.length && (
          <div className="absolute top-4 right-4 z-10 px-3 py-2 bg-warning/20 border border-warning rounded-lg text-sm">
            ⚠️ Topology incomplete: {topologyData.links.length - edges.length} links filtered
          </div>
        )}

        {topologyLoading ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
        ) : nodes.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center gap-2">
            <p className="text-text-secondary">No devices in this lab</p>
            <p className="text-sm text-text-muted">Select a different lab or add devices in CML</p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#3A4554" gap={20} />
            <Controls className="bg-background-elevated border border-border rounded-lg" />
            <MiniMap
              nodeColor={(node) =>
                node.data.isAffected
                  ? '#049FD9'
                  : node.data.state === 'BOOTED'
                  ? '#00D084'
                  : '#3A4554'
              }
              maskColor="rgba(10, 14, 20, 0.8)"
              className="bg-background-elevated border border-border rounded-lg"
            />
          </ReactFlow>
        )}
      </div>

      {/* Legend */}
      {affectedDevices.length > 0 && (
        <div className="absolute bottom-4 left-4 p-3 bg-background-elevated/90 backdrop-blur-sm rounded-lg border border-border">
          <p className="text-xs text-text-muted mb-2">Affected Devices</p>
          <div className="flex flex-wrap gap-2">
            {affectedDevices.map((device) => (
              <span
                key={device}
                className="px-2 py-1 bg-primary/20 text-primary text-xs rounded"
              >
                {device}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
