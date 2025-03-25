import { useState, useCallback } from 'react'
import {
  Box,
  Container,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Paper,
  Chip,
  List,
  ListItem,
  ListItemText,
  Grid,
  IconButton,
  Stack,
  useTheme,
  ThemeProvider,
  createTheme,
  Divider,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import RemoveIcon from '@mui/icons-material/Remove'
import CytoscapeComponent from 'react-cytoscapejs'
import { Core } from 'cytoscape'
import './App.css'

// Color scheme that is colorblind-friendly and modern
const COLORS = {
  query: '#3498db',     // Soft Blue
  community: '#9b59b6', // Purple
  insert: '#e67e22',    // Darker Orange
  delete: '#e74c3c',    // Coral Red
  normal: '#7f8c8d',    // Darker Gray
  edges: {
    community: '#8e44ad', // Dark Purple
    normal: '#bdc3c7'     // Lighter Gray
  }
}

// Custom theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#3498db',
      light: '#5dade2',
      dark: '#2980b9',
    },
    secondary: {
      main: '#9b59b6',
      light: '#a569bd',
      dark: '#8e44ad',
    },
    background: {
      default: '#ecf0f1',
      paper: '#ffffff',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
      letterSpacing: '-0.5px',
    },
    h6: {
      fontWeight: 500,
      fontSize: '1.1rem',
    },
    button: {
      textTransform: 'none',
      fontWeight: 500,
      fontSize: '1rem',
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 4px 20px rgba(0,0,0,0.05)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          },
        },
        contained: {
          '&:hover': {
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          '&:hover': {
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
          },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
          },
        },
      },
    },
  },
})

// Example queries
const EXAMPLE_QUERIES = [
  'John Smith, Mary Johnson',
  'David Brown, Sarah Davis',
  'Michael Wilson, Jennifer Taylor'
]

// Initial graph data for testing
const INITIAL_GRAPH_DATA = {
  nodes: [
    { id: 'q1', label: 'John Smith', type: 'query', color: COLORS.query },
    { id: 'q2', label: 'Mary Johnson', type: 'query', color: COLORS.query },
    { id: 'c1', label: 'Community Node 1', type: 'community', color: COLORS.community },
    { id: 'c2', label: 'Community Node 2', type: 'community', color: COLORS.community },
    { id: 'i1', label: 'Insert Node 1', type: 'insert', color: COLORS.insert },
    { id: 'i2', label: 'Insert Node 2', type: 'insert', color: COLORS.insert },
    { id: 'i3', label: 'Insert Node 3', type: 'insert', color: COLORS.insert },
    { id: 'i4', label: 'Insert Node 4', type: 'insert', color: COLORS.insert },
    { id: 'i5', label: 'Insert Node 5', type: 'insert', color: COLORS.insert },
    { id: 'i6', label: 'Insert Node 6', type: 'insert', color: COLORS.insert },
    { id: 'i7', label: 'Insert Node 7', type: 'insert', color: COLORS.insert },
    { id: 'i8', label: 'Insert Node 8', type: 'insert', color: COLORS.insert },
    { id: 'i9', label: 'Insert Node 9', type: 'insert', color: COLORS.insert },
    { id: 'i10', label: 'Insert Node 10', type: 'insert', color: COLORS.insert },
    { id: 'd1', label: 'Delete Node 1', type: 'delete', color: COLORS.delete },
    { id: 'd2', label: 'Delete Node 2', type: 'delete', color: COLORS.delete },
    { id: 'd3', label: 'Delete Node 3', type: 'delete', color: COLORS.delete },
    { id: 'd4', label: 'Delete Node 4', type: 'delete', color: COLORS.delete },
    { id: 'd5', label: 'Delete Node 5', type: 'delete', color: COLORS.delete },
    { id: 'd6', label: 'Delete Node 6', type: 'delete', color: COLORS.delete },
    { id: 'd7', label: 'Delete Node 7', type: 'delete', color: COLORS.delete },
    { id: 'd8', label: 'Delete Node 8', type: 'delete', color: COLORS.delete },
    { id: 'd9', label: 'Delete Node 9', type: 'delete', color: COLORS.delete },
    { id: 'd10', label: 'Delete Node 10', type: 'delete', color: COLORS.delete },
    { id: 'n1', label: 'Normal Node 1', type: 'normal', color: COLORS.normal }
  ],
  edges: [
    { source: 'q1', target: 'q2', type: 'normal', color: COLORS.edges.normal },
    { source: 'q1', target: 'c1', type: 'community', color: COLORS.edges.community },
    { source: 'q2', target: 'c2', type: 'community', color: COLORS.edges.community },
    { source: 'c1', target: 'c2', type: 'community', color: COLORS.edges.community }
  ],
  recommendInsert: ['i1', 'i2', 'i3', 'i4', 'i5', 'i6', 'i7', 'i8', 'i9', 'i10'],
  recommendDelete: ['d1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7', 'd8', 'd9', 'd10']
}

