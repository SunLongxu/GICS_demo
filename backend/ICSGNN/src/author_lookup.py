"""作者名 → 节点 ID 解析（支持 list / dict / numpy.ndarray）。"""

from __future__ import annotations

from typing import Any, Iterable, Optional, Tuple


def _iter_authors(authorname: Any) -> Iterable[Tuple[int, str]]:
    if authorname is None:
        return
    if isinstance(authorname, dict):
        for node_id, author_name in authorname.items():
            yield int(node_id), str(author_name)
        return
    if hasattr(authorname, "__len__") and hasattr(authorname, "__getitem__"):
        for node_id in range(len(authorname)):
            yield node_id, str(authorname[node_id])


def find_author_node_id(
    authorname: Any,
    query: str,
    *,
    strict: bool = False,
) -> Optional[int]:
    """
    按优先级匹配作者：
    1. 全名精确匹配（忽略大小写）
    2. 查询各 token 均出现在作者名中（如 Jiawei + Han）
    3. 非 strict：查询字符串为作者名子串
    """
    name = (query or "").strip()
    if not name or authorname is None:
        return None

    name_l = name.lower()
    tokens = [t for t in name_l.split() if t]
    exact: list[int] = []
    token_hits: list[int] = []
    partial: list[int] = []

    for node_id, author_name in _iter_authors(authorname):
        an_l = author_name.lower()
        if an_l == name_l:
            exact.append(node_id)
            continue
        if len(tokens) >= 2 and all(token in an_l for token in tokens):
            token_hits.append(node_id)
            continue
        if not strict and name_l in an_l:
            partial.append(node_id)

    if exact:
        return int(exact[0])
    if token_hits:
        return int(token_hits[0])
    if partial:
        return int(partial[0])
    return None
