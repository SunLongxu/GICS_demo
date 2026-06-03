"""
社区搜索模型：GNN / ACQ / WCS 在 Demo API 中的实现。

- GNN: 结构 BFS（与 ICSGNN 图学习推荐管线配合的可视化子图）
- ACQ: 属性社区查询 — 优先扩展与查询节点关键词重叠高的邻居（对齐 ACQ Dec 思路）
- WCS: 加权核心搜索 — 先关键词过滤再连通扩展，邻居按度加权（对齐 BasicW 思路）
"""

from __future__ import annotations

import heapq
from collections import deque
from typing import Callable, Iterable, Set


def _keyword_set(get_keywords: Callable[[int], list], node: int) -> Set[str]:
    return {k.lower() for k in (get_keywords(node) or []) if k}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def expand_community_gnn(
    graph,
    query_node: int,
    community_size: int,
    eligible: Set[int],
    constraint: str,
) -> list:
    """结构 BFS 社区扩展。"""
    community_nodes = []
    queue = deque([query_node])
    visited = {query_node}

    while queue and len(community_nodes) < community_size:
        node = queue.popleft()
        if constraint == "Core k" and node not in eligible:
            continue
        community_nodes.append(node)
        for neighbor in graph.neighbors(node):
            if (
                neighbor not in visited
                and len(community_nodes) < community_size
                and (constraint != "Core k" or neighbor in eligible)
            ):
                visited.add(neighbor)
                queue.append(neighbor)
    return community_nodes


def expand_community_acq(
    graph,
    query_node: int,
    community_size: int,
    eligible: Set[int],
    constraint: str,
    get_keywords: Callable[[int], list],
) -> list:
    """
    ACQ 风格：在连通约束下优先加入与查询关键词相似度高的节点。
    """
    query_kw = _keyword_set(get_keywords, query_node)
    community = [query_node]
    frontier = {query_node}

    while len(community) < community_size and frontier:
        candidates = []
        for u in frontier:
            for v in graph.neighbors(u):
                if v in community:
                    continue
                if constraint == "Core k" and v not in eligible:
                    continue
                score = _jaccard(query_kw, _keyword_set(get_keywords, v))
                if graph.degree(v):
                    score += 0.05 * graph.degree(v)
                heapq.heappush(candidates, (-score, v))
        if not candidates:
            break
        added_any = False
        while candidates and len(community) < community_size:
            _, v = heapq.heappop(candidates)
            if v in community:
                continue
            community.append(v)
            frontier.add(v)
            added_any = True
            break
        if not added_any:
            break
        frontier = {community[-1]}

    if len(community) < community_size:
        extra = expand_community_gnn(
            graph, query_node, community_size, eligible, constraint
        )
        for n in extra:
            if n not in community:
                community.append(n)
            if len(community) >= community_size:
                break
    return community[:community_size]


def expand_community_wcs(
    graph,
    query_node: int,
    community_size: int,
    eligible: Set[int],
    constraint: str,
    get_keywords: Callable[[int], list],
) -> list:
    """
    WCS 风格：先关键词过滤候选集，再按邻居度加权 BFS。
    """
    query_kw = _keyword_set(get_keywords, query_node)
    if not query_kw:
        return expand_community_gnn(
            graph, query_node, community_size, eligible, constraint
        )

    def shares_keyword(node: int) -> bool:
        return bool(query_kw & _keyword_set(get_keywords, node))

    candidates = {query_node}
    hop_frontier = {query_node}
    for _ in range(3):
        next_hop = set()
        for u in hop_frontier:
            for v in graph.neighbors(u):
                if constraint == "Core k" and v not in eligible:
                    continue
                if shares_keyword(v):
                    candidates.add(v)
                    next_hop.add(v)
        hop_frontier = next_hop

    if len(candidates) < community_size:
        for u in list(candidates):
            for v in graph.neighbors(u):
                if constraint == "Core k" and v not in eligible:
                    continue
                candidates.add(v)

    community = [query_node]
    pq = []
    visited = {query_node}

    for v in graph.neighbors(query_node):
        if v in candidates and (constraint != "Core k" or v in eligible):
            heapq.heappush(pq, (-graph.degree(v), v))

    while pq and len(community) < community_size:
        _, v = heapq.heappop(pq)
        if v in visited:
            continue
        visited.add(v)
        community.append(v)
        for w in graph.neighbors(v):
            if w in visited or w not in candidates:
                continue
            if constraint == "Core k" and w not in eligible:
                continue
            heapq.heappush(pq, (-graph.degree(w), w))

    if len(community) < community_size:
        for n in expand_community_gnn(
            graph, query_node, community_size, eligible, constraint
        ):
            if n not in community:
                community.append(n)
            if len(community) >= community_size:
                break
    return community[:community_size]


def expand_community(
    model: str,
    graph,
    query_node: int,
    community_size: int,
    eligible: Iterable[int],
    constraint: str,
    get_keywords: Callable[[int], list],
) -> list:
    eligible_set = set(eligible)
    model_upper = (model or "GNN").upper()

    if model_upper == "ACQ":
        return expand_community_acq(
            graph, query_node, community_size, eligible_set, constraint, get_keywords
        )
    if model_upper == "WCS":
        return expand_community_wcs(
            graph, query_node, community_size, eligible_set, constraint, get_keywords
        )
    return expand_community_gnn(
        graph, query_node, community_size, eligible_set, constraint
    )
