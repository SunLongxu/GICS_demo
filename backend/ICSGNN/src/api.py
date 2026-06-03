from flask import Flask, request, jsonify, make_response
from src.api_wrapper import ICSGNNWrapper
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import eventlet
import logging
import sys
from werkzeug.serving import WSGIRequestHandler
import traceback
from main import search_community

# 配置 Werkzeug 使用 HTTP/1.1
WSGIRequestHandler.protocol_version = "HTTP/1.1"

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

eventlet.monkey_patch()

app = Flask(__name__)

# CORS 配置
CORS(app, 
     origins=["http://localhost:5173", "*"],
     allow_headers=["Content-Type"],
     supports_credentials=True)

# Socket.IO 配置
socketio = SocketIO(app, 
                   cors_allowed_origins=["http://localhost:5173", "*"],
                   async_mode='eventlet',
                   ping_timeout=60,
                   ping_interval=25,
                   logger=True)

# 全局变量存储ICSGNN实例
icsgnn_instance = None

def initialize_icsgnn():
    """
    初始化ICSGNN Wrapper实例
    """
    global icsgnn_instance
    try:
        if icsgnn_instance is None:
            logger.info("Initializing ICSGNN Wrapper...")
            icsgnn_instance = ICSGNNWrapper()
            
            # 检查是否已经加载了数据集
            if not hasattr(icsgnn_instance, 'graph') or icsgnn_instance.graph is None:
                logger.info("Loading DBLP dataset...")
                # 加载DBLP数据集
                icsgnn_instance.load_dataset("com-dblpname")
                logger.info("DBLP dataset loaded successfully")
            else:
                logger.info("Dataset already loaded, skipping...")
                
            # 确保recommender已初始化
            if not hasattr(icsgnn_instance, 'recommender') or icsgnn_instance.recommender is None:
                logger.info("Initializing recommender...")
                icsgnn_instance.initialize_recommender()
                logger.info("Successfully initialized recommender")
            else:
                logger.info("Recommender already initialized")
                
            logger.info("ICSGNN Wrapper initialized successfully")
        else:
            logger.info("ICSGNN Wrapper already initialized")
            
        return True
    except Exception as e:
        logger.error(f"Failed to initialize ICSGNN Wrapper: {str(e)}")
        logger.error(traceback.format_exc())
        return False

@app.route('/')
def index():
    logger.debug("Root route accessed")
    return "Server is running"

@app.route('/test', methods=['GET'])
def test_endpoint():
    logger.debug("Test route accessed")
    response = jsonify({
        "status": "success",
        "message": "Test endpoint working with Waitress"
    })
    logger.debug(f"Response headers: {dict(response.headers)}")
    return response

@app.route('/check-cors')
def check_cors():
    logger.debug("Check CORS route accessed")
    response = jsonify({"message": "CORS check successful with Waitress"})
    logger.debug(f"Response headers: {dict(response.headers)}")
    return response

@socketio.on('connect')
def connect_handler():
    logger.debug("Client connected")
    print('Client connected')
    emit('connection_response', {'data': 'Connected'})

@socketio.on('disconnect')
def disconnect_handler():
    logger.debug("Client disconnected")
    print('Client disconnected')

@socketio.on('message')
def handle_message(data):
    logger.debug(f"Received message: {data}")
    print('Received message: ' + str(data))
    emit('response', 'Server received your message!')

@socketio.on_error()
def error_handler(e):
    logger.error(f"Socket.IO error: {str(e)}")
    print(f"Socket.IO error: {str(e)}")

def handle_state_update(state):
    """
    处理状态更新并通过 WebSocket 发送
    """
    try:
        logger.debug(f"Emitting state update: {state}")
        socketio.emit('state_update', state)
    except Exception as e:
        logger.error(f"Error emitting state update: {e}")
        print(f"Error emitting state update: {e}")

