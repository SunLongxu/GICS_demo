import { GraphData } from '../types/graph';
import { apiFetch, apiJson } from '../utils/apiRequest';
import { NETWORK_ERROR, toNetworkError } from '../utils/networkError';
import { io, Socket } from 'socket.io-client';

export { NETWORK_ERROR };

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:5001/api';
const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL ?? 'http://localhost:5001';
const defaultHeaders = {
  'Content-Type': 'application/json',
};

let socket: Socket | null = null;

const debugLog = (message: string, data?: unknown) => {
  console.log(`[DEBUG] ${message}`, data ?? '');
};

export async function testServerConnection() {
  try {
    const testUrl = API_BASE_URL.replace(/\/api\/?$/, '') + '/test';
    return await apiJson(testUrl, {
      method: 'GET',
      credentials: 'include',
      headers: defaultHeaders,
    });
  } catch (error) {
    console.error('Server test error:', error);
    throw toNetworkError();
  }
}

export const connectWebSocket = async (
  onMessage: (data: unknown) => void,
  onVisualizationUpdate?: (data: unknown) => void
) => {
  try {
    debugLog('Starting WebSocket connection process...');

    if (socket) {
      socket.disconnect();
    }

    if (!WS_BASE_URL) {
      socket = io({
        transports: ['websocket', 'polling'],
        withCredentials: true,
      });
    } else {
      socket = io(WS_BASE_URL, {
        transports: ['websocket', 'polling'],
        withCredentials: true,
      });
    }

    socket.on('message', (data) => onMessage(data));
    socket.on('state_update', (data) => onMessage(data));
    if (onVisualizationUpdate) {
      socket.on('visualization_update', onVisualizationUpdate);
    }

    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => reject(toNetworkError()), 5000);
      socket?.on('connect', () => {
        clearTimeout(timeout);
        resolve();
      });
      socket?.on('connect_error', () => {
        clearTimeout(timeout);
        reject(toNetworkError());
      });
    });

    return true;
  } catch (error) {
    debugLog('WebSocket connection error:', error);
    throw toNetworkError();
  }
};

export const disconnectWebSocket = () => {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
};

export const fetchInitialGraph = async (
  dataset: string = 'DBLP',
  model: string = 'GNN',
  constraint: string = 'Size k',
  parameter: number = 25,
  query: string = ''
) => {
  try {
    const params = new URLSearchParams({
      dataset,
      model,
      constraint,
      parameter: String(parameter),
    });
    if (query.trim()) {
      params.set('query', query.trim());
    }
    return await apiJson(
      `${API_BASE_URL}/graph/initial?${params.toString()}`,
      { method: 'GET', headers: defaultHeaders }
    );
  } catch (error) {
    console.error('Error fetching initial graph:', error);
    throw toNetworkError();
  }
};

export const searchCommunity = async (
  query: string,
  dataset: string = 'DBLP',
  model: string = 'GNN',
  constraint: string = 'Size k',
  parameter: number = 5
) => {
  try {
    const names = query.split(',').map((name) => name.trim()).filter(Boolean);
    if (names.length === 0) {
      throw toNetworkError();
    }

    return await apiJson(`${API_BASE_URL}/search`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({
        query: names[0],
        additional_names: names.slice(1),
        community_size: parameter,
        positive_nodes: [],
        negative_nodes: [],
        iteration: 0,
        dataset,
        model,
        constraint,
        parameter,
      }),
    });
  } catch (error) {
    console.error('查询社区错误:', error);
    throw toNetworkError();
  }
};

export const updateCommunity = async (
  positiveNodes: string[],
  negativeNodes: string[],
  iteration: number = 0
): Promise<unknown> => {
  try {
    return await apiJson(`${API_BASE_URL}/update`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({
        positive_nodes: positiveNodes,
        negative_nodes: negativeNodes,
        iteration,
      }),
    });
  } catch {
    throw toNetworkError();
  }
};

export const insertNode = async (nodeId: string): Promise<GraphData> => {
  try {
    const result = await apiJson<{ status: string; data: GraphData }>(
      `${API_BASE_URL}/graph/node/insert`,
      {
        method: 'POST',
        headers: defaultHeaders,
        body: JSON.stringify({ nodeId }),
      }
    );
    if (!result.data) {
      throw toNetworkError();
    }
    return result.data;
  } catch {
    throw toNetworkError();
  }
};

export const deleteNode = async (nodeId: string): Promise<GraphData> => {
  try {
    const result = await apiJson<{ status: string; data: GraphData }>(
      `${API_BASE_URL}/graph/node/delete`,
      {
        method: 'POST',
        headers: defaultHeaders,
        body: JSON.stringify({ nodeId }),
      }
    );
    if (!result.data) {
      throw toNetworkError();
    }
    return result.data;
  } catch {
    throw toNetworkError();
  }
};

export const testVisualization = async () => {
  try {
    return await apiJson(`${API_BASE_URL}/visualtest`, { method: 'GET' });
  } catch {
    throw toNetworkError();
  }
};

export const submitUserChoice = async (
  action: 'insert' | 'delete' | 'confirm' | 'none',
  nodeId: string | number | null = null
) => {
  try {
    return await apiJson(`${API_BASE_URL}/user_choice`, {
      method: 'POST',
      headers: defaultHeaders,
      body: JSON.stringify({ action, node_id: nodeId }),
    });
  } catch {
    throw toNetworkError();
  }
};

export const getLastVisualization = async () => {
  try {
    return await apiJson(`${API_BASE_URL}/lastvisualization`, { method: 'GET' });
  } catch {
    throw toNetworkError();
  }
};
