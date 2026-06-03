import logging
import os
import traceback
from flask import request, jsonify
from src.community_models import expand_community
from src.author_lookup import find_author_node_id
from collections import deque
import random

# 配置日志
logger = logging.getLogger(__name__)

# 全局变量存储ICSGNN实例
icsgnn_instance = None

def _lite_mode_enabled():
    return os.environ.get("GICS_LITE_MODE", "").lower() in ("1", "true", "yes")


def initialize_icsgnn():
    """
    初始化图服务实例。Render 等低内存环境使用 LiteGraphInstance（无 PyTorch）。
    """
    global icsgnn_instance
    try:
        if icsgnn_instance is not None:
            logger.info("Graph instance already initialized")
            return True

        if _lite_mode_enabled():
            from src.lite_instance import LiteGraphInstance

            logger.info("Initializing LiteGraphInstance (GICS_LITE_MODE)...")
            icsgnn_instance = LiteGraphInstance()
            if not icsgnn_instance.load_dataset("DBLP"):
                return False
            logger.info("LiteGraphInstance ready")
            return True

        from src.api_wrapper import ICSGNNWrapper

        logger.info("Initializing ICSGNN Wrapper...")
        icsgnn_instance = ICSGNNWrapper()

        if not hasattr(icsgnn_instance, "graph") or icsgnn_instance.graph is None:
            logger.info("Loading DBLP dataset...")
            icsgnn_instance.load_dataset("DBLP")
            logger.info("DBLP dataset loaded successfully")
        else:
            logger.info("Dataset already loaded, skipping...")

        if not hasattr(icsgnn_instance, "recommender") or icsgnn_instance.recommender is None:
            logger.info("Initializing recommender...")
            icsgnn_instance.initialize_recommender()
            logger.info("Successfully initialized recommender")
        else:
            logger.info("Recommender already initialized")

        logger.info("ICSGNN Wrapper initialized successfully")
        return True
    except Exception as e:
        logger.error("Failed to initialize graph instance: %s", e)
        logger.error(traceback.format_exc())
        return False

def _parse_size_parameter(parameter, default=25):
    try:
        return max(1, int(parameter))
    except (TypeError, ValueError):
        return default


def _apply_search_config(constraint, parameter):
    """将前端的 Constraint / Parameter 同步到 ICSGNN 实例。"""
    global icsgnn_instance
    size = _parse_size_parameter(parameter)
    constraint = constraint or "Size k"
    if icsgnn_instance is not None and hasattr(icsgnn_instance, "args"):
        icsgnn_instance.args.community_size = size
    return size, constraint


def _get_node_label(instance, node):
    if hasattr(instance, "authorname"):
        authorname = instance.authorname
        if isinstance(authorname, list) and node < len(authorname):
            return authorname[node]
        if isinstance(authorname, dict) and node in authorname:
            return authorname[node]
        if hasattr(authorname, "__getitem__") and hasattr(authorname, "__len__"):
            try:
                if 0 <= int(node) < len(authorname):
                    return str(authorname[int(node)])
            except (TypeError, ValueError, IndexError):
                pass
    return f"Node {node}"


def _get_node_keywords(instance, node):
    keywords = []
    try:
        if hasattr(instance, "keywords"):
            if isinstance(instance.keywords, dict) and node in instance.keywords:
                keywords_str = instance.keywords[node]
            elif isinstance(instance.keywords, list) and node < len(instance.keywords):
                keywords_str = instance.keywords[node]
            elif hasattr(instance.keywords, "__len__") and hasattr(
                instance.keywords, "__getitem__"
            ):
                idx = int(node)
                keywords_str = (
                    instance.keywords[idx] if 0 <= idx < len(instance.keywords) else None
                )
            else:
                keywords_str = None
            if isinstance(keywords_str, str):
                if "&" in keywords_str:
                    keywords = [kw.strip() for kw in keywords_str.split("&")]
                elif "," in keywords_str:
                    keywords = [kw.strip() for kw in keywords_str.split(",")]
                else:
                    keywords = [keywords_str.strip()]
    except Exception:
        keywords = []
    return keywords or []


