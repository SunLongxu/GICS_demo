import { GraphData, NodeType } from '../types/graph';

export interface VisualizationPayload {
  nodes: Array<{
    id: string;
    label?: string;
    type?: string;
    keywords?: string[];
  }>;
  edges: Array<{
    source: string;
    target: string;
    type?: string;
    weight?: number;
  }>;
  recommendInsert?: string[];
  recommendDelete?: string[];
}

export function extractVisualization(
  response: Record<string, unknown> | null | undefined
): VisualizationPayload | null {
  if (!response || response.status !== 'success') {
    return null;
  }

  const data = response.data as Record<string, unknown> | undefined;
  if (data?.visualization) {
    return data.visualization as VisualizationPayload;
  }

  if (Array.isArray(response.nodes)) {
    return {
      nodes: response.nodes as VisualizationPayload['nodes'],
      edges: (response.edges as VisualizationPayload['edges']) ?? [],
      recommendInsert: (response.recommendInsert as string[]) ?? [],
      recommendDelete: (response.recommendDelete as string[]) ?? [],
    };
  }

  if (data && Array.isArray(data.nodes)) {
    return data as unknown as VisualizationPayload;
  }

  return null;
}

export function toGraphData(
  visualization: VisualizationPayload,
  seedNodeId?: string | number | null
): GraphData {
  const seedKey = seedNodeId != null ? String(seedNodeId) : null;

  return {
    nodes: visualization.nodes.map((node) => ({
      id: node.id,
      label: node.label ?? `Node ${node.id}`,
      type: (seedKey && String(node.id) === seedKey
        ? 'query'
        : (node.type || 'normal')) as NodeType,
      keywords: node.keywords ?? [],
    })),
    edges: visualization.edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
      type: (edge.type || 'normal') as GraphData['edges'][0]['type'],
      weight: edge.weight ?? 1,
    })),
    recommendInsert: visualization.recommendInsert ?? [],
    recommendDelete: visualization.recommendDelete ?? [],
  };
}

export async function parseApiError(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json();
    return (body.message as string) || (body.error as string) || fallback;
  } catch {
    return fallback;
  }
}
