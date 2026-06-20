"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

export interface KGNode {
  id: string;
  label: string;
  description: string;
}

export interface KGEdge {
  source: string;
  target: string;
  relationship: string;
}

interface KnowledgeGraphProps {
  nodes: KGNode[];
  edges: KGEdge[];
}

// Simple deterministic layout: arrange nodes in a circle. Good enough for
// the handful of components (~5) this pipeline typically produces — a real
// force-directed layout engine would be overkill here.
function layoutNodes(nodes: KGNode[]): Node[] {
  const radius = 220;
  const centerX = 320;
  const centerY = 240;

  return nodes.map((n, i) => {
    const angle = (2 * Math.PI * i) / Math.max(nodes.length, 1) - Math.PI / 2;
    return {
      id: n.id,
      position: {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      },
      data: { label: n.label, description: n.description },
      style: {
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: 14,
        padding: "10px 14px",
        fontSize: 12,
        fontWeight: 600,
        color: "#1e293b",
        boxShadow: "0 1px 3px rgba(15, 23, 42, 0.08)",
        width: 150,
        textAlign: "center" as const,
      },
    };
  });
}

function layoutEdges(edges: KGEdge[]): Edge[] {
  return edges.map((e, i) => ({
    id: `${e.source}-${e.target}-${i}`,
    source: e.source,
    target: e.target,
    label: e.relationship,
    labelStyle: { fontSize: 10, fill: "#6366f1", fontWeight: 600 },
    labelBgStyle: { fill: "#eef2ff" },
    style: { stroke: "#c7d2fe", strokeWidth: 1.5 },
    markerEnd: { type: MarkerType.ArrowClosed, color: "#a5b4fc" },
    animated: true,
  }));
}

export default function KnowledgeGraph({ nodes, edges }: KnowledgeGraphProps) {
  const flowNodes = useMemo(() => layoutNodes(nodes), [nodes]);
  const flowEdges = useMemo(() => layoutEdges(edges), [edges]);

  if (nodes.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-2xl border border-slate-100 bg-white text-sm text-slate-400">
        No component graph available for this paper.
      </div>
    );
  }

  return (
    <div className="h-[480px] w-full overflow-hidden rounded-2xl border border-slate-100 bg-slate-50">
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#cbd5e1" gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