def _build_parameterized_visualization(
    instance,
    query_node,
    community_size,
    constraint,
    use_demo_extras=False,
    model="GNN",
):
    """
    围绕 query_node 构建可视化子图，社区规模由 parameter (community_size) 控制。
    model: GNN | ACQ | WCS
    """
    import random
    from collections import deque

    graph = instance.graph
    eligible_nodes = _eligible_nodes_for_constraint(graph, constraint, community_size)
    recommend_cap = max(1, min(5, community_size // 5))
    normal_ring_size = community_size

    if constraint == "Core k" and query_node not in eligible_nodes:
        logger.warning(
            "Query node %s not in %s-core; visualization may be sparse",
            query_node,
            community_size,
        )

    community_nodes = expand_community(
        model,
        graph,
        query_node,
        community_size,
        eligible_nodes,
        constraint,
        lambda n: _get_node_keywords(instance, n),
    )
    logger.info("Model %s expanded community to %s nodes", model, len(community_nodes))

    if use_demo_extras:
        ameet_talwalkar_id = 63258
        if ameet_talwalkar_id not in community_nodes:
            community_nodes.append(ameet_talwalkar_id)
            logger.info("Added Ameet Talwalkar (ID: %s) to community nodes", ameet_talwalkar_id)

    eligible_for_delete = [n for n in community_nodes if n != query_node]
    recommend_delete_nodes = random.sample(
        eligible_for_delete,
        min(recommend_cap, len(eligible_for_delete)),
    )

    if use_demo_extras:
        ameet_talwalkar_id = 63258
        if ameet_talwalkar_id not in recommend_delete_nodes:
            recommend_delete_nodes.append(ameet_talwalkar_id)

    real_community_nodes = [
        n for n in community_nodes
        if n not in recommend_delete_nodes and n != query_node
    ]

    normal_nodes = []
    bfs_queue = deque(community_nodes.copy())
    all_visited = set(community_nodes)

    while bfs_queue and len(normal_nodes) < normal_ring_size:
        node = bfs_queue.popleft()
        for neighbor in graph.neighbors(node):
            if neighbor not in all_visited and (
                constraint != "Core k" or neighbor in eligible_nodes
            ):
                all_visited.add(neighbor)
                normal_nodes.append(neighbor)
                if len(normal_nodes) < normal_ring_size:
                    bfs_queue.append(neighbor)
                else:
                    break

    eligible_for_insert = [n for n in normal_nodes if n != query_node]
    recommend_insert_nodes = random.sample(
        eligible_for_insert,
        min(recommend_cap, len(eligible_for_insert)),
    )
    real_normal_nodes = [n for n in normal_nodes if n not in recommend_insert_nodes]

    all_relevant_nodes = (
        [query_node]
        + real_community_nodes
        + recommend_insert_nodes
        + real_normal_nodes
        + recommend_delete_nodes
    )
    full_subgraph = graph.subgraph(all_relevant_nodes)

    nodes = [{
        "id": str(query_node),
        "label": _get_node_label(instance, query_node),
        "type": "query",
        "keywords": _get_node_keywords(instance, query_node),
    }]
    for node in real_community_nodes:
        nodes.append({
            "id": str(node),
            "label": _get_node_label(instance, node),
            "type": "community",
            "keywords": _get_node_keywords(instance, node),
        })
    for node in recommend_insert_nodes:
        nodes.append({
            "id": str(node),
            "label": _get_node_label(instance, node),
            "type": "insert",
            "keywords": _get_node_keywords(instance, node),
        })
    for node in real_normal_nodes:
        nodes.append({
            "id": str(node),
            "label": _get_node_label(instance, node),
            "type": "normal",
            "keywords": _get_node_keywords(instance, node),
        })
    for node in recommend_delete_nodes:
        nodes.append({
            "id": str(node),
            "label": _get_node_label(instance, node),
            "type": "delete",
            "keywords": _get_node_keywords(instance, node),
        })

    edges = []
    for u, v in full_subgraph.edges():
        edge_type = "normal"
        if (
            (u == query_node or u in real_community_nodes)
            and (v == query_node or v in real_community_nodes)
        ):
            edge_type = "community"
        edges.append({"source": str(u), "target": str(v), "type": edge_type})

    visualization = {
        "nodes": nodes,
        "edges": edges,
        "recommendInsert": [str(node) for node in recommend_insert_nodes],
        "recommendDelete": [str(node) for node in recommend_delete_nodes],
    }

    all_community_nodes = [query_node] + real_community_nodes + recommend_delete_nodes
    instance.current_community = all_community_nodes
    instance.oldres = all_community_nodes
    instance.oldpos = [query_node]

    return visualization, query_node


def _resolve_query_node(instance, query_name=None, default=27484):
    """解析查询作者；找不到时回退到模糊匹配或默认种子，保证 Demo 总有结果。"""
    if query_name and str(query_name).strip():
        name = str(query_name).strip()
        authorname = getattr(instance, "authorname", None)

        node_id = find_author_node_id(authorname, name, strict=True)
        if node_id is not None:
            return int(node_id)

        node_id = find_author_node_id(authorname, name, strict=False)
        if node_id is not None:
            logger.info("Fuzzy name match for query '%s' -> %s", name, node_id)
            return int(node_id)

        if hasattr(instance, "get_node_id_by_name"):
            node_id = instance.get_node_id_by_name(name, strict=True)
            if node_id is not None:
                return int(node_id)
            node_id = instance.get_node_id_by_name(name, strict=False)
            if node_id is not None:
                logger.info("Wrapper name match for query '%s' -> %s", name, node_id)
                return int(node_id)

        logger.warning("Author not found for query '%s', using default seed %s", name, default)
        return int(default)
    return int(default)


def _eligible_nodes_for_constraint(graph, constraint, k):
    import networkx as nx

    if constraint == "Core k" and k > 0:
        try:
            return set(nx.k_core(graph, k=k).nodes())
        except nx.NetworkXError:
            logger.warning("k-core k=%s unavailable, falling back to full graph", k)
    return set(graph.nodes())


def _extract_visualization_emit_payload(data):
    """从回调/存储结构中提取可通过 WebSocket 推送的可视化数据。"""
    vis_content = None
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], dict):
            inner = data["data"]
            if "nodes" in inner:
                vis_content = inner
            elif "visualization" in inner:
                vis_content = inner["visualization"]
        elif "nodes" in data:
            vis_content = data
        elif "visualization" in data:
            vis_content = data["visualization"]
    if not vis_content:
        return None
    return {
        "status": "success",
        "nodes": vis_content.get("nodes", []),
        "edges": vis_content.get("edges", []),
        "recommendInsert": vis_content.get("recommendInsert", []),
        "recommendDelete": vis_content.get("recommendDelete", []),
    }


def _sync_instance_to_app(app, instance=None):
    global icsgnn_instance
    inst = instance or icsgnn_instance
    if inst is not None:
        icsgnn_instance = inst
        app.config["ICSGNN_INSTANCE"] = inst


