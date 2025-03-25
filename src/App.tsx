import { useState } from 'react'
import { Box, CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import GraphVisualization from './components/GraphVisualization'

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2196f3',
    },
    secondary: {
      main: '#f50057',
    },
  },
});

interface Node {
  id: string;
  label: string;
}

interface Edge {
  source: string;
  target: string;
  label?: string;
}

function App() {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  const handleNodeAdd = (node: Node) => {
    setNodes([...nodes, node]);
  };

  const handleNodeRemove = (nodeId: string) => {
    setNodes(nodes.filter((node) => node.id !== nodeId));
    setEdges(edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId));
  };

  const handleEdgeAdd = (edge: Edge) => {
    setEdges([...edges, edge]);
  };

  const handleEdgeRemove = (edgeId: string) => {
    const [source, target] = edgeId.split('-');
    setEdges(edges.filter((edge) => edge.source !== source || edge.target !== target));
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ width: '100vw', height: '100vh', p: 2 }}>
        <GraphVisualization
          initialNodes={nodes}
          initialEdges={edges}
          onNodeAdd={handleNodeAdd}
          onNodeRemove={handleNodeRemove}
          onEdgeAdd={handleEdgeAdd}
          onEdgeRemove={handleEdgeRemove}
        />
      </Box>
    </ThemeProvider>
  )
}

export default App 