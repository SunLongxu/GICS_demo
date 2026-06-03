import { useState, useCallback, useEffect, useMemo } from 'react'
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
  Tooltip,
  CircularProgress,
  Alert,
} from '@mui/material'
import { Search as SearchIcon, ZoomIn as ZoomInIcon, ZoomOut as ZoomOutIcon, AccountTree as AccountTreeIcon, GridView as GridViewIcon, Refresh as RefreshIcon, Add as AddIcon, Remove as RemoveIcon } from '@mui/icons-material'
import CytoscapeComponent from 'react-cytoscapejs'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import { Core, NodeSingular, EdgeSingular } from 'cytoscape'
import './App.css'
import { fetchInitialGraph, insertNode, deleteNode, connectWebSocket, disconnectWebSocket, testVisualization, testServerConnection, NETWORK_ERROR } from './services/api'
import { extractVisualization, toGraphData } from './utils/graphResponse'
import { GraphData as ImportedGraphData, NodeType, EdgeType } from './types/graph'

// 注册dagre布局
cytoscape.use(dagre)

const publicAsset = (filename: string) =>
  `${import.meta.env.BASE_URL}${filename}`

// Color scheme that is colorblind-friendly and modern
const COLORS = {
  query: '#3498db',     // Soft Blue
  community: '#9b59b6', // Purple
  insert: '#e67e22',    // Darker Orange
  delete: '#e74c3c',    // Coral Red
  normal: '#7f8c8d',    // Darker Gray
  edges: {
    community: '#8e44ad', // Dark Purple
    normal: '#95a5a6'     // Darker Gray
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
  'Jiawei Han',
  'Christos Faloutsos',
  'Philip S. Yu',
]

// Initial graph data for testing
const INITIAL_GRAPH_DATA: ImportedGraphData = {
  nodes: [
    { id: "1", label: "Author 1", type: "normal" as NodeType },
    { id: "2", label: "Author 2", type: "normal" as NodeType },
    { id: "3", label: "Author 3", type: "normal" as NodeType },
    { id: "4", label: "Author 4", type: "normal" as NodeType },
    { id: "5", label: "Author 5", type: "normal" as NodeType },
    { id: "6", label: "Author 6", type: "normal" as NodeType },
    { id: "7", label: "Author 7", type: "normal" as NodeType },
    { id: "8", label: "Author 8", type: "normal" as NodeType }
  ],
  edges: [
    { source: "1", target: "2", type: "normal" as EdgeType },
    { source: "2", target: "3", type: "normal" as EdgeType },
    { source: "3", target: "4", type: "normal" as EdgeType },
    { source: "4", target: "5", type: "normal" as EdgeType },
    { source: "5", target: "6", type: "normal" as EdgeType },
    { source: "6", target: "7", type: "normal" as EdgeType },
    { source: "7", target: "8", type: "normal" as EdgeType },
    { source: "8", target: "1", type: "normal" as EdgeType }
  ],
  recommendInsert: [],
  recommendDelete: []
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

type Layouts = 'grid' | 'circle' | 'concentric' | 'breadthfirst' | 'cose' | 'random' | 'layered'

interface SearchResponse {
  status: string;
  message?: string;
  data?: {
    status?: string;
    message?: string;
    data?: ImportedGraphData;
  };
}

// 添加通知状态类型
interface Notification {
  message: string;
  type: 'success' | 'error' | 'info';
}

// 添加节点和边的接口定义
interface VisualizationNode {
  id: string;
  label: string;
  type?: string;
  keywords?: string[];
}

interface VisualizationEdge {
  source: string;
  target: string;
  type?: string;
  weight?: number;
}

// 添加GraphVisualizationData接口定义
interface GraphVisualizationData {
  nodes: VisualizationNode[];
  edges: VisualizationEdge[];
  recommendInsert: string[];
  recommendDelete: string[];
}

// 修改推荐数据类型
interface RecommendationNode {
  id: number | string;
  label?: string;
  type?: string;
  keywords?: string[];
}

// 修改GraphData类型定义
type GraphData = GraphVisualizationData;

function App() {
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDataset, setSelectedDataset] = useState('DBLP');
  const [selectedModel, setSelectedModel] = useState('GNN');
  const [selectedConstraint, setSelectedConstraint] = useState('Size k');
  const [selectedParameter, setSelectedParameter] = useState('25');
  const [cy, setCy] = useState<Core | null>(null);
  const [layout, setLayout] = useState<Layouts>('circle');
  const [zoomLevel, setZoomLevel] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notification, setNotification] = useState<Notification | null>(null);

  // 布局配置对象
const layouts = {
  grid: {
    name: 'grid',
    fit: true,
    padding: 50,
    avoidOverlap: true,
    animate: false
  },
  circle: {
    name: 'circle',
    fit: true,
    padding: 50,
    avoidOverlap: true,
    animate: false,
    radius: 200
  },
  concentric: {
    name: 'concentric',
    fit: true,
    padding: 50,
    avoidOverlap: true,
    animate: false,
    minNodeSpacing: 50
  },
  breadthfirst: {
    name: 'breadthfirst',
    fit: true,
    padding: 50,
    avoidOverlap: true,
    animate: false
  },
  cose: {
    name: 'cose',
    fit: true,
    padding: 50,
    componentSpacing: 50,
    randomize: false,
    nodeRepulsion: 1000,
    edgeElasticity: 100,
    nestingFactor: 5,
    gravity: 50,
    numIter: 500,
    initialTemp: 10,
    coolingFactor: 0.99,
    animate: false
  },
  random: {
    name: 'random',
    fit: true,
    padding: 50,
    animate: false
  },
  layered: {
    name: 'dagre',
    fit: true,
    padding: 50,
    animate: false,
    rankDir: 'TB',
    nodeDimensionsIncludeLabels: true,
    ranker: 'network-simplex',
    rankSep: 100,
    nodeSep: 50,
    edgeSep: 50,
    run: function(cy: Core) {
      console.log('执行layered自定义布局');
      
      try {
        // 严格按照类型分类节点
        const queryNodes = cy.nodes().filter((node) => node.data('type') === 'query');
        const communityNodes = cy.nodes().filter((node) => node.data('type') === 'community');
        const deleteNodes = cy.nodes().filter((node) => node.data('type') === 'delete');
        const insertNodes = cy.nodes().filter((node) => node.data('type') === 'insert');
        const normalNodes = cy.nodes().filter((node) => node.data('type') === 'normal');
        
        console.log(`节点统计 - 总数: ${cy.nodes().length}, 查询: ${queryNodes.length}, 社区: ${communityNodes.length}, 删除: ${deleteNodes.length}, 插入: ${insertNodes.length}, 普通: ${normalNodes.length}`);

        // 获取画布中心和尺寸
        const centerX = cy.width() / 2;
        const centerY = cy.height() / 2;
        const minDimension = Math.min(cy.width(), cy.height());
        
        // 设置5层不同的半径
        const radius1 = minDimension * 0.2;  // 第一层（查询节点）半径
        const radius2 = minDimension * 0.6;  // 第二层（第一部分community和delete节点）半径
        const radius3 = minDimension * 1.0;  // 第三层（第二部分community和delete节点）半径
        const radius4 = minDimension * 1.6;  // 第四层（第一部分insertion和normal节点）半径
        const radius5 = minDimension * 2.2;  // 第五层（第二部分insertion和normal节点）半径
        
        // 计算每个节点的大小以确定合适的分布角度
        const avgNodeWidth = 180; // 预估节点宽度，包含标签
        const avgNodeHeight = 100; // 预估节点高度，包含标签和关键词
        
        // 1. 设置查询节点在中心
        queryNodes.forEach((node) => {
          node.position({
            x: centerX,
            y: centerY
          });
        });
        
        // 2. 处理community和delete节点 - 随机分到两层
        // 先合并两种节点
        const innerNodes = [...communityNodes, ...deleteNodes];
        
        if (innerNodes.length > 0) {
          // 重新组织节点顺序 - 交错排列community和delete节点
          const arrangeedInnerNodes = [];
          const maxLength = Math.max(communityNodes.length, deleteNodes.length);
          
          // 交错添加节点
          for (let i = 0; i < maxLength; i++) {
            if (i < communityNodes.length) {
              arrangeedInnerNodes.push({node: communityNodes[i], type: 'community'});
            }
            if (i < deleteNodes.length) {
              arrangeedInnerNodes.push({node: deleteNodes[i], type: 'delete'});
            }
          }
          
          // 随机将节点分配到两层
          const layer2Nodes: {node: cytoscape.NodeSingular, type: string}[] = [];
          const layer3Nodes: {node: cytoscape.NodeSingular, type: string}[] = [];
          
          // 随机分配节点到两层
          arrangeedInnerNodes.forEach(item => {
            // 随机决定节点应该分配到哪一层
            if (Math.random() < 0.5) {
              layer2Nodes.push(item);
            } else {
              layer3Nodes.push(item);
            }
          });
          
          // 确保两层都有节点
          if (layer2Nodes.length === 0 && layer3Nodes.length > 0) {
            // 将一半节点移到第二层
            const halfIndex = Math.floor(layer3Nodes.length / 2);
            layer2Nodes.push(...layer3Nodes.splice(0, halfIndex));
          } else if (layer3Nodes.length === 0 && layer2Nodes.length > 0) {
            // 将一半节点移到第三层
            const halfIndex = Math.floor(layer2Nodes.length / 2);
            layer3Nodes.push(...layer2Nodes.splice(0, halfIndex));
          }
          
          console.log(`内圈节点分配: 第二层 ${layer2Nodes.length} 个, 第三层 ${layer3Nodes.length} 个`);
          
          // 设置第二层节点位置（第一部分community和delete节点）
          if (layer2Nodes.length > 0) {
            const layer2Circumference = 2 * Math.PI * radius2;
            const layer2Spacing = Math.max(layer2Circumference / layer2Nodes.length, avgNodeWidth * 1.5);
            
            layer2Nodes.forEach((item, i) => {
              const angle = (i / layer2Nodes.length) * 2 * Math.PI;
              const randomRadiusOffset = (Math.random() * 0.2) - 0.1; // -10% 到 +10% 的半径变化
              const finalRadius = radius2 * (1 + randomRadiusOffset);
              const angleOffset = (Math.random() * 0.15) - 0.075; // -0.075 到 +0.075 弧度的角度微调
              
              item.node.position({
                x: centerX + finalRadius * Math.cos(angle + angleOffset),
                y: centerY + finalRadius * Math.sin(angle + angleOffset)
              });
            });
          }
          
          // 设置第三层节点位置（第二部分community和delete节点）
          if (layer3Nodes.length > 0) {
            const layer3Circumference = 2 * Math.PI * radius3;
            const layer3Spacing = Math.max(layer3Circumference / layer3Nodes.length, avgNodeWidth * 1.5);
            
            layer3Nodes.forEach((item, i) => {
              const angle = (i / layer3Nodes.length) * 2 * Math.PI;
              const randomRadiusOffset = (Math.random() * 0.2) - 0.1; // -10% 到 +10% 的半径变化
              const finalRadius = radius3 * (1 + randomRadiusOffset);
              const angleOffset = (Math.random() * 0.15) - 0.075; // -0.075 到 +0.075 弧度的角度微调
              
              item.node.position({
                x: centerX + finalRadius * Math.cos(angle + angleOffset),
                y: centerY + finalRadius * Math.sin(angle + angleOffset)
              });
            });
          }
        }
        
        // 3. 处理insertion和normal节点 - 随机分到两层
        // 合并两种节点
        const outerNodes = [...insertNodes, ...normalNodes];
        
        if (outerNodes.length > 0) {
          // 重新组织节点顺序 - 交错排列insertion和normal节点
          const arrangedOuterNodes = [];
          const maxLength = Math.max(insertNodes.length, normalNodes.length);
          
          // 交错添加节点
          for (let i = 0; i < maxLength; i++) {
            if (i < insertNodes.length) {
              arrangedOuterNodes.push({node: insertNodes[i], type: 'insert'});
            }
            if (i < normalNodes.length) {
              arrangedOuterNodes.push({node: normalNodes[i], type: 'normal'});
            }
          }
          
          // 随机将节点分配到两层
          const layer4Nodes: {node: cytoscape.NodeSingular, type: string}[] = [];
          const layer5Nodes: {node: cytoscape.NodeSingular, type: string}[] = [];
          
          // 随机分配节点到两层
          arrangedOuterNodes.forEach(item => {
            // 随机决定节点应该分配到哪一层
            if (Math.random() < 0.5) {
              layer4Nodes.push(item);
            } else {
              layer5Nodes.push(item);
            }
          });
          
          // 确保两层都有节点
          if (layer4Nodes.length === 0 && layer5Nodes.length > 0) {
            // 将一半节点移到第四层
            const halfIndex = Math.floor(layer5Nodes.length / 2);
            layer4Nodes.push(...layer5Nodes.splice(0, halfIndex));
          } else if (layer5Nodes.length === 0 && layer4Nodes.length > 0) {
            // 将一半节点移到第五层
            const halfIndex = Math.floor(layer4Nodes.length / 2);
            layer5Nodes.push(...layer4Nodes.splice(0, halfIndex));
          }
          
          console.log(`外圈节点分配: 第四层 ${layer4Nodes.length} 个, 第五层 ${layer5Nodes.length} 个`);
          
          // 设置第四层节点位置（第一部分insertion和normal节点）
          if (layer4Nodes.length > 0) {
            const layer4Circumference = 2 * Math.PI * radius4;
            const layer4Spacing = Math.max(layer4Circumference / layer4Nodes.length, avgNodeWidth * 1.5);
            
            layer4Nodes.forEach((item, i) => {
              const angle = (i / layer4Nodes.length) * 2 * Math.PI;
              const randomRadiusOffset = (Math.random() * 0.2) - 0.1; // -10% 到 +10% 的半径变化
              const finalRadius = radius4 * (1 + randomRadiusOffset);
              const angleOffset = (Math.random() * 0.15) - 0.075; // -0.075 到 +0.075 弧度的角度微调
              
              item.node.position({
                x: centerX + finalRadius * Math.cos(angle + angleOffset),
                y: centerY + finalRadius * Math.sin(angle + angleOffset)
              });
            });
          }
          
          // 设置第五层节点位置（第二部分insertion和normal节点）
          if (layer5Nodes.length > 0) {
            const layer5Circumference = 2 * Math.PI * radius5;
            const layer5Spacing = Math.max(layer5Circumference / layer5Nodes.length, avgNodeWidth * 1.5);
            
            layer5Nodes.forEach((item, i) => {
              const angle = (i / layer5Nodes.length) * 2 * Math.PI;
              const randomRadiusOffset = (Math.random() * 0.2) - 0.1; // -10% 到 +10% 的半径变化
              const finalRadius = radius5 * (1 + randomRadiusOffset);
              const angleOffset = (Math.random() * 0.15) - 0.075; // -0.075 到 +0.075 弧度的角度微调
              
              item.node.position({
                x: centerX + finalRadius * Math.cos(angle + angleOffset),
                y: centerY + finalRadius * Math.sin(angle + angleOffset)
              });
            });
          }
        }
        
        // 检测节点重叠并尝试微调位置
        setTimeout(() => {
          try {
            // 获取所有节点的当前位置和尺寸
            const nodePositions = cy.nodes().map(node => ({
              id: node.id(),
              pos: node.position(),
              width: node.width(),
              height: node.height(),
              type: node.data('type')
            }));
            
            // 输出一些节点信息以便调试
            console.log('完成5层布局, 节点位置示例:', nodePositions.slice(0, 3));
          } catch(e) {
            console.error('节点位置检查错误:', e);
          }
        }, 200);
        
        console.log('自定义5层布局已应用完成');
        
      } catch(error) {
        console.error('应用layered布局时发生错误:', error);
      }
    }
  }
};

  // 添加 WebSocket 连接
  useEffect(() => {
    console.log('Setting up WebSocket connection...');
    
    const handleWebSocketMessage = (data: any) => {
      console.log('Received WebSocket message:', data);
      if (data.status === 'waiting_for_user_input') {
        setGraphData(data.data);
        setLoading(false);
      } else if (data.status === 'error') {
        setError(NETWORK_ERROR);
        setLoading(false);
      }
    };
    
    // 添加专门处理visualization_update事件的函数
    const handleVisualizationUpdate = (data: any) => {
      console.log('Received visualization update:', data);
      const visualization = extractVisualization(
        data?.nodes ? { status: 'success', ...data } : data
      );
      if (visualization) {
        setGraphData(toGraphData(visualization));
        
        // 更新加载状态
        setLoading(false);
        
        // 添加成功提示
        setNotification({
          message: '可视化数据已更新',
          type: 'success'
        });
      }
    };

    // 使用新的connectWebSocket函数，传递visualization_update处理函数
    connectWebSocket(handleWebSocketMessage, handleVisualizationUpdate)
      .then(() => {
        console.log('WebSocket connected successfully');
      })
      .catch(error => {
        console.error('WebSocket connection error:', error);
        // setError('无法连接到WebSocket服务器');
      });

    testServerConnection()
      .then(() => console.log('Backend health check OK'))
      .catch((err) => console.warn('Backend not reachable:', err));

    return () => {
      console.log('Cleaning up WebSocket connection...');
      disconnectWebSocket();
    };
  }, []);

  // 修改初始化图数据的useEffect - 初始化时不加载数据
  useEffect(() => {
    // 不在组件挂载时获取数据，只设置一个空的初始状态
    setGraphData({
      nodes: [],
      edges: [],
      recommendInsert: [],
      recommendDelete: []
    });
  }, []);

  // 修改 Cytoscape 组件的数据处理
  const cytoscapeElements = useMemo(() => {
    if (!graphData) {
      console.log('No graph data available');
      return [];
    }
    
    console.log('Processing graph data:', graphData);
    
    // 处理节点数据
    const nodes = graphData.nodes.map(node => ({
        data: {
          id: node.id,
        label: node.label,
        type: node.type || 'normal',
        keywords: node.keywords || []
      }
    }));
    
    // 处理边数据
    const edges = graphData.edges.map(edge => ({
        data: {
          id: `${edge.source}-${edge.target}`,
          source: edge.source,
          target: edge.target,
        type: edge.type || 'normal',
        weight: edge.weight || 1
        }
    }));
    
    console.log('Final Cytoscape elements:', { nodes, edges });
    return [...nodes, ...edges];
  }, [graphData]);

  // Graph manipulation
  const centerGraph = useCallback(() => {
    if (cy) {
      cy.fit()
      cy.center()
    }
  }, [cy])

  const handleZoomIn = () => {
    if (cy) {
      const currentZoom = cy.zoom()
      const newZoom = currentZoom * 1.2
      cy.animate({
        zoom: newZoom,
        duration: 200
      })
    }
  }

  const handleZoomOut = () => {
    if (cy) {
      const currentZoom = cy.zoom()
      const newZoom = currentZoom * 0.8
      cy.animate({
        zoom: newZoom,
        duration: 200
      })
    }
  }

  // 修改handleCyInit函数，移除自动布局逻辑
  const handleCyInit = (cyInstance: Core) => {
    if (!cyInstance) return;
    
    // 保存实例引用
    setCy(cyInstance);
    
    try {
    // 配置节点拖拽
      cyInstance.nodes().ungrabify();
      cyInstance.nodes().grabify();
    
      // 添加拖拽事件处理
      cyInstance.on('dragfree', 'node', (evt) => {
        try {
          const node = evt.target;
          console.log(`Node ${node.id()} dragged to position:`, node.position());
        } catch (e) {
          console.warn('Drag event error:', e);
        }
      });
    } catch (e) {
      console.error('Cytoscape initialization error:', e);
    }
  };

  // 重写applyLayout函数
  const applyLayout = useCallback(() => {
    // 确保有效的cy实例
    if (!cy) return;
    
    try {
      // 避免在已销毁的实例上操作
      if (typeof cy.destroyed === 'function' && cy.destroyed()) {
        console.warn('Cannot apply layout: Cytoscape instance has been destroyed');
        return;
      }
      
      // 检查节点数量
      try {
        const nodes = cy.nodes();
        if (nodes.length === 0) {
          console.warn('No nodes to layout');
          return;
        }
        
        console.log(`Applying ${layout} layout to ${nodes.length} nodes`);
        
        // 特别处理layered布局
        if (layout === 'layered') {
          console.log('执行自定义layered布局');
          
          // 直接调用layered布局的run函数
          if (layouts.layered && typeof layouts.layered.run === 'function') {
            layouts.layered.run(cy);
          } else {
            console.error('layered布局的run函数不可用');
          }
        } else if (layout === 'random') {
          // 为random布局设置随机位置
          nodes.forEach((node) => {
            try {
              node.position({
                x: Math.random() * cy.width(),
                y: Math.random() * cy.height()
              });
            } catch (e) {
              console.warn('Random position setting error:', e);
            }
          });
        } else {
          // 对其他布局类型使用圆形排列
          try {
            // 创建并运行布局
            const layoutConfig = layouts[layout];
            const layoutInstance = cy.layout(layoutConfig);
            layoutInstance.run();
          } catch (e) {
            console.error('布局应用失败:', e);
            
            // 回退到手动圆形布局
            const centerX = cy.width() / 2;
            const centerY = cy.height() / 2;
            const radius = Math.min(cy.width(), cy.height()) * 0.35;
            
            // 直接设置节点位置
            nodes.forEach((node, i) => {
              try {
                const angle = (i / nodes.length) * 2 * Math.PI;
                node.position({
                  x: centerX + radius * Math.cos(angle),
                  y: centerY + radius * Math.sin(angle)
                });
              } catch (e) {
                console.warn(`Error positioning node ${i}:`, e);
              }
            });
          }
        }
        
        // 对于非layered布局，延迟fit和center操作
        if (layout !== 'layered') {
          setTimeout(() => {
            try {
              if (cy && typeof cy.destroyed === 'function' && !cy.destroyed()) {
                cy.fit();
                cy.center();
              }
            } catch (e) {
              console.warn('Fit/center failed:', e);
            }
          }, 200);
        }
      } catch (e) {
        console.warn('Node retrieval error:', e);
      }
    } catch (e) {
      console.error('Layout application error:', e);
    }
  }, [cy, layout]);

  // 添加加载状态显示
  const LoadingOverlay = () => {
    if (!loading) return null;
    return (
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'rgba(255, 255, 255, 0.8)',
          zIndex: 1000,
        }}
      >
        <CircularProgress />
      </Box>
    );
  };

  // 修改错误提示组件
  const ErrorMessage = () => {
    if (!error) return null;
    return (
      <Alert 
        severity="error" 
        sx={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          zIndex: 1000,
          minWidth: '300px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
        }}
      >
        {error}
      </Alert>
    );
  };

  const applyGraphPayload = (payload: ReturnType<typeof extractVisualization>, seedNodeId?: string | number | null) => {
    if (!payload) return false;
    setGraphData(toGraphData(payload, seedNodeId));
    return true;
  };

  const handleSearch = async () => {
    try {
      console.log("开始搜索...");
      setLoading(true);

      const parameter = parseInt(selectedParameter, 10) || 25;
      const query = searchQuery.trim();

      let response = await fetchInitialGraph(
        selectedDataset,
        selectedModel,
        selectedConstraint,
        parameter,
        query
      );
      console.log('完整的搜索响应:', response);

      let seedNodeId = response?.seed_node ?? response?.data?.seed_node ?? null;
      let visualizationData = extractVisualization(response);

      if (!visualizationData && query) {
        response = await fetchInitialGraph(
          selectedDataset,
          selectedModel,
          selectedConstraint,
          parameter,
          ''
        );
        seedNodeId = response?.seed_node ?? response?.data?.seed_node ?? null;
        visualizationData = extractVisualization(response);
      }

      if (applyGraphPayload(visualizationData, seedNodeId)) {
        setNotification({
          message: `加载成功 (${selectedModel}, ${visualizationData!.nodes.length} 节点, Parameter=${parameter})`,
          type: 'success'
        });
      } else {
        console.error('无效的响应格式:', response);
        setError(NETWORK_ERROR);
      }
    } catch (error) {
      console.error('搜索错误:', error);
      setError(NETWORK_ERROR);
    } finally {
      setLoading(false);
    }
  };

  const handleInsertNode = async (nodeId: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await insertNode(nodeId);
      if (applyGraphPayload(data as ReturnType<typeof extractVisualization>)) {
        setNotification({ message: `已添加节点 ${nodeId}`, type: 'success' });
      } else {
        setError(NETWORK_ERROR);
      }
    } catch (error) {
      console.error('Failed to insert node:', error);
      setError(NETWORK_ERROR);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteNode = async (nodeId: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await deleteNode(nodeId);
      if (applyGraphPayload(data as ReturnType<typeof extractVisualization>)) {
        setNotification({ message: `已删除节点 ${nodeId}`, type: 'success' });
      } else {
        setError(NETWORK_ERROR);
      }
    } catch (error) {
      console.error('Failed to delete node:', error);
      setError(NETWORK_ERROR);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = async () => {
    try {
      setLoading(true);
      await handleSearch();
    } catch (error) {
      console.error('搜索错误:', error);
      setLoading(false);
      setError(NETWORK_ERROR);
    }
  };
  
  // 添加测试可视化数据的函数
  const handleTestVisualization = async () => {
    try {
      console.log('开始测试可视化数据...');
      setLoading(true);
      const result = await testVisualization();
      console.log('测试可视化数据结果:', result);
      
      if (applyGraphPayload(extractVisualization(result))) {
        
        setNotification({
          message: '测试可视化数据加载成功',
          type: 'success'
        });
      } else {
        setError(NETWORK_ERROR);
      }
    } catch (error) {
      console.error('测试可视化数据错误:', error);
      setError(NETWORK_ERROR);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <Container maxWidth="xl" sx={{ py: 2 }}>
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 3
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
                src={publicAsset('hkbu_logo.jpg')} 
                alt="HKBU Logo" 
                style={{ 
                  height: '28px',
                  width: 'auto',
                  opacity: 0.9
                }} 
              />
              <Typography variant="subtitle1" sx={{ color: 'text.primary', fontSize: '1rem' }}>
                Hong Kong Baptist University
              </Typography>
            </Box>
            <Box sx={{ 
              display: 'flex', 
              alignItems: 'center',
              gap: 1
            }}>
              <img 
                src={publicAsset('tsinghua_logo.png')} 
                alt="清华大学 Tsinghua University" 
                style={{ 
                  height: '32px',
                  width: 'auto',
                  maxWidth: '200px',
                  objectFit: 'contain',
                  opacity: 0.95
                }} 
              />
              <Typography variant="subtitle1" sx={{ color: 'text.primary', fontSize: '1rem' }}>
                清华大学 · Tsinghua University
              </Typography>
            </Box>
          </Box>
        </Box>

        <Typography 
          variant="h4" 
          component="h1" 
          gutterBottom 
          sx={{ 
            textAlign: 'center',
            mb: 4,
            background: 'linear-gradient(45deg, #3498db 30%, #9b59b6 90%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            fontWeight: 500
          }}
        >
          Interactive Community Search System (GICS)
        </Typography>

        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} md={2}>
            <FormControl fullWidth>
              <InputLabel>Dataset</InputLabel>
              <Select
                value={selectedDataset}
                label="Dataset"
                onChange={(e) => setSelectedDataset(e.target.value)}
                sx={{
                  backgroundColor: 'white',
                  '&:hover': {
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  },
                }}
              >
                <MenuItem value="DBLP">Aminer</MenuItem>
                <MenuItem value="">DBLP</MenuItem>
                <MenuItem value="Amazon">Amazon</MenuItem>
                <MenuItem value="Youtube">Youtube</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={2}>
            <FormControl fullWidth>
              <InputLabel>Search Model</InputLabel>
              <Select
                value={selectedModel}
                label="Search Model"
                onChange={(e) => setSelectedModel(e.target.value)}
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
          
          <Grid item xs={12} md={2}>
            <FormControl fullWidth>
              <InputLabel>Constraint</InputLabel>
              <Select
                value={selectedConstraint}
                label="Constraint"
                onChange={(e) => setSelectedConstraint(e.target.value)}
                sx={{
                  backgroundColor: 'white',
                  '&:hover': {
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  },
                }}
              >
                <MenuItem value="Size k">Size k</MenuItem>
                <MenuItem value="Core k">Core k</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={1}>
            <FormControl fullWidth>
              <InputLabel>Parameter</InputLabel>
              <Select
                value={selectedParameter}
                label="Parameter"
                onChange={(e) => setSelectedParameter(e.target.value)}
                sx={{
                  backgroundColor: 'white',
                  '&:hover': {
                    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                  },
                }}
              >
                {[5, 10, 15, 20, 25, 30].map((value) => (
                  <MenuItem key={value} value={value.toString()}>{value}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={3}>
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
              onClick={handleSearchSubmit}
              sx={{ 
                height: '56px',
                background: loading ? '#1976d2' : 'linear-gradient(45deg, #3498db 30%, #9b59b6 90%)',
                '&:hover': { background: 'linear-gradient(45deg, #2980b9 30%, #8e44ad 90%)' },
                marginLeft: '8px', 
                fontSize: '1rem',
                color: 'white !important',
                fontWeight: 500,
                boxShadow: '0 3px 5px 2px rgba(52, 152, 219, 0.2)'
              }}
              disabled={loading || !searchQuery}
            >
              {loading ? 'Searching...' : 'Search'}
            </Button>
            
            {/* 测试按钮 */}
            
          </Grid>
        </Grid>

        <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
            <Typography variant="subtitle1" sx={{ color: 'text.secondary', whiteSpace: 'nowrap' }}>
              Layout:
            </Typography>
            <Tooltip title="Force-directed layout (may be slower)">
              <Chip
                label="Force"
                onClick={() => setLayout('cose')}
                clickable
                sx={{ 
                  backgroundColor: layout === 'cose' ? 'rgba(25, 118, 210, 0.15)' : 'white',
                  transition: 'all 0.2s',
                  '&:hover': {
                    backgroundColor: layout === 'cose' ? 'rgba(25, 118, 210, 0.25)' : 'rgba(25, 118, 210, 0.08)',
                  },
                }}
              />
            </Tooltip>
            <Tooltip title="Random layout (fastest)">
              <Chip
                label="Random"
                onClick={() => setLayout('random')}
                clickable
                sx={{ 
                  backgroundColor: layout === 'random' ? 'rgba(25, 118, 210, 0.15)' : 'white',
                  transition: 'all 0.2s',
                  '&:hover': {
                    backgroundColor: layout === 'random' ? 'rgba(25, 118, 210, 0.25)' : 'rgba(25, 118, 210, 0.08)',
                  },
                }}
              />
            </Tooltip>
            <Tooltip title="Grid layout">
              <Chip
                label="Grid"
                onClick={() => setLayout('grid')}
                clickable
                sx={{ 
                  backgroundColor: layout === 'grid' ? 'rgba(25, 118, 210, 0.15)' : 'white',
                  transition: 'all 0.2s',
                  '&:hover': {
                    backgroundColor: layout === 'grid' ? 'rgba(25, 118, 210, 0.25)' : 'rgba(25, 118, 210, 0.08)',
                  },
                }}
              />
            </Tooltip>
            <Tooltip title="Circle layout">
              <Chip
                label="Circle"
                onClick={() => setLayout('circle')}
                clickable
                sx={{ 
                  backgroundColor: layout === 'circle' ? 'rgba(25, 118, 210, 0.15)' : 'white',
                  transition: 'all 0.2s',
                  '&:hover': {
                    backgroundColor: layout === 'circle' ? 'rgba(25, 118, 210, 0.25)' : 'rgba(25, 118, 210, 0.08)',
                  },
                }}
              />
            </Tooltip>
            <Tooltip title="Concentric layout">
              <Chip
                label="Concentric"
                onClick={() => setLayout('concentric')}
                clickable
                sx={{ 
                  backgroundColor: layout === 'concentric' ? 'rgba(25, 118, 210, 0.15)' : 'white',
                  transition: 'all 0.2s',
                  '&:hover': {
                    backgroundColor: layout === 'concentric' ? 'rgba(25, 118, 210, 0.25)' : 'rgba(25, 118, 210, 0.08)',
                  },
                }}
              />
            </Tooltip>
            <Tooltip title="Tree layout">
              <Chip
                label="Tree"
                onClick={() => setLayout('breadthfirst')}
                clickable
                sx={{ 
                  backgroundColor: layout === 'breadthfirst' ? 'rgba(25, 118, 210, 0.15)' : 'white',
                  transition: 'all 0.2s',
                  '&:hover': {
                    backgroundColor: layout === 'breadthfirst' ? 'rgba(25, 118, 210, 0.25)' : 'rgba(25, 118, 210, 0.08)',
                  },
                }}
              />
            </Tooltip>
            <Tooltip title="Layered layout (Query in center)">
              <Chip
                label="Layered"
                onClick={() => {
                  setLayout('layered');
                  // 延迟一下再应用布局，确保layout状态已更新
                  setTimeout(() => {
                    if (cy && layouts.layered && typeof layouts.layered.run === 'function') {
                      console.log('直接调用layered布局函数');
                      layouts.layered.run(cy);
                    }
                  }, 50);
                }}
                clickable
                sx={{ 
                  backgroundColor: layout === 'layered' ? 'rgba(25, 118, 210, 0.15)' : 'white',
                  transition: 'all 0.2s',
                  '&:hover': {
                    backgroundColor: layout === 'layered' ? 'rgba(25, 118, 210, 0.25)' : 'rgba(25, 118, 210, 0.08)',
                  },
                }}
              />
            </Tooltip>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
            <Typography variant="subtitle1" sx={{ color: 'text.secondary', whiteSpace: 'nowrap' }}>
              Example Queries:
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {EXAMPLE_QUERIES.map((query, index) => (
                <Chip
                  key={index}
                  label={query}
                  onClick={() => setSearchQuery(query)}
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
              <LoadingOverlay />
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
                  <ZoomInIcon />
                </IconButton>
                <IconButton onClick={handleZoomOut} size="small">
                  <ZoomOutIcon />
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
                  elements={cytoscapeElements}
                  style={{ 
                    width: '100%', 
                    height: '100%',
                    backgroundColor: '#f5f5f5',
                    borderRadius: '8px'
                  }}
                  cy={(cy) => {
                    handleCyInit(cy)
                  }}
                  layout={layouts[layout]}
                  stylesheet={[
                    {
                      selector: 'node',
                      style: {
                        'background-color': (ele: NodeSingular) => {
                          const type = ele.data('type') as NodeType;
                          return COLORS[type] || COLORS.normal;
                        },
                        'label': (ele: NodeSingular) => {
                          const label = ele.data('label') || '';
                          const keywords = ele.data('keywords');
                          
                          if (keywords && Array.isArray(keywords) && keywords.length > 0) {
                            const topKeywords = keywords.slice(0, 2).join(',');
                            return `${label}\n(${topKeywords})`;
                          }
                          return label;
                        },
                        'text-wrap': 'wrap',
                        'text-max-width': '120px',
                        'font-size': '14px',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'width': 'label',
                        'height': 'label',
                        'padding': '15px',
                        'shape': 'ellipse',
                        'border-width': 2,
                        'border-color': '#fff',
                        'border-opacity': 0.8,
                        'text-margin-y': '5px'
                      }
                    },
                    {
                      selector: 'node[type="query"]',
                      style: {
                        'background-color': COLORS.query,
                        'border-width': 3,
                        'border-color': '#fff',
                        'font-weight': 'bold',
                        'font-size': '14px'
                      }
                    },
                    {
                      selector: 'node[type="insert"]',
                      style: {
                        'background-color': COLORS.insert,
                        'border-width': 2,
                        'border-color': '#fff'
                      }
                    },
                    {
                      selector: 'node[type="delete"]',
                      style: {
                        'background-color': COLORS.delete,
                        'border-width': 2,
                        'border-color': '#fff'
                      }
                    },
                    {
                      selector: 'node[type="community"]',
                      style: {
                        'background-color': COLORS.community,
                        'border-width': 2,
                        'border-color': '#fff'
                      }
                    },
                    {
                      selector: 'node:selected',
                      style: {
                        'border-width': 4,
                        'border-color': '#3498db',
                        'padding': '20px'
                      }
                    },
                    {
                      selector: 'edge',
                      style: {
                        'width': 1.5,
                        'line-color': (ele: EdgeSingular) => {
                          const type = ele.data('type') as EdgeType;
                          return COLORS.edges[type] || COLORS.edges.normal;
                        },
                        'curve-style': 'bezier',
                        'target-arrow-shape': 'none',
                        'opacity': 0.7
                      }
                    },
                    {
                      selector: 'edge[type="community"]',
                      style: {
                        'width': 2.5,
                        'line-color': COLORS.edges.community,
                        'opacity': 0.9
                      }
                    }
                  ]}
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
                sx={{ 
                  justifyContent: 'center',
                  width: '100%'
                }}
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
                {graphData?.recommendInsert?.map((nodeId: string) => {
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
                        onClick={() => handleInsertNode(nodeId)}
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
                {graphData?.recommendDelete?.map((nodeId: string) => {
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
                        onClick={() => handleDeleteNode(nodeId)}
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
          position: 'fixed',
          bottom: 20,
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          gap: 2
        }}>
          <Typography 
            variant="caption" 
            display="block" 
            align="center"
            sx={{ 
              color: 'text.secondary',
              opacity: 0.8
            }}
          >
            © 2026 Interactive Community Search System (GICS) · MIT License
          </Typography>
          <Typography 
            variant="caption" 
            component="a" 
            href="https://github.com/SunLongxu/GICS_demo" 
            target="_blank"
            sx={{ 
              color: 'text.secondary',
              textDecoration: 'none',
              display: 'flex',
              alignItems: 'center',
              gap: 0.5,
              opacity: 0.8,
              '&:hover': {
                color: 'primary.main',
                opacity: 1,
              },
            }}
          >
            <svg height="16" width="16" viewBox="0 0 16 16" style={{ fill: 'currentColor' }}>
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
            </svg>
            GitHub
          </Typography>
        </Box>
      </Container>
      <ErrorMessage />
    </ThemeProvider>
  )
}

export default App