@app.route('/api/graph/initial', methods=['GET'])
def get_initial_graph():
    """
    获取初始图数据
    """
    try:
        # 获取查询参数
        dataset = request.args.get('dataset', 'DBLP')
        model = request.args.get('model', 'GNN')
        
        # 根据选择的模型和数据集加载相应的模块
        if dataset == 'DBLP' and model == 'GNN':
            # 初始化ICSGNN实例
            if not initialize_icsgnn():
                return jsonify({
                    "status": "error",
                    "message": "Failed to initialize ICSGNN Wrapper"
                }), 500
            
            # 获取初始图数据
            result = icsgnn_instance.get_initial_graph()
        if result["status"] == "success":
            return jsonify({
                "status": "success",
                "data": result["data"]
            })
        else:
            return jsonify({
                "status": "error",
                "message": result.get("message", "Failed to load initial graph")
            }), 500
        else:
            return jsonify({
                "status": "error",
                "message": f"Unsupported combination of dataset ({dataset}) and model ({model})"
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
    处理社区搜索请求 - 异步模式
    请求体格式:
    {
        "query": str,  # 查询人名
        "community_size": int,  # 期望的社区大小
        "positive_nodes": List[int],  # 正样本节点列表
        "negative_nodes": List[int],  # 负样本节点列表
        "iteration": int,  # 当前迭代次数
        "dataset": str,  # 数据集名称
        "model": str  # 模型名称
    }
    """
    try:
        # 获取查询参数
        data = request.get_json()
        query = data.get('query')
        additional_names = data.get('additional_names', [])
        community_size = data.get('community_size', 30)
        positive_nodes = data.get('positive_nodes', [])
        negative_nodes = data.get('negative_nodes', [])
        iteration = data.get('iteration', 0)
        dataset = data.get('dataset', 'DBLP')
        model = data.get('model', 'GNN')
        
        logger.info(f"Received search request: query={query}, dataset={dataset}, model={model}")
        
        if not query:
            return jsonify({"error": "query is required"}), 400

        # 根据选择的模型和数据集使用相应的模块
        if dataset == 'DBLP' and model == 'GNN':
            # 确保ICSGNN实例已初始化
            if not initialize_icsgnn():
                return jsonify({"error": "Failed to initialize ICSGNN Wrapper"}), 500

            # 设置参数
            icsgnn_instance.args.community_size = community_size
            
            # 直接操作recommender
            # 1. 如果不存在，先初始化recommender
            if not hasattr(icsgnn_instance, 'recommender') or icsgnn_instance.recommender is None:
                logger.info("Creating new recommender instance")
                from src.recommend import PPRRecommend
                icsgnn_instance.recommender = PPRRecommend(icsgnn_instance.args, icsgnn_instance)
            
            # 2. 定义并设置可视化回调函数 - 这是异步更新的关键
            def visualization_callback(data):
                logger.info("\n===== 调试: visualization_callback被调用 =====")
                logger.info(f"接收到可视化数据结构类型: {type(data).__name__}")
                
                try:
                    # 处理可视化数据
                    if isinstance(data, dict) and 'data' in data:
                        visualization_content = data['data']
                        
                        # 确保每个节点都有关键词
                        if 'nodes' in visualization_content:
                            nodes_count = len(visualization_content['nodes'])
                            logger.info(f"处理{nodes_count}个节点的关键词数据...")
                            
                            # 处理前检查关键词状态
                            nodes_with_keywords_before = sum(1 for node in visualization_content['nodes'] if 'keywords' in node and node['keywords'])
                            logger.info(f"处理前，有{nodes_with_keywords_before}个节点包含关键词")
                            
                            # 处理节点关键词
                            for node in visualization_content['nodes']:
                                node_id = None
                                try:
                                    # 将节点ID转换为整数，因为大多数API都使用整数ID
                                    node_id = int(node['id'])
                                    
                                    # 确保每个节点都有keywords字段
                                    if 'keywords' not in node or not node['keywords']:
                                        # 尝试从icsgnn_instance获取关键词
                                        if hasattr(icsgnn_instance, 'keywords'):
                                            if isinstance(icsgnn_instance.keywords, dict) and node_id in icsgnn_instance.keywords:
                                                keyword_str = icsgnn_instance.keywords[node_id]
                                                if isinstance(keyword_str, str):
                                                    if "&" in keyword_str:
                                                        node['keywords'] = [kw.strip() for kw in keyword_str.split("&")]
                                                    elif "," in keyword_str:
                                                        node['keywords'] = [kw.strip() for kw in keyword_str.split(",")]
                                                    else:
                                                        node['keywords'] = [keyword_str.strip()]
                                                else:
                                                    node['keywords'] = []
                                            else:
                                                # 如果找不到关键词，用空数组
                                                node['keywords'] = []
                                except Exception as e:
                                    logger.error(f"处理节点{node_id}关键词时出错: {str(e)}")
                        
                        # 准备发送数据结构
                        emit_data = {
                            'status': 'success',
                            'nodes': visualization_content.get('nodes', []),
                            'edges': visualization_content.get('edges', []),
                            'recommendInsert': visualization_content.get('recommendInsert', []),
                            'recommendDelete': visualization_content.get('recommendDelete', [])
                        }
                        
                        # 将数据通过websocket推送给前端
                        logger.info(f"通过WebSocket推送可视化数据，包含{len(emit_data.get('nodes', []))}个节点")
                        socketio.emit('visualization_update', emit_data)
                    
                    # 存储可视化数据供后续请求使用
                    app.config['LAST_VISUALIZATION'] = data
                    logger.info("===== 调试: visualization_callback处理完成 =====\n")
                except Exception as e:
                    logger.error(f"visualization_callback处理异常: {str(e)}")
                    logger.error(traceback.format_exc())
                
                return data

        # 设置状态回调
            icsgnn_instance.set_state_callback(visualization_callback)
            logger.info(f"状态回调已设置到icsgnn_instance")
            
            # 获取查询节点ID（根据人名查询）
            node_id = icsgnn_instance.get_node_id_by_name(query)
            if node_id is None:
                return jsonify({"error": f"找不到作者: {query}"}), 404

            logger.info(f"查询作者 '{query}' 对应的节点ID: {node_id}")
            
            # 处理额外的作者名称作为positive nodes
            positive_ids = []
            if additional_names and len(additional_names) > 0:
                logger.info(f"Processing additional names: {additional_names}")
                for name in additional_names:
                    additional_node_id = icsgnn_instance.get_node_id_by_name(name)
                    if additional_node_id is not None:
                        positive_ids.append(additional_node_id)
                        logger.info(f"Added additional author: {name} (ID: {additional_node_id})")
            
            # 确保主查询节点也在正样本列表中
            if node_id not in positive_ids:
                positive_ids.append(node_id)
            
            # 设置到实例中用于追踪
            if hasattr(icsgnn_instance, 'oldpos'):
                icsgnn_instance.oldpos = positive_ids
            
            # 异步启动搜索过程 - 使用后台线程执行
            import threading
            
            def run_search():
                try:
                    # 调用 main.py 中的 search_community 函数
                    logger.info(f"在后台线程中启动search_community，查询节点: {node_id}")
                    result = search_community(icsgnn_instance.args, node_id)
                    
                    if result["status"] == "success":
                        # 保存结果到实例中
                        icsgnn_instance.current_community = result["data"]["community"]
                        icsgnn_instance.oldres = result["data"]["community"]
                        logger.info(f"搜索完成，找到社区节点: {len(result['data']['community'])}")
                    else:
                        logger.error(f"搜索失败: {result.get('message', 'Unknown error')}")
                except Exception as e:
                    logger.error(f"后台搜索线程异常: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # 启动搜索线程
            search_thread = threading.Thread(target=run_search)
            search_thread.daemon = True  # 设置为守护线程，主程序退出时线程会自动结束
            search_thread.start()
            
            # 立即返回初始响应
            initial_response = {
                'status': 'processing',
                'message': '搜索已开始，结果将通过WebSocket推送',
                'seed_node': node_id,
                'seed_name': query
            }
            
            # 设置CORS头
            response = jsonify(initial_response)
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        else:
            return jsonify({
                "error": f"Unsupported combination of dataset ({dataset}) and model ({model})"
            }), 400

    except Exception as e:
        logger.error(f"Error in search_community_api: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/update', methods=['POST'])
def update_community():
    """
    处理社区更新请求
    请求体格式:
    {
        "positive_nodes": List[int],  # 要插入的节点列表
        "negative_nodes": List[int],  # 要删除的节点列表
        "iteration": int  # 当前迭代次数
    }
    """
    try:
        data = request.get_json()
        positive_nodes = data.get('positive_nodes', [])
        negative_nodes = data.get('negative_nodes', [])
        iteration = data.get('iteration', 0)

        # 设置状态回调
        icsgnn_instance.set_state_callback(handle_state_update)

        # 更新社区
        result = icsgnn_instance.update_community(
            positive_nodes=positive_nodes,
            negative_nodes=negative_nodes,
            iteration=iteration
        )

        if "error" in result:
            return jsonify(result), 400

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/recommend', methods=['POST'])
def recommend_nodes():
    """
    处理节点推荐请求
    请求体格式:
    {
        "current_community": List[int],  # 当前社区节点列表
        "num_recommendations": int  # 推荐节点数量
    }
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

@app.route('/api/visualtest', methods=['GET'])
def visual_test():
    """测试可视化数据路由，返回一些固定的模拟数据"""
    logger.info("测试可视化数据路由被访问")
    
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
    
    logger.info(f"返回测试数据: {test_data}")
    
    # 设置CORS头
    response = jsonify(test_data)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/api/lastvisualization', methods=['GET'])
def get_last_visualization():
    """获取最近一次存储的可视化数据，用于调试"""
    logger.info("获取最近一次的可视化数据")
    
    # 从app.config中获取最近的可视化数据
    visualization_data = app.config.get('LAST_VISUALIZATION', {})
    
    if not visualization_data:
        logger.warning("没有找到可视化数据")
        return jsonify({
            "status": "error",
            "message": "No visualization data available"
        }), 404
    
    # 从可视化数据中提取节点和边
    if isinstance(visualization_data, dict) and 'data' in visualization_data:
        vis_content = visualization_data['data']
        
        response_data = {
            "status": "success",
            "nodes": vis_content.get('nodes', []),
            "edges": vis_content.get('edges', []),
            "recommendInsert": vis_content.get('recommendInsert', []),
            "recommendDelete": vis_content.get('recommendDelete', [])
        }
        
        logger.info(f"返回可视化数据：包含{len(response_data.get('nodes', []))}个节点")
        
        # 设置CORS头
        response = jsonify(response_data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
    else:
        logger.warning("可视化数据格式不正确")
        return jsonify({
            "status": "error",
            "message": "Invalid visualization data format"
        }), 500

@app.route('/api/debug/status', methods=['GET'])
def debug_status():
    """返回当前ICSGNN实例的状态信息，用于调试"""
    global icsgnn_instance
    
    if icsgnn_instance is None:
        return jsonify({
            "status": "error",
            "message": "icsgnn_instance is not initialized"
        }), 404
    
    # 收集状态信息
    status = {
        "initialized": True,
        "has_graph": hasattr(icsgnn_instance, 'graph') and icsgnn_instance.graph is not None,
        "has_recommender": hasattr(icsgnn_instance, 'recommender') and icsgnn_instance.recommender is not None,
        "has_callback": hasattr(icsgnn_instance, 'state_callback') and icsgnn_instance.state_callback is not None,
        "has_authorname": hasattr(icsgnn_instance, 'authorname'),
        "has_keywords": hasattr(icsgnn_instance, 'keywords'),
        "has_current_community": hasattr(icsgnn_instance, 'current_community') and icsgnn_instance.current_community is not None,
        "community_size": len(icsgnn_instance.current_community) if hasattr(icsgnn_instance, 'current_community') and icsgnn_instance.current_community else 0,
        "callback_type": str(type(icsgnn_instance.state_callback)) if hasattr(icsgnn_instance, 'state_callback') and icsgnn_instance.state_callback else "None"
    }
    
    # 如果有recommender，添加更多信息
    if status["has_recommender"]:
        try:
            recommender = icsgnn_instance.recommender
            status["recommender_info"] = {
                "type": str(type(recommender)),
                "has_upgraph": hasattr(recommender, 'upgraph') and recommender.upgraph is not None,
                "has_callback": hasattr(recommender, 'state_callback') and recommender.state_callback is not None,
                "callback_type": str(type(recommender.state_callback)) if hasattr(recommender, 'state_callback') and recommender.state_callback else "None"
            }
        except Exception as e:
            status["recommender_error"] = str(e)
    
    # 检查app.config中的可视化数据
    status["has_visualization_data"] = 'LAST_VISUALIZATION' in app.config and app.config['LAST_VISUALIZATION'] is not None
    
    if status["has_visualization_data"]:
        viz_data = app.config['LAST_VISUALIZATION']
        status["visualization_data_type"] = str(type(viz_data))
        status["visualization_has_data"] = 'data' in viz_data if isinstance(viz_data, dict) else False
        
        if status["visualization_has_data"] and isinstance(viz_data['data'], dict):
            viz_content = viz_data['data']
            status["visualization_nodes_count"] = len(viz_content.get('nodes', []))
            status["visualization_edges_count"] = len(viz_content.get('edges', []))
            
            # 检查关键词情况
            if 'nodes' in viz_content and viz_content['nodes']:
                nodes_with_keywords = sum(1 for node in viz_content['nodes'] if 'keywords' in node and node['keywords'])
                status["nodes_with_keywords"] = f"{nodes_with_keywords}/{len(viz_content['nodes'])}"
                
                # 提供一个节点示例
                status["sample_node"] = viz_content['nodes'][0] if viz_content['nodes'] else None
    
    return jsonify(status)

# 如果直接运行此文件，使用 Flask 开发服务器
if __name__ == '__main__':
    print("Starting server with Socket.IO:")
    print(f"Host: 0.0.0.0")
    print(f"Port: 5001")
    print(f"CORS origins: http://localhost:5173")
    print(f"Debug mode: on")
    
    # 使用socketio.run()而不是app.run()，以确保WebSocket功能正常工作
    socketio.run(app, 
                host='0.0.0.0', 
                port=5001, 
                debug=True, 
               use_reloader=False,
               log_output=True) 