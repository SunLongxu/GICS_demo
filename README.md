# GICS (Interactive Community Search in Graphs)

GICS is an interactive community search system with real-time graph visualization for community search and refinement.

## Architecture

- **Frontend**: React + TypeScript + Vite + Cytoscape.js (`frontend/`)
- **Backend**: Flask + Socket.IO + ICSGNN (`backend/ICSGNN/`)

In development, the frontend proxies `/api`, `/test`, and `/socket.io` to the backend on port **5001**.

## Online Demo

- **前端 (GitHub Pages):** https://sunlongxu.github.io/GICS_demo/
- **后端 (Render):** 见 [DEPLOY.md](./DEPLOY.md) 部署 `gics-demo-api`

推送 `main`/`master` 后自动发布前端；API 失败时界面显示 `network error`。

## Quick Start

### 1. Backend

```bash
cd backend/ICSGNN
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run_api.py
```

Or from the repo root:

```bash
bash backend/start.sh
```

Verify: open [http://localhost:5001/test](http://localhost:5001/test) — you should see JSON `{"status":"success",...}`.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Click search / load graph; requests go to the backend via the Vite proxy.

### Environment (optional)

`frontend/.env.development`:

```env
VITE_API_BASE_URL=/api
VITE_WS_BASE_URL=
```

For production without a reverse proxy, set full URLs:

```env
VITE_API_BASE_URL=http://localhost:5001/api
VITE_WS_BASE_URL=http://localhost:5001
```

## API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/test` | GET | Health check |
| `/api/graph/initial` | GET | Initial subgraph visualization |
| `/api/search` | POST | Community search by author name (GNN / ACQ / WCS) |
| `/api/update` | POST | Refine community (positive/negative nodes) |
| `/api/graph/node/insert` | POST | Add node to community |
| `/api/graph/node/delete` | POST | Remove node from community |
| `/api/user_choice` | POST | Apply recommended insert/delete/confirm |
| `/api/lastvisualization` | GET | Last visualization payload |

WebSocket events: `visualization_update`, `state_update` (Socket.IO on port 5001).

### Search models (DBLP demo)

| Model | Description |
|-------|-------------|
| **GNN** | Structure BFS on the collaboration graph (ICSGNN pipeline) |
| **ACQ** | Attribute community query — expand by keyword similarity to the seed author |
| **WCS** | Weighted core search — keyword-filtered candidates, degree-weighted expansion |

Full Java ACQ/WCS batch experiments live under `backend/ACQ/` (requires separate Amazon index data and optional `WCS/` index module).

### Integration check

With the backend running:

```bash
bash scripts/check-integration.sh
```

## License

MIT License © 2024 GICS