// Legend items for node and edge types
const LEGEND_ITEMS = [
  { type: 'Query Node', color: COLORS.query },
  { type: 'Community Node', color: COLORS.community },
  { type: 'Insert Node', color: COLORS.insert },
  { type: 'Delete Node', color: COLORS.delete },
  { type: 'Normal Node', color: COLORS.normal },
  { type: 'Community Edge', color: COLORS.edges.community },
  { type: 'Normal Edge', color: COLORS.edges.normal }
]

function App() {
  const [dataset, setDataset] = useState('DBLP')
  const [model, setModel] = useState('GNN')
  const [searchQuery, setSearchQuery] = useState('')
  const [graphData, setGraphData] = useState(INITIAL_GRAPH_DATA)
  const [cyInstance, setCyInstance] = useState<Core | null>(null)
  const [zoom, setZoom] = useState(1)

  // API calls
  const searchAPI = async (query: string, dataset: string, model: string) => {
    // TODO: Implement actual API call
    console.log('Search API called with:', { query, dataset, model })
    return INITIAL_GRAPH_DATA
  }

  const insertNodeAPI = async (nodeId: string) => {
    // TODO: Implement actual API call
    console.log('Insert node API called with:', nodeId)
    return {
      ...graphData,
      nodes: graphData.nodes.map(node =>
        node.id === nodeId ? { ...node, type: 'community', color: COLORS.community } : node
      )
    }
  }

  const deleteNodeAPI = async (nodeId: string) => {
    // TODO: Implement actual API call
    console.log('Delete node API called with:', nodeId)
    return {
      ...graphData,
      nodes: graphData.nodes.map(node =>
        node.id === nodeId ? { ...node, type: 'normal', color: COLORS.normal } : node
      )
    }
  }

  // Event handlers
  const handleSearch = async () => {
    const result = await searchAPI(searchQuery, dataset, model)
    setGraphData(result)
    centerGraph()
  }

  const handleExampleClick = (query: string) => {
    setSearchQuery(query)
    handleSearch()
  }

  const handleNodeOperation = async (nodeId: string, operation: 'insert' | 'delete') => {
    const result = operation === 'insert' 
      ? await insertNodeAPI(nodeId)
      : await deleteNodeAPI(nodeId)
    setGraphData(result)
  }

  // Graph manipulation
  const centerGraph = useCallback(() => {
    if (cyInstance) {
      cyInstance.fit()
      cyInstance.center()
    }
  }, [cyInstance])

  const handleZoomIn = () => {
    if (cyInstance) {
      const currentZoom = cyInstance.zoom();
      const newZoom = currentZoom * 1.2;
      cyInstance.animate({
        zoom: newZoom,
        duration: 200
      });
    }
  }

  const handleZoomOut = () => {
    if (cyInstance) {
      const currentZoom = cyInstance.zoom();
      const newZoom = currentZoom * 0.8;
      cyInstance.animate({
        zoom: newZoom,
        duration: 200
      });
    }
  }

  const handleCyInit = (cy: Core) => {
    setCyInstance(cy);
    
    // 配置节点拖拽
    cy.nodes().ungrabify(); // 先禁用默认的拖拽
    cy.nodes().grabify();   // 重新启用拖拽，确保正确配置

    // 添加拖拽事件监听器
    cy.on('dragfree', 'node', (evt) => {
      const node = evt.target;
      console.log(`Node ${node.id()} dragged to position:`, node.position());
    });

    // 初始化时居中和适配
    requestAnimationFrame(() => {
      cy.fit();
      cy.center();
    });
  }

  const elements = [
    ...graphData.nodes.map(node => ({
      data: { 
        id: node.id, 
        label: node.label,
        type: node.type,
        color: node.color
      }
    })),
    ...graphData.edges.map(edge => ({
      data: { 
        id: `${edge.source}-${edge.target}`,
        source: edge.source, 
        target: edge.target,
        type: edge.type,
        color: edge.color
      }
    }))
  ]

  return (
    <ThemeProvider theme={theme}>
      <Container maxWidth="xl" sx={{ 
        py: 2,
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #ecf0f1 0%, #f5f6fa 100%)',
      }}>
        <Box sx={{ mb: 3 }}>
          <Typography 
            variant="h4" 
            component="h1" 
            gutterBottom 
            align="center" 
            sx={{ 
              fontWeight: 'bold', 
              background: 'linear-gradient(45deg, #1976d2 30%, #9c27b0 90%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              mb: 2
            }}
          >
            Interactive Community Search System (GICS)
          </Typography>
        </Box>
        
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth>
              <InputLabel>Dataset</InputLabel>
              <Select
                value={dataset}
                label="Dataset"
                onChange={(e) => setDataset(e.target.value)}
                sx={{
                  backgroundColor: 'white',
                  '&:hover': {
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  },
                }}
              >
                <MenuItem value="DBLP">DBLP</MenuItem>
                <MenuItem value="OTHER">Other Dataset</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <FormControl fullWidth>
              <InputLabel>Search Model</InputLabel>
              <Select
                value={model}
                label="Search Model"
                onChange={(e) => setModel(e.target.value)}
                sx={{
                  backgroundColor: 'white',
                  '&:hover': {
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  },
                }}
              >
                <MenuItem value="GNN">GNN</MenuItem>
                <MenuItem value="ACQ">ACQ</MenuItem>
                <MenuItem value="WCS">WCS</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              label="Enter Query (names separated by commas)"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              variant="outlined"
              sx={{
                backgroundColor: 'white',
                '&:hover': {
                  '& .MuiOutlinedInput-root': {
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  },
                },
              }}
            />
          </Grid>

          <Grid item xs={12} md={2}>
            <Button
              fullWidth
              variant="contained"
              onClick={handleSearch}
              sx={{ 
                height: '56px',
                background: 'linear-gradient(45deg, #3498db 30%, #9b59b6 90%)',
                color: 'white',
                fontSize: '1.2rem',
                fontWeight: 500,
                '&:hover': {
                  background: 'linear-gradient(45deg, #2980b9 30%, #8e44ad 90%)',
                }
              }}
            >
              Search
            </Button>
          </Grid>
        </Grid>

        <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="subtitle1" sx={{ color: 'text.secondary', whiteSpace: 'nowrap' }}>
            Example Queries:
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {EXAMPLE_QUERIES.map((query, index) => (
              <Chip
                key={index}
                label={query}
                onClick={() => handleExampleClick(query)}
                clickable
                sx={{ 
                  backgroundColor: 'white',
                  transition: 'all 0.2s',
                  '&:hover': {
                    backgroundColor: 'rgba(25, 118, 210, 0.08)',
                  },
                }}
              />
            ))}
          </Stack>
        </Box>

        <Grid container spacing={2}>
          <Grid item xs={12} md={8}>
            <Paper 
              elevation={3} 
              sx={{ 
                height: 'calc(100vh - 380px)',
                width: '100%',
                position: 'relative',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                background: 'linear-gradient(to right bottom, #ffffff, #f8f9fa)',
              }}
            >
              <Box
                sx={{
                  position: 'absolute',
                  top: 16,
                  right: 16,
                  zIndex: 2,
                  backgroundColor: 'rgba(255, 255, 255, 0.8)',
                  borderRadius: 1,
                  padding: 0.5,
                }}
              >
                <IconButton onClick={handleZoomIn} size="small">
                  <AddIcon />
                </IconButton>
                <IconButton onClick={handleZoomOut} size="small">
                  <RemoveIcon />
                </IconButton>
              </Box>
              <Box 
                className="graph-container"
                sx={{
                  flex: 1,
                  minHeight: 0,
                  '& .cytoscape-container': {
                    position: 'absolute',
                    left: 0,
                    top: 0,
                    width: '100%',
                    height: '100%'
                  }
                }}
              >
                <CytoscapeComponent
                  elements={elements}
                  style={{ 
                    width: '100%', 
                    height: '100%'
                  }}
                  cy={(cy) => {
                    handleCyInit(cy);
                  }}
                  stylesheet={[
                    {
                      selector: 'node',
                      style: {
                        'background-color': 'data(color)',
                        'label': 'data(label)',
                        'color': '#000000',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'font-size': '12px',
                        'width': 30,
                        'height': 30,
                        'text-outline-color': '#ffffff',
                        'text-outline-width': 2,
                        'text-outline-opacity': 0.8,
                      }
                    },
                    {
                      selector: 'edge',
                      style: {
                        'width': 2,
                        'line-color': 'data(color)',
                        'curve-style': 'unbundled-bezier',
                        'target-arrow-shape': 'none',
                        'opacity': 0.8,
                      }
                    }
                  ]}
                  layout={{ 
                    name: 'cose',
                    animate: false,
                    nodeDimensionsIncludeLabels: true,
                    idealEdgeLength: () => 100,
                    nodeOverlap: 20,
                    refresh: 20,
                    fit: true,
                    padding: 30,
                    randomize: true,
                    componentSpacing: 100,
                    nodeRepulsion: () => 8000,
                    gravity: 0.3,
                  }}
                  userZoomingEnabled={true}
                  userPanningEnabled={true}
                  boxSelectionEnabled={false}
                />
              </Box>
            </Paper>
            <Paper 
              elevation={3} 
              sx={{ 
                mt: 1, 
                p: 1,
                background: 'linear-gradient(to right, #ffffff, #f8f9fa)',
              }}
            >
              <Stack
                direction="row"
                spacing={1}
                alignItems="center"
                flexWrap="wrap"
                useFlexGap
                sx={{ justifyContent: 'center' }}
              >
                {LEGEND_ITEMS.map((item, index) => (
                  <Box
                    key={index}
                    sx={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 0.5,
                      px: 1,
                    }}
                  >
                    <Box
                      sx={{
                        width: 16,
                        height: 16,
                        backgroundColor: item.color,
                        borderRadius: item.type.includes('Edge') ? 0 : '50%',
                      }}
                    />
                    <Typography variant="caption">{item.type}</Typography>
                  </Box>
                ))}
              </Stack>
            </Paper>
          </Grid>
          
          <Grid item xs={12} md={2}>
            <Paper 
              elevation={3} 
              sx={{ 
                height: 'calc(100vh - 380px)',
                p: 2,
                background: 'linear-gradient(to right bottom, #ffffff, #f8f9fa)',
                overflow: 'auto'
              }}
            >
              <Typography variant="h6" gutterBottom sx={{ color: 'text.primary', fontSize: '0.95rem', position: 'sticky', top: 0, backgroundColor: '#fff', pb: 1, zIndex: 1 }}>
                Recommended Insertions
              </Typography>
              <Box sx={{ 
                display: 'flex', 
                flexDirection: 'column',
                gap: 0.5
              }}>
                {graphData.recommendInsert.map(nodeId => {
                  const node = graphData.nodes.find(n => n.id === nodeId)
                  return (
                    <Box
                      key={nodeId}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        backgroundColor: 'rgba(230, 126, 34, 0.05)',
                        borderRadius: 1,
                        py: 0.5,
                        px: 1,
                        width: '100%',
                        height: '36px',
                        '&:hover': {
                          backgroundColor: 'rgba(230, 126, 34, 0.1)',
                        },
                      }}
                    >
                      <Typography 
                        variant="body2"
                        sx={{ 
                          color: 'text.primary', 
                          fontSize: '0.9rem',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          flex: 1,
                          mr: 1
                        }}
                      >
                        {node?.label}
                      </Typography>
                      <IconButton
                        size="small"
                        onClick={() => handleNodeOperation(nodeId, 'insert')}
                        sx={{
                          backgroundColor: COLORS.insert,
                          color: 'white',
                          width: '24px',
                          height: '24px',
                          '&:hover': {
                            backgroundColor: COLORS.insert,
                            opacity: 0.9,
                          },
                          '& .MuiSvgIcon-root': {
                            fontSize: '1rem',
                          },
                        }}
                      >
                        <AddIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  )
                })}
              </Box>
            </Paper>
          </Grid>

          <Grid item xs={12} md={2}>
            <Paper 
              elevation={3} 
              sx={{ 
                height: 'calc(100vh - 380px)',
                p: 2,
                background: 'linear-gradient(to right bottom, #ffffff, #f8f9fa)',
                overflow: 'auto'
              }}
            >
              <Typography variant="h6" gutterBottom sx={{ color: 'text.primary', fontSize: '0.95rem', position: 'sticky', top: 0, backgroundColor: '#fff', pb: 1, zIndex: 1 }}>
                Recommended Deletions
              </Typography>
              <List dense sx={{ 
                display: 'flex',
                flexDirection: 'column',
                gap: 0.5,
                p: 0
              }}>
                {graphData.recommendDelete.map(nodeId => {
                  const node = graphData.nodes.find(n => n.id === nodeId)
                  return (
                    <ListItem 
                      key={nodeId}
                      sx={{
                        borderRadius: 1,
                        backgroundColor: 'rgba(231, 76, 60, 0.05)',
                        py: 0.5,
                        px: 1,
                        height: '36px',
                        '&:hover': {
                          backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        },
                      }}
                    >
                      <ListItemText 
                        primary={node?.label}
                        primaryTypographyProps={{
                          sx: { 
                            color: 'text.primary', 
                            fontSize: '0.9rem',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }
                        }}
                        sx={{
                          m: 0,
                          flex: 1,
                          mr: 1
                        }}
                      />
                      <IconButton
                        size="small"
                        onClick={() => handleNodeOperation(nodeId, 'delete')}
                        sx={{
                          backgroundColor: COLORS.delete,
                          color: 'white',
                          width: '24px',
                          height: '24px',
                          '&:hover': {
                            backgroundColor: COLORS.delete,
                            opacity: 0.9,
                          },
                          '& .MuiSvgIcon-root': {
                            fontSize: '1rem',
                          },
                        }}
                      >
                        <RemoveIcon fontSize="small" />
                      </IconButton>
                    </ListItem>
                  )
                })}
              </List>
            </Paper>
          </Grid>
        </Grid>

        <Box sx={{ 
          mt: 2, 
          textAlign: 'center',
          backgroundColor: 'rgba(255, 255, 255, 0.9)',
          borderRadius: 2,
          py: 1.5,
          px: 2,
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
        }}>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center',
            gap: 3
          }}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center',
              gap: 1
            }}>
              <img 
                src="/hkbu_logo.jpg" 
                alt="HKBU Logo" 
                style={{ 
                  height: '24px',
                  width: 'auto',
                  opacity: 0.9
                }} 
              />
              <Typography variant="body2">
                Hong Kong Baptist University
              </Typography>
            </Box>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center',
              gap: 1
            }}>
              <img 
                src="/sfu_logo.png" 
                alt="SFU Logo" 
                style={{ 
                  height: '24px',
                  width: 'auto',
                  opacity: 0.9
                }} 
              />
              <Typography variant="body2">
                Simon Fraser University
              </Typography>
            </Box>
          </Box>

          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center',
            gap: 3
          }}>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center',
              gap: 1
            }}>
              <Typography 
                variant="body2" 
                component="a" 
                href="https://github.com/SunLongxu/GICS_demo" 
                target="_blank"
                sx={{ 
                  color: 'primary.main',
                  textDecoration: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.5,
                  '&:hover': {
                    textDecoration: 'underline'
                  }
                }}
              >
                <svg height="16" width="16" viewBox="0 0 16 16" style={{ fill: 'currentColor' }}>
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                </svg>
                GitHub
              </Typography>
            </Box>
          </Box>
        </Box>
        <Typography 
          variant="caption" 
          display="block" 
          align="center"
          sx={{ 
            mt: 1, 
            mb: 1,
            color: 'text.secondary',
            opacity: 0.8
          }}
        >
          © 2024 Interactive Community Search System (GICS) · MIT License
        </Typography>
      </Container>
    </ThemeProvider>
  )
}

export default App
