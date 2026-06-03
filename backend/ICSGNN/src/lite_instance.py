"""
Render / 低内存环境下的轻量图数据实例（不依赖 PyTorch / ICSGNN 训练管线）。
"""

from __future__ import annotations

import logging
import os.path as osp
import random
import traceback
from types import SimpleNamespace

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


def _data_dir():
    return osp.join(osp.dirname(osp.realpath(__file__)), "..", "data", "com_dblpname")


class LiteGraphInstance:
    """仅加载 DBLP 图与作者元数据，供 Demo API 可视化使用。"""

    def __init__(self):
        self.args = SimpleNamespace(
            data_set="dblpname",
            iteration=True,
            community_size=25,
        )
        self.graph = None
        self.features = None
        self.authorname = None
        self.keywords = None
        self.mapper = None
        self.current_community = []
        self.oldres = []
        self.oldpos = []
        self.recommender = None

    def load_dataset(self, dataset_name: str) -> bool:
        try:
            if self.graph is not None:
                return True
            if "dblp" not in dataset_name.lower():
                logger.error("Lite mode only supports DBLP")
                return False

            logger.info("LiteGraphInstance loading com_dblpname (numpy, no torch)...")
            path = _data_dir()
            edges = np.load(osp.join(path, "edges.npy"))
            self.graph = nx.from_edgelist(edges)
            del edges
            self.features = None
            self.authorname = np.load(
                osp.join(path, "auname.npy"), allow_pickle=True
            )
            self.keywords = np.load(
                osp.join(path, "keywords.npy"), allow_pickle=True
            )
            self.mapper = np.load(osp.join(path, "mapper.npy"), allow_pickle=True)
            self.current_community = []
            self.oldres = []
            logger.info(
                "LiteGraphInstance loaded %s nodes, %s edges",
                self.graph.number_of_nodes(),
                self.graph.number_of_edges(),
            )
            return True
        except Exception as e:
            logger.error("LiteGraphInstance load failed: %s", e)
            logger.error(traceback.format_exc())
            return False

    def get_initial_graph(self):
        try:
            if self.graph is None:
                return {"status": "error", "message": "图数据尚未加载"}

            node_count = self.graph.number_of_nodes()
            edge_count = self.graph.number_of_edges()
            sample_size = min(10, node_count)
            node_ids = list(self.graph.nodes())
            random_nodes = (
                random.sample(node_ids, sample_size) if len(node_ids) > sample_size else node_ids
            )

            sample_nodes = []
            for node in random_nodes:
                node_info = {
                    "id": int(node),
                    "name": self._author_label(node),
                    "keywords": [],
                }
                if isinstance(self.keywords, list) and node < len(self.keywords):
                    node_info["keywords"] = self.keywords[node]
                elif isinstance(self.keywords, dict) and node in self.keywords:
                    node_info["keywords"] = self.keywords[node]
                sample_nodes.append(node_info)

            return {
                "status": "success",
                "data": {
                    "statistics": {
                        "node_count": node_count,
                        "edge_count": edge_count,
                    },
                    "sample_nodes": sample_nodes,
                },
            }
        except Exception as e:
            logger.error("get_initial_graph failed: %s", e)
            return {"status": "error", "message": str(e)}

    def _author_label(self, node):
        if isinstance(self.authorname, list) and node < len(self.authorname):
            return self.authorname[node]
        if isinstance(self.authorname, dict) and node in self.authorname:
            return self.authorname[node]
        return f"Node {node}"

    def get_node_id_by_name(self, name, strict=False):
        try:
            if self.authorname is None:
                return None
            name_l = name.lower()
            if isinstance(self.authorname, list):
                for node_id, author_name in enumerate(self.authorname):
                    if name_l in str(author_name).lower():
                        return int(node_id)
                if not strict:
                    for node_id, author_name in enumerate(self.authorname):
                        if name.split()[0].lower() in str(author_name).lower():
                            return int(node_id)
            elif isinstance(self.authorname, dict):
                for node_id, author_name in self.authorname.items():
                    if name_l in str(author_name).lower():
                        return int(node_id)
            if strict:
                return None
            return 27436 if self.graph and self.graph.has_node(27436) else 0
        except Exception as e:
            logger.error("get_node_id_by_name: %s", e)
            return None

    def find_author_id(self, name):
        return self.get_node_id_by_name(name, strict=False)
