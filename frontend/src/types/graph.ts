export type NodeType = 'normal' | 'query' | 'community' | 'insert' | 'delete';
export type EdgeType = 'normal' | 'community';

export interface Node {
  id: string;
  label: string;
  type: NodeType;
}

export interface Edge {
  source: string;
  target: string;
  type: EdgeType;
}

export interface GraphData {
  nodes: Node[];
  edges: Edge[];
  recommendInsert: string[];
  recommendDelete: string[];
} 