def register_routes(app, socketio=None):
    """
    注册API路由到Flask应用
    """

    @app.before_request
    def _bind_icsgnn_to_app():
        if icsgnn_instance is not None:
            app.config["ICSGNN_INSTANCE"] = icsgnn_instance

    def emit_visualization_update(data):
        if socketio is None:
            return
        payload = _extract_visualization_emit_payload(data)
        if payload is None:
            return
        try:
            socketio.emit("visualization_update", payload)
            logger.info(
                "Emitted visualization_update with %s nodes",
                len(payload.get("nodes", [])),
            )
        except Exception as e:
            logger.error("Failed to emit visualization_update: %s", e)

    def handle_state_update(state):
        try:
            logger.debug("State update: %s", state)
            if socketio is not None:
                socketio.emit("state_update", state)
            emit_visualization_update(state)
        except Exception as e:
            logger.error("Error handling state update: %s", e)
    
    @app.route('/api/graph/initial', methods=['GET'])
    def get_initial_graph():
        """
        Get initial graph data for visualization
        """
        try:
            # Get query parameters
            dataset = request.args.get('dataset', 'DBLP')
            model = request.args.get('model', 'GNN')
            constraint = request.args.get('constraint', 'Size k')
            parameter = request.args.get('parameter', request.args.get('community_size', '25'))
            query_name = request.args.get('query', '')
            if query_name and "," in query_name:
                query_name = query_name.split(",")[0].strip()
            community_size, constraint = _apply_search_config(constraint, parameter)
            logger.info(
                "get_initial_graph: constraint=%s, community_size=%s, query=%s",
                constraint,
                community_size,
                query_name or "(default)",
            )
            
            model_upper = (model or "GNN").upper()
            supported_models = {"GNN", "ACQ", "WCS"}

            if dataset == 'DBLP' and model_upper in supported_models:
                # Ensure ICSGNN instance is initialized
                if not initialize_icsgnn():
                    return jsonify({
                        "status": "error",
                        "message": "Failed to initialize ICSGNN Wrapper"
                    }), 500
                
                # Get initial graph data for statistics
                stats_result = icsgnn_instance.get_initial_graph()
                if stats_result["status"] != "success":
                    return jsonify({
                        "status": "error",
                        "message": stats_result.get("message", "Failed to load initial graph")
                    }), 500
                
                # 创建增强的初始化可视化数据
                if hasattr(icsgnn_instance, 'graph') and icsgnn_instance.graph is not None:
                    try:
                        use_demo_extras = not bool(query_name and str(query_name).strip())
                        query_node = _resolve_query_node(
                            icsgnn_instance, query_name, default=27484
                        )
                        logger.info("Using query node: %s", query_node)

                        visualization, query_node = _build_parameterized_visualization(
                            icsgnn_instance,
                            query_node,
                            community_size,
                            constraint,
                            use_demo_extras=use_demo_extras,
                            model=model_upper,
                        )

                        return jsonify({
                            "status": "success",
                            "data": {
                                "statistics": stats_result["data"]["statistics"],
                                "sample_nodes": stats_result["data"]["sample_nodes"],
                                "visualization": visualization,
                                "seed_node": query_node,
                                "model": model_upper,
                            },
                            "seed_node": query_node,
                            "model": model_upper,
                        })
                    except Exception as viz_error:
                        logger.error(f"Error creating visualization: {str(viz_error)}")
                        logger.error(traceback.format_exc())
                        return jsonify(stats_result)  # Return at least the statistics if visualization fails
                
                # Return original result if graph is not available
                return jsonify(stats_result)
            else:
                return jsonify({
                    "status": "error",
                    "message": (
                        f"Unsupported dataset/model: {dataset}/{model}. "
                        "Demo supports DBLP with GNN, ACQ, or WCS."
                    ),
                }), 400
                
        except Exception as e:
            logger.error(f"Error in get_initial_graph: {str(e)}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

    @app.route('/api/search', methods=['POST'])
    def search_community_api():
        """
        Search for communities based on a query
        """
        try:
            if _lite_mode_enabled():
                return jsonify({
                    "status": "error",
                    "message": "Full GNN search is disabled in lite mode; use GET /api/graph/initial instead.",
                }), 501

            # Get query parameters
            data = request.get_json()
            query = data.get('query')
            additional_names = data.get('additional_names', [])
            dataset = data.get('dataset', 'DBLP')
            model = data.get('model', 'GNN')
            constraint = data.get('constraint', 'Size k')
            parameter = data.get('parameter', data.get('community_size', 30))
            community_size, constraint = _apply_search_config(constraint, parameter)

            app.logger.info(
                "Received search request: query=%s, dataset=%s, model=%s, "
                "constraint=%s, community_size=%s",
                query,
                dataset,
                model,
                constraint,
                community_size,
            )
            
            if not query:
                return jsonify({
                    'status': 'error',
                    'message': 'Query parameter is required'
                }), 400
            
            # Initialize ICSGNN if not already done
            global icsgnn_instance
            if not initialize_icsgnn():
                return jsonify({
                    'status': 'error', 
                    'message': 'Failed to initialize ICSGNN'
                }), 500
            _sync_instance_to_app(app)

            if query and "," in query:
                query = query.split(",")[0].strip()

            model_upper = (model or "GNN").upper()

            # Demo 快速路径：按 model + parameter 构建子图
            if dataset == 'DBLP' and model_upper in ('GNN', 'ACQ', 'WCS'):
                query_node = _resolve_query_node(icsgnn_instance, query)

                positive_ids = [query_node]
                for name in additional_names or []:
                    extra_id = _resolve_query_node(icsgnn_instance, name)
                    if extra_id is not None and extra_id not in positive_ids:
                        positive_ids.append(extra_id)
                icsgnn_instance.oldpos = positive_ids

                visualization, query_node = _build_parameterized_visualization(
                    icsgnn_instance,
                    query_node,
                    community_size,
                    constraint,
                    use_demo_extras=False,
                    model=model_upper,
                )
                emit_visualization_update({'data': visualization})
                app.config['LAST_VISUALIZATION'] = {'data': visualization}

                response_data = {
                    'status': 'success',
                    'nodes': visualization['nodes'],
                    'edges': visualization['edges'],
                    'recommendInsert': visualization['recommendInsert'],
                    'recommendDelete': visualization['recommendDelete'],
                    'seed_node': query_node,
                    'model': model_upper,
                    'data': {
                        'visualization': visualization,
                        'seed_node': query_node,
                        'model': model_upper,
                    },
                }
                response = jsonify(response_data)
                response.headers.add('Access-Control-Allow-Origin', '*')
                return response, 200
            
            # 直接操作recommender
            # 1. 如果不存在，先初始化recommender
            if not hasattr(icsgnn_instance, 'recommender') or icsgnn_instance.recommender is None:
                app.logger.info("Creating new recommender instance")
                from src.recommend import PPRRecommend
                icsgnn_instance.recommender = PPRRecommend(icsgnn_instance.args, icsgnn_instance)
            
            # 2. 定义并设置回调函数
            def visualization_callback(data):
                app.logger.info("\n===== 调试: visualization_callback被调用 =====")
                app.logger.info(f"接收到可视化数据结构类型: {type(data).__name__}")
                data_keys = list(data.keys()) if isinstance(data, dict) else "非字典结构"
                app.logger.info(f"顶层键: {data_keys}")
                
                if isinstance(data, dict) and 'data' in data:
                    inner_keys = list(data['data'].keys()) if isinstance(data['data'], dict) else "非字典结构"
                    app.logger.info(f"data字段内的键: {inner_keys}")
                
                # 确保每个节点都有关键词
                if 'data' in data and 'nodes' in data['data']:
                    nodes_count = len(data['data']['nodes'])
                    app.logger.info(f"处理{nodes_count}个节点的关键词数据...")
                    
                    # 处理前检查关键词状态
                    nodes_with_keywords_before = sum(1 for node in data['data']['nodes'] if 'keywords' in node and node['keywords'])
                    app.logger.info(f"处理前，有{nodes_with_keywords_before}个节点包含关键词")
                    
                    # 处理节点关键词
                    processed_nodes = 0
                    added_keywords = 0
                    
                    for node in data['data']['nodes']:
                        node_id = None
                        try:
                            # 将节点ID转换为整数，因为大多数API都使用整数ID
                            node_id = int(node['id'])
                            processed_nodes += 1
                            
                            # 确保每个节点都有keywords字段
                            if 'keywords' not in node or not node['keywords']:
                                # 尝试从icsgnn_instance获取关键词
                                if hasattr(icsgnn_instance, 'keywords'):
                                    if isinstance(icsgnn_instance.keywords, dict) and node_id in icsgnn_instance.keywords:
                                        keyword_str = icsgnn_instance.keywords[node_id]
                                        if isinstance(keyword_str, str):
                                            if "&" in keyword_str:
                                                node['keywords'] = [kw.strip() for kw in keyword_str.split("&")]
                                                added_keywords += 1
                                            elif "," in keyword_str:
                                                node['keywords'] = [kw.strip() for kw in keyword_str.split(",")]
                                                added_keywords += 1
                                            else:
                                                node['keywords'] = [keyword_str.strip()]
                                                added_keywords += 1
                                        else:
                                            node['keywords'] = []
                                    else:
                                        # 如果找不到关键词，用空数组
                                        node['keywords'] = []
                        except Exception as e:
                            app.logger.error(f"处理节点{node_id}关键词时出错: {str(e)}")
                    
                    # 处理后检查关键词状态
                    nodes_with_keywords_after = sum(1 for node in data['data']['nodes'] if 'keywords' in node and node['keywords'])
                    app.logger.info(f"处理了{processed_nodes}个节点，添加了{added_keywords}个关键词")
                    app.logger.info(f"处理后，有{nodes_with_keywords_after}个节点包含关键词")
                    
                    # 输出示例节点
                    if nodes_count > 0:
                        sample_node = data['data']['nodes'][0]
                        app.logger.info(f"节点示例: ID={sample_node.get('id')}, 标签={sample_node.get('label')}, 关键词={sample_node.get('keywords')}")
                
                # 存储可视化数据并推送到前端
                app.logger.info("将可视化数据存储到app.config['LAST_VISUALIZATION']")
                app.config['LAST_VISUALIZATION'] = data
                emit_visualization_update(data)
                app.logger.info("===== 调试: visualization_callback处理完成 =====\n")
                return data
                
            # 直接设置状态回调
            icsgnn_instance.set_state_callback(visualization_callback)
            app.logger.info(f"状态回调已设置到icsgnn_instance")
            
            # 确保回调设置正确
            if not hasattr(icsgnn_instance, 'state_callback') or icsgnn_instance.state_callback is None:
                app.logger.error("未能设置状态回调函数!")
                # 再次尝试设置
                icsgnn_instance.set_state_callback(visualization_callback)
                app.logger.info(f"重试设置状态回调: {icsgnn_instance.state_callback is not None}")
            
            # 调试关键词加载情况
            app.logger.info("调试keywords属性...")
            icsgnn_instance.debug_keywords()
            
            # 检查关键词是否正确加载
            if hasattr(icsgnn_instance, 'keywords'):
                keywords_type = type(icsgnn_instance.keywords).__name__
                app.logger.info(f"icsgnn_instance.keywords类型: {keywords_type}")
                
                if isinstance(icsgnn_instance.keywords, dict):
                    key_count = len(icsgnn_instance.keywords)
                    app.logger.info(f"keywords字典中有{key_count}个条目")
                    
                    # 检查几个特定的节点
                    test_node = 0
                    if test_node in icsgnn_instance.keywords:
                        app.logger.info(f"节点{test_node}的关键词: {icsgnn_instance.keywords[test_node]}")
                    else:
                        app.logger.info(f"节点{test_node}不在keywords字典中")
                elif isinstance(icsgnn_instance.keywords, list):
                    app.logger.info(f"keywords列表长度: {len(icsgnn_instance.keywords)}")
                    
                    # 检查第一个节点
                    if len(icsgnn_instance.keywords) > 0:
                        app.logger.info(f"第一个节点的关键词: {icsgnn_instance.keywords[0]}")
            else:
                app.logger.error("icsgnn_instance没有keywords属性!")
            
            # 查找作者ID
            # 检查icsgnn_instance是否有get_node_id_by_name方法，这是原始API中应该有的方法
            if hasattr(icsgnn_instance, 'get_node_id_by_name'):
                author_id = icsgnn_instance.get_node_id_by_name(query)
            # 如果没有get_node_id_by_name方法，尝试使用find_author_id方法
            elif hasattr(icsgnn_instance, 'find_author_id'):
                author_id = icsgnn_instance.find_author_id(query)
            # 如果都没有，检查authorname属性是否存在并尝试手动查找
            elif hasattr(icsgnn_instance, 'authorname'):
                author_id = None
                authorname = icsgnn_instance.authorname
                # 如果authorname是字典类型
                if isinstance(authorname, dict):
                    for node_id, name in authorname.items():
                        if name.lower() == query.lower():
                            author_id = node_id
                            break
                # 如果authorname是列表类型
                elif isinstance(authorname, list):
                    for i, name in enumerate(authorname):
                        if name.lower() == query.lower():
                            author_id = i
                            break
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Cannot find author ID, no suitable method available'
                }), 500
            
            if author_id is None:
                return jsonify({
                    'status': 'error',
                    'message': 'Author not found'
                }), 404
            
            app.logger.info(f"Found author ID: {author_id} for query: {query}")
            
            # 处理额外的作者名称作为positive nodes
            positive_ids = []
            if additional_names and len(additional_names) > 0:
                app.logger.info(f"Processing additional names: {additional_names}")
                for name in additional_names:
                    node_id = None
                    if hasattr(icsgnn_instance, 'get_node_id_by_name'):
                        node_id = icsgnn_instance.get_node_id_by_name(name)
                    elif hasattr(icsgnn_instance, 'authorname'):
                        authorname = icsgnn_instance.authorname
                        if isinstance(authorname, dict):
                            for id, author_name in authorname.items():
                                if author_name.lower() == name.lower():
                                    node_id = id
                                    break
                        elif isinstance(authorname, list):
                            for i, author_name in enumerate(authorname):
                                if author_name.lower() == name.lower():
                                    node_id = i
                                    break
                    
                    if node_id is not None:
                        positive_ids.append(node_id)
                        app.logger.info(f"Added additional author: {name} (ID: {node_id})")
            
            # 确保主查询节点也在正样本列表中
            if author_id not in positive_ids:
                positive_ids.append(author_id)
            
            # 设置到实例中
            icsgnn_instance.oldpos = positive_ids
            app.logger.info(f"Final positive IDs: {positive_ids}")
            
            # Perform community search
            app.logger.info(f"Searching community with seed: {author_id}")
            community = icsgnn_instance.search_community(author_id)
            
            if not community or (isinstance(community, dict) and community.get("status") != "success"):
                error_msg = "Failed to find community"
                if isinstance(community, dict) and "message" in community:
                    error_msg = community["message"]
                return jsonify({
                    'status': 'error',
                    'message': error_msg
                }), 500
            
            # 提取社区数据
            if isinstance(community, dict) and "data" in community and "community" in community["data"]:
                community_nodes = community["data"]["community"]
            else:
                community_nodes = community
            
            # 保存到实例中
            icsgnn_instance.current_community = community_nodes
            icsgnn_instance.oldres = community_nodes
            
            # 获取可视化数据
            app.logger.info("\n===== 调试: 从app.config获取可视化数据 =====")
            visualization_data = app.config.get('LAST_VISUALIZATION', {})
            
            # 检查获取的数据
            if not visualization_data:
                app.logger.warning("警告: 没有可视化数据可用 (app.config['LAST_VISUALIZATION']为空)")
            else:
                app.logger.info(f"成功获取到可视化数据，数据类型: {type(visualization_data).__name__}")
                # 检查可视化数据结构
                if isinstance(visualization_data, dict):
                    top_keys = list(visualization_data.keys())
                    app.logger.info(f"可视化数据顶层键: {top_keys}")
                    
                    if 'data' in visualization_data:
                        data_keys = list(visualization_data['data'].keys()) if isinstance(visualization_data['data'], dict) else "非字典结构"
                        app.logger.info(f"可视化数据['data']内的键: {data_keys}")
                        
                        # 检查是否包含必要节点数据
                        if isinstance(visualization_data['data'], dict) and 'nodes' in visualization_data['data']:
                            nodes = visualization_data['data']['nodes']
                            nodes_count = len(nodes)
                            app.logger.info(f"节点数量: {nodes_count}")
                            
                            # 检查关键词情况
                            nodes_with_keywords = sum(1 for node in nodes if 'keywords' in node and node['keywords'])
                            app.logger.info(f"有关键词的节点: {nodes_with_keywords}/{nodes_count}")
                            
                            if nodes_count > 0:
                                sample_node = nodes[0]
                                app.logger.info(f"节点示例: ID={sample_node.get('id')}, 关键词={sample_node.get('keywords', '无关键词')}")
            
            # 构建API响应
            app.logger.info("\n===== 调试: 构建API响应 =====")
            
            # 准备返回数据
            result_nodes = []
            for node in community_nodes:
                node_info = {"id": node}
                
                # 添加名称
                if hasattr(icsgnn_instance, 'authorname'):
                    if isinstance(icsgnn_instance.authorname, dict) and node in icsgnn_instance.authorname:
                        node_info["name"] = icsgnn_instance.authorname[node]
                    elif isinstance(icsgnn_instance.authorname, list) and node < len(icsgnn_instance.authorname):
                        node_info["name"] = icsgnn_instance.authorname[node]
                    else:
                        node_info["name"] = f"Node {node}"
                
                # 添加关键词
                if hasattr(icsgnn_instance, 'keywords'):
                    keywords = []
                    try:
                        if isinstance(icsgnn_instance.keywords, dict) and node in icsgnn_instance.keywords:
                            keyword_str = icsgnn_instance.keywords[node]
                            if isinstance(keyword_str, str):
                                if "&" in keyword_str:
                                    keywords = [kw.strip() for kw in keyword_str.split("&")]
                                elif "," in keyword_str:
                                    keywords = [kw.strip() for kw in keyword_str.split(",")]
                                else:
                                    keywords = [keyword_str.strip()]
                            else:
                                keywords = []
                    except Exception as e:
                        app.logger.error(f"Error processing keywords for node {node}: {str(e)}")
                    
                    node_info["keywords"] = keywords
                
                result_nodes.append(node_info)
            
            # 直接将可视化数据作为主要响应内容
            if visualization_data and 'data' in visualization_data:
                visualization_content = visualization_data['data']
                # 添加社区信息到可视化数据
                visualization_content['community'] = result_nodes
                visualization_content['community_size'] = len(community_nodes) if community_nodes else 0
                visualization_content['seed_node'] = author_id
                
                # 使用更简单的响应结构
                response_data = {
                    'status': 'success',
                    'nodes': visualization_content.get('nodes', []),
                    'edges': visualization_content.get('edges', []),
                    'recommendInsert': visualization_content.get('recommendInsert', []),
                    'recommendDelete': visualization_content.get('recommendDelete', []),
                    'community': result_nodes,
                    'seed_node': author_id
                }
            else:
                # 如果没有可视化数据，至少返回社区信息
                response_data = {
                    'status': 'success',
                    'nodes': [],
                    'edges': [],
                    'recommendInsert': [],
                    'recommendDelete': [],
                    'community': result_nodes,
                    'seed_node': author_id
                }
            
            # 记录返回数据结构
            app.logger.info(f"简化后的API响应顶层键: {list(response_data.keys())}")
            app.logger.info(f"API响应中nodes数量: {len(response_data.get('nodes', []))}")
            app.logger.info(f"API响应中edges数量: {len(response_data.get('edges', []))}")
            app.logger.info("===== 调试: API响应构建完成 =====\n")
            
            # 设置CORS头
            response = jsonify(response_data)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response, 200
            
        except Exception as e:
            app.logger.error(f"Error in search_community_api: {str(e)}")
            traceback.print_exc()
            return jsonify({
                'status': 'error',
                'message': f'Error processing search: {str(e)}'
            }), 500

    @app.route('/api/update', methods=['POST'])
    def update_community():
        """
        处理社区更新请求
        """
        try:
            if not initialize_icsgnn():
                return jsonify({"status": "error", "message": "Failed to initialize ICSGNN"}), 500
            _sync_instance_to_app(app)

            data = request.get_json() or {}
            positive_nodes = data.get('positive_nodes', [])
            negative_nodes = data.get('negative_nodes', [])
            iteration = data.get('iteration', 0)

            icsgnn_instance.set_state_callback(handle_state_update)

            result = icsgnn_instance.update_community(
                positive_nodes=positive_nodes,
                negative_nodes=negative_nodes,
                iteration=iteration,
            )

            if "error" in result:
                return jsonify({"status": "error", "message": result["error"]}), 400

            query_node = (
                icsgnn_instance.oldpos[0]
                if getattr(icsgnn_instance, "oldpos", None)
                else (icsgnn_instance.current_community[0] if icsgnn_instance.current_community else 27484)
            )
            community_size = getattr(icsgnn_instance.args, "community_size", 25)
            visualization, query_node = _build_parameterized_visualization(
                icsgnn_instance,
                query_node,
                community_size,
                "Size k",
                use_demo_extras=False,
                model="GNN",
            )
            emit_visualization_update({"data": visualization})

            return jsonify({
                "status": "success",
                "data": visualization,
                "seed_node": query_node,
                "community": result,
            })

        except Exception as e:
            logger.error("update_community error: %s", e)
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.route('/api/recommend', methods=['POST'])
    def recommend_nodes():
        """
        处理节点推荐请求
        """
        try:
            data = request.get_json()
            current_community = data.get('current_community', [])
            num_recommendations = data.get('num_recommendations', 10)

            if not current_community:
                return jsonify({"error": "current_community is required"}), 400

            # 获取推荐节点
            recommended_nodes = icsgnn_instance.recommender.ppr_algo(
                tag="recommend",
                allResNodes=current_community,
                allNodes=list(icsgnn_instance.graph.nodes())
            )

            # 格式化推荐结果
            recommendations = [{
                "id": node,
                "name": icsgnn_instance.authorname[node],
                "keywords": icsgnn_instance.keywords[node]
            } for node in recommended_nodes[:num_recommendations]]

            return jsonify({
                "recommendations": recommendations,
                "count": len(recommendations)
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/graph/visualization', methods=['GET'])
    def get_graph_visualization():
        """
        获取图可视化数据，包括当前社区、推荐插入和删除节点
        """
        try:
            # 确保ICSGNN实例已初始化
            if not initialize_icsgnn():
                return jsonify({"error": "Failed to initialize ICSGNN Wrapper"}), 500

            # 检查是否有当前社区
            if not hasattr(icsgnn_instance, 'current_community') or not icsgnn_instance.current_community:
                return jsonify({"error": "No community data available. Please perform a search first."}), 404

            # 获取当前社区
            community_nodes = icsgnn_instance.current_community
            
            # 获取推荐节点(前10个)
            if hasattr(icsgnn_instance, 'recommender'):
                # 获取推荐插入节点
                rec_insert_nodes = []
                all_nodes = list(icsgnn_instance.graph.nodes())
                if hasattr(icsgnn_instance, 'oldres') and icsgnn_instance.oldres:
                    # 使用ppr_algo获取推荐插入节点
                    rec_insert_nodes = icsgnn_instance.recommender.ppr_algo(1, icsgnn_instance.oldres, all_nodes)[:10]
                
                # 获取推荐删除节点
                rec_delete_nodes = []
                if hasattr(icsgnn_instance, 'oldres') and icsgnn_instance.oldres:
                    # 使用ppr_algo获取推荐删除节点
                    rec_delete_nodes = icsgnn_instance.recommender.ppr_algo(0, [], icsgnn_instance.oldres)[:10]
                
                # 使用get_2hop_neighbors获取图可视化数据
                graph_data = icsgnn_instance.recommender.get_2hop_neighbors(
                    rec_insert_nodes, 
                    rec_delete_nodes, 
                    community_nodes
                )
                
                # 返回图数据
                return jsonify(graph_data)
            else:
                return jsonify({"error": "Recommender not initialized"}), 500
            
        except Exception as e:
            logger.error(f"Error in get_graph_visualization: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    @app.route('/api/user_choice', methods=['POST'])
    def process_user_choice():
        """
        处理用户对推荐节点的选择（插入、删除或确认）
        请求体应包含：
        - action: "insert", "delete", "confirm" 或 "none"
        - node_id: 节点ID（仅在insert或delete操作时需要）
        返回:
        - 操作成功或失败的状态
        """
        try:
            if not initialize_icsgnn():
                return jsonify({
                    'status': 'error',
                    'message': 'ICSGNN instance not initialized',
                }), 400
            _sync_instance_to_app(app)
            instance = icsgnn_instance

            request_data = request.get_json()
            if not request_data:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid request data'
                }), 400
            
            action = request_data.get('action')
            node_id = request_data.get('node_id')
            
            # 验证action
            if action not in ['insert', 'delete', 'confirm', 'none']:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid action: {action}'
                }), 400
            
            # 验证node_id（当action为insert或delete时需要）
            if action in ['insert', 'delete'] and node_id is None:
                return jsonify({
                    'status': 'error',
                    'message': f'Node ID is required for {action} action'
                }), 400
            
            if action in ('insert', 'delete') and node_id is not None:
                return jsonify({
                    'status': 'error',
                    'message': (
                        'For demo UI use POST /api/graph/node/insert or '
                        '/api/graph/node/delete'
                    ),
                }), 400

            if action == 'confirm':
                return jsonify({
                    'status': 'success',
                    'message': 'Community confirmed',
                }), 200
            if action == 'none':
                return jsonify({'status': 'success', 'message': 'No action'}), 200

            return jsonify({
                'status': 'error',
                'message': f'Invalid action: {action}',
            }), 400
            
        except Exception as e:
            app.logger.error(f"Error processing user choice: {str(e)}")
            traceback.print_exc()
            return jsonify({
                'status': 'error',
                'message': f'Error processing user choice: {str(e)}'
            }), 500

    @app.route('/api/visualtest', methods=['GET'])
    def visual_test():
        """测试可视化数据路由，返回一些固定的模拟数据"""
        app.logger.info("测试可视化数据路由被访问")
        
        # 构造一些测试数据
        test_nodes = [
            {"id": "1", "label": "Test Node 1", "type": "query", "keywords": ["keyword1", "keyword2"]},
            {"id": "2", "label": "Test Node 2", "type": "community", "keywords": ["keyword3", "keyword4"]},
            {"id": "3", "label": "Test Node 3", "type": "normal", "keywords": ["keyword5"]}
        ]
        
        test_edges = [
            {"source": "1", "target": "2", "type": "community"},
            {"source": "2", "target": "3", "type": "normal"}
        ]
        
        # 测试数据结构
        test_data = {
            "status": "success",
            "nodes": test_nodes,
            "edges": test_edges,
            "recommendInsert": ["4", "5"],
            "recommendDelete": ["6", "7"],
            "community": [
                {"id": 1, "name": "Test Node 1", "keywords": ["keyword1", "keyword2"]},
                {"id": 2, "name": "Test Node 2", "keywords": ["keyword3", "keyword4"]}
            ],
            "seed_node": 1
        }
        
        app.logger.info(f"返回测试数据: {test_data}")
        
        # 设置CORS头
        response = jsonify(test_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    @app.route('/api/lastvisualization', methods=['GET'])
    def get_last_visualization():
        """获取最近一次存储的可视化数据"""
        visualization_data = app.config.get('LAST_VISUALIZATION', {})
        if not visualization_data:
            return jsonify({
                "status": "error",
                "message": "No visualization data available",
            }), 404

        payload = _extract_visualization_emit_payload(visualization_data)
        if payload is None:
            return jsonify({
                "status": "error",
                "message": "Invalid visualization data format",
            }), 500

        response = jsonify(payload)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    @app.route('/api/graph/node/delete', methods=['POST'])
    def delete_node():
        """
        删除节点API接口
        将指定节点从社区中移除（变成普通节点）
        特别处理Ameet Talwalkar的情况
        """
        try:
            data = request.get_json()
            node_id = data.get('nodeId')
            
            if not node_id:
                return jsonify({
                    "status": "error",
                    "message": "Node ID is required"
                }), 400
                
            logger.info(f"Processing delete node request for node: {node_id}")
            
            # 尝试将字符串ID转换为整数
            try:
                node_id = int(node_id)
            except ValueError:
                pass  # 如果无法转换，保持原样
                
            # 确保ICSGNN实例已初始化
            if not initialize_icsgnn():
                return jsonify({
                    "status": "error",
                    "message": "Failed to initialize ICSGNN Wrapper"
                }), 500
                
            # 获取当前社区和推荐节点数据
            community_nodes = []
            if hasattr(icsgnn_instance, 'current_community') and icsgnn_instance.current_community:
                community_nodes = icsgnn_instance.current_community
            elif hasattr(icsgnn_instance, 'oldres') and icsgnn_instance.oldres:
                community_nodes = icsgnn_instance.oldres
                
            if not community_nodes:
                return jsonify({
                    "status": "error",
                    "message": "No community data available"
                }), 404
                
            # 检查节点是否在社区中
            ameet_talwalkar_id = 63258
            node_in_community = False
            
            # 将字符串ID转换为适当的类型进行比较
            for node in community_nodes:
                if str(node) == str(node_id):
                    node_in_community = True
                    break
            
            if not node_in_community:
                return jsonify({
                    "status": "error",
                    "message": "Node not found in community"
                }), 404
                
            # 特殊处理Ameet Talwalkar
            is_ameet = str(node_id) == str(ameet_talwalkar_id)
            if is_ameet:
                logger.info(f"Special handling for Ameet Talwalkar (ID: {ameet_talwalkar_id})")
                
            # 从社区中移除节点
            new_community = []
            for node in community_nodes:
                if str(node) != str(node_id):
                    new_community.append(node)
                    
            # 更新社区数据
            if hasattr(icsgnn_instance, 'current_community'):
                icsgnn_instance.current_community = new_community
            if hasattr(icsgnn_instance, 'oldres'):
                icsgnn_instance.oldres = new_community

            query_node = (
                icsgnn_instance.oldpos[0]
                if getattr(icsgnn_instance, "oldpos", None)
                else 27484
            )

            community_nodes = new_community

            ring_size = getattr(icsgnn_instance.args, "community_size", 25)
            recommend_cap = max(1, min(5, ring_size // 5))

            normal_nodes = []
            bfs_queue = deque(community_nodes.copy())
            all_visited = set(community_nodes)

            while bfs_queue and len(normal_nodes) < ring_size:
                node = bfs_queue.popleft()

                for neighbor in icsgnn_instance.graph.neighbors(node):
                    if neighbor not in all_visited:
                        all_visited.add(neighbor)
                        normal_nodes.append(neighbor)
                        if len(normal_nodes) < ring_size:
                            bfs_queue.append(neighbor)
                        else:
                            break

            if node_id not in normal_nodes:
                normal_nodes.append(node_id)

            recommend_insert_nodes = []
            if len(normal_nodes) > recommend_cap:
                filtered_normal_nodes = [n for n in normal_nodes if str(n) != str(node_id) and n != query_node]
                if len(filtered_normal_nodes) >= recommend_cap:
                    recommend_insert_nodes = random.sample(filtered_normal_nodes, recommend_cap)
                else:
                    recommend_insert_nodes = filtered_normal_nodes

            recommend_delete_nodes = []
            if len(community_nodes) > recommend_cap:
                filtered_community_nodes = [n for n in community_nodes if n != query_node]
                if len(filtered_community_nodes) >= recommend_cap:
                    recommend_delete_nodes = random.sample(filtered_community_nodes, recommend_cap)
                else:
                    recommend_delete_nodes = filtered_community_nodes
                
            # 从列表中移除推荐节点以避免重复
            real_normal_nodes = [n for n in normal_nodes if n not in recommend_insert_nodes]
            real_community_nodes = [n for n in community_nodes if n not in recommend_delete_nodes]
            
            # 获取完整图数据
            all_relevant_nodes = [query_node] + real_community_nodes + recommend_insert_nodes + real_normal_nodes + recommend_delete_nodes
            full_subgraph = icsgnn_instance.graph.subgraph(all_relevant_nodes)
            
            # 准备节点数据
            nodes = []

            # 添加查询节点
            nodes.append({
                "id": str(query_node),
                "label": _get_node_label(icsgnn_instance, query_node),
                "type": "query",
                "keywords": _get_node_keywords(icsgnn_instance, query_node)
            })

            # 添加社区节点
            for node in real_community_nodes:
                nodes.append({
                    "id": str(node),
                    "label": _get_node_label(icsgnn_instance, node),
                    "type": "community",
                    "keywords": _get_node_keywords(icsgnn_instance, node)
                })

            # 添加推荐插入节点
            for node in recommend_insert_nodes:
                nodes.append({
                    "id": str(node),
                    "label": _get_node_label(icsgnn_instance, node),
                    "type": "insert",
                    "keywords": _get_node_keywords(icsgnn_instance, node)
                })

            # 添加普通节点，包括刚删除的节点
            for node in real_normal_nodes:
                # 特殊处理Ameet Talwalkar，给他特殊标记
                node_type = "normal"
                if is_ameet and str(node) == str(node_id):
                    node_type = "normal"  # 你也可以设置一个特殊值如"removed"

                nodes.append({
                    "id": str(node),
                    "label": _get_node_label(icsgnn_instance, node),
                    "type": node_type,
                    "keywords": _get_node_keywords(icsgnn_instance, node)
                })

            # 添加推荐删除节点
            for node in recommend_delete_nodes:
                nodes.append({
                    "id": str(node),
                    "label": _get_node_label(icsgnn_instance, node),
                    "type": "delete",
                    "keywords": _get_node_keywords(icsgnn_instance, node)
                })
                
            # 准备边数据
            edges = []
            for u, v in full_subgraph.edges():
                # 判断边的类型
                edge_type = "normal"
                # 如果两个节点都是社区节点或查询节点，则标记为社区边
                if ((u == query_node or u in real_community_nodes) and 
                    (v == query_node or v in real_community_nodes)):
                    edge_type = "community"
                    
                edges.append({
                    "source": str(u),
                    "target": str(v),
                    "type": edge_type
                })
                
            # 创建可视化数据
            visualization = {
                "nodes": nodes,
                "edges": edges,
                "recommendInsert": [str(node) for node in recommend_insert_nodes],
                "recommendDelete": [str(node) for node in recommend_delete_nodes]
            }
            
            emit_visualization_update({"data": visualization})

            return jsonify({
                "status": "success",
                "message": f"Node {node_id} has been removed from community",
                "data": visualization
            })
            
        except Exception as e:
            logger.error(f"Error in delete_node: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                "status": "error",
                "message": f"Error: {str(e)}"
            }), 500

    @app.route('/api/graph/node/insert', methods=['POST'])
    def insert_node():
        """
        添加节点API接口
        将指定节点添加到社区中（从普通节点变为社区节点）
        """
        try:
            data = request.get_json()
            node_id = data.get('nodeId')
            
            if not node_id:
                return jsonify({
                    "status": "error",
                    "message": "Node ID is required"
                }), 400
                
            logger.info(f"Processing insert node request for node: {node_id}")
            
            # 尝试将字符串ID转换为整数
            try:
                node_id = int(node_id)
            except ValueError:
                pass  # 如果无法转换，保持原样
                
            # 确保ICSGNN实例已初始化
            if not initialize_icsgnn():
                return jsonify({
                    "status": "error",
                    "message": "Failed to initialize ICSGNN Wrapper"
                }), 500
                
            # 获取当前社区和推荐节点数据
            community_nodes = []
            if hasattr(icsgnn_instance, 'current_community') and icsgnn_instance.current_community:
                community_nodes = icsgnn_instance.current_community
            elif hasattr(icsgnn_instance, 'oldres') and icsgnn_instance.oldres:
                community_nodes = icsgnn_instance.oldres
                
            if not community_nodes:
                return jsonify({
                    "status": "error",
                    "message": "No community data available"
                }), 404
                
            # 检查节点是否已经在社区中
            node_in_community = False
            for node in community_nodes:
                if str(node) == str(node_id):
                    node_in_community = True
                    break
            
            if node_in_community:
                return jsonify({
                    "status": "error",
                    "message": "Node already in community"
                }), 400
                
            # 将节点添加到社区
            new_community = community_nodes.copy()
            new_community.append(node_id)
                    
            # 更新社区数据
            if hasattr(icsgnn_instance, 'current_community'):
                icsgnn_instance.current_community = new_community
            if hasattr(icsgnn_instance, 'oldres'):
                icsgnn_instance.oldres = new_community

            query_node = (
                icsgnn_instance.oldpos[0]
                if getattr(icsgnn_instance, "oldpos", None)
                else 27484
            )
            community_nodes = new_community

            ring_size = getattr(icsgnn_instance.args, "community_size", 25)
            recommend_cap = max(1, min(5, ring_size // 5))

            normal_nodes = []
            bfs_queue = deque(community_nodes.copy())
            all_visited = set(community_nodes)

            while bfs_queue and len(normal_nodes) < ring_size:
                node = bfs_queue.popleft()

                for neighbor in icsgnn_instance.graph.neighbors(node):
                    if neighbor not in all_visited:
                        all_visited.add(neighbor)
                        normal_nodes.append(neighbor)
                        if len(normal_nodes) < ring_size:
                            bfs_queue.append(neighbor)
                        else:
                            break

            recommend_insert_nodes = []
            if len(normal_nodes) > recommend_cap:
                filtered_normal_nodes = [n for n in normal_nodes if str(n) != str(node_id) and n != query_node]
                if len(filtered_normal_nodes) >= recommend_cap:
                    recommend_insert_nodes = random.sample(filtered_normal_nodes, recommend_cap)
                else:
                    recommend_insert_nodes = filtered_normal_nodes

            recommend_delete_nodes = []
            if len(community_nodes) > recommend_cap:
                filtered_community_nodes = [n for n in community_nodes if n != query_node]
                if len(filtered_community_nodes) >= recommend_cap:
                    recommend_delete_nodes = random.sample(filtered_community_nodes, recommend_cap)
                else:
                    recommend_delete_nodes = filtered_community_nodes
                
            # 从列表中移除推荐节点以避免重复
            real_normal_nodes = [n for n in normal_nodes if n not in recommend_insert_nodes]
            real_community_nodes = [n for n in community_nodes if n not in recommend_delete_nodes]
            
            # 获取完整图数据
            all_relevant_nodes = [query_node] + real_community_nodes + recommend_insert_nodes + real_normal_nodes + recommend_delete_nodes
            full_subgraph = icsgnn_instance.graph.subgraph(all_relevant_nodes)
            
            # 准备节点数据
            nodes = []

            # 添加查询节点
            nodes.append({
                "id": str(query_node),
                "label": _get_node_label(icsgnn_instance, query_node),
                "type": "query",
                "keywords": _get_node_keywords(icsgnn_instance, query_node)
            })

            # 添加社区节点，包括刚添加的节点
            for node in real_community_nodes:
                nodes.append({
                    "id": str(node),
                    "label": _get_node_label(icsgnn_instance, node),
                    "type": "community",
                    "keywords": _get_node_keywords(icsgnn_instance, node)
                })

            # 添加推荐插入节点
            for node in recommend_insert_nodes:
                nodes.append({
                    "id": str(node),
                    "label": _get_node_label(icsgnn_instance, node),
                    "type": "insert",
                    "keywords": _get_node_keywords(icsgnn_instance, node)
                })

            # 添加普通节点
            for node in real_normal_nodes:
                nodes.append({
                    "id": str(node),
                    "label": _get_node_label(icsgnn_instance, node),
                    "type": "normal",
                    "keywords": _get_node_keywords(icsgnn_instance, node)
                })

            # 添加推荐删除节点
            for node in recommend_delete_nodes:
                nodes.append({
                    "id": str(node),
                    "label": _get_node_label(icsgnn_instance, node),
                    "type": "delete",
                    "keywords": _get_node_keywords(icsgnn_instance, node)
                })
                
            # 准备边数据
            edges = []
            for u, v in full_subgraph.edges():
                # 判断边的类型
                edge_type = "normal"
                # 如果两个节点都是社区节点或查询节点，则标记为社区边
                if ((u == query_node or u in real_community_nodes) and 
                    (v == query_node or v in real_community_nodes)):
                    edge_type = "community"
                    
                edges.append({
                    "source": str(u),
                    "target": str(v),
                    "type": edge_type
                })
                
            # 创建可视化数据
            visualization = {
                "nodes": nodes,
                "edges": edges,
                "recommendInsert": [str(node) for node in recommend_insert_nodes],
                "recommendDelete": [str(node) for node in recommend_delete_nodes]
            }
            
            emit_visualization_update({"data": visualization})

            return jsonify({
                "status": "success",
                "message": f"Node {node_id} has been added to community",
                "data": visualization
            })
            
        except Exception as e:
            logger.error(f"Error in insert_node: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({
                "status": "error",
                "message": f"Error: {str(e)}"
            }), 500 