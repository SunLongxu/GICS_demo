import React, { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import CytoscapeComponent from 'cytoscape-react';
import { Box, Button, IconButton, Paper, Stack, TextField } from '@mui/material';
import { Add as AddIcon, Remove as RemoveIcon, ZoomIn, ZoomOut } from '@mui/icons-material';

interface Node {
  id: string;
  label: string;
}

interface Edge {
  source: string;
  target: string;
  label?: string;
}

interface GraphVisualizationProps {
  initialNodes?: Node[];
  initialEdges?: Edge[];
  onNodeAdd?: (node: Node) => void;
  onNodeRemove?: (nodeId: string) => void;
  onEdgeAdd?: (edge: Edge) => void;
  onEdgeRemove?: (edgeId: string) => void;
}

const GraphVisualization: React.FC<GraphVisualizationProps> = ({
  initialNodes = [],
  initialEdges = [],
  onNodeAdd,
  onNodeRemove,
  onEdgeAdd,
  onEdgeRemove,
}) => {
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [newNodeLabel, setNewNodeLabel] = useState('');

  const elements = {
    nodes: initialNodes.map((node) => ({
      data: { id: node.id, label: node.label },
    })),
    edges: initialEdges.map((edge) => ({
      data: {
        id: `${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        label: edge.label,
      },
    })),
  };

  const layout = {
    name: 'cose',
    animate: true,
    nodeDimensionsIncludeLabels: true,
  };

  const style = [
    {
      selector: 'node',
      style: {
        'background-color': '#4CAF50',
        'label': 'data(label)',
        'text-valign': 'center',
        'text-halign': 'center',
        'width': 30,
        'height': 30,
      },
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': '#666',
        'target-arrow-color': '#666',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'label': 'data(label)',
      },
    },
  ];

  const handleAddNode = () => {
    if (!newNodeLabel) return;
    
    const newNode: Node = {
      id: `node-${Date.now()}`,
      label: newNodeLabel,
    };

    onNodeAdd?.(newNode);
    setNewNodeLabel('');
  };

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.2);
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 0.8);
    }
  };

  return (
    <Box sx={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" spacing={2} alignItems="center">
          <TextField
            label="节点标签"
            value={newNodeLabel}
            onChange={(e) => setNewNodeLabel(e.target.value)}
            size="small"
          />
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleAddNode}
            disabled={!newNodeLabel}
          >
            添加节点
          </Button>
          <IconButton onClick={handleZoomIn}>
            <ZoomIn />
          </IconButton>
          <IconButton onClick={handleZoomOut}>
            <ZoomOut />
          </IconButton>
        </Stack>
      </Paper>
      <Box sx={{ flexGrow: 1, border: '1px solid #ddd', borderRadius: 1, overflow: 'hidden' }}>
        <CytoscapeComponent
          elements={elements}
          layout={layout}
          style={{ width: '100%', height: '100%' }}
          stylesheet={style}
          cy={(cy) => {
            cyRef.current = cy;
          }}
        />
      </Box>
    </Box>
  );
};

export default GraphVisualization; 