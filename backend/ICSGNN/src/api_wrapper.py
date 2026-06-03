from typing import Dict, List, Any
from src.recommend import PPRRecommend
import argparse
import traceback
from src.parser import parameter_parser
import numpy as np
import torch
import torch.nn as nn
from main import search_community, get_global_data, load_data
import random

class ICSGNNWrapper:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ICSGNNWrapper, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """
        初始化 ICSGNN 包装器（单例模式）
        """
        if self._initialized:
            return
            
        try:
            # 初始化参数
            self.args = parameter_parser()
            
            # 从 main.py 获取全局数据
            global_data = get_global_data()
            
            # 检查数据是否已加载
            if global_data.get('graph') is None:
                print("Loading DBLP dataset...")
                # 调用 load_data 加载数据
                graph, features, target, _, _, _, authorname, keywords, mapper = load_data(self.args)
                
                # 更新全局数据
                global_data['graph'] = graph
                global_data['features'] = features
                global_data['authorname'] = authorname
                global_data['keywords'] = keywords
                global_data['mapper'] = mapper
                print("DBLP dataset loaded successfully")
            else:
                print("Using existing DBLP dataset")
                graph = global_data['graph']
                features = global_data['features']
                authorname = global_data['authorname']
                keywords = global_data['keywords']
                mapper = global_data['mapper']
            
            # 保存数据到实例变量
            self.graph = graph
            self.features = features
            self.authorname = authorname
            self.keywords = keywords
            self.mapper = mapper
            
            # 初始化推荐器
            self.create_recommender()
            print("Successfully initialized recommender")
            
            # 当前社区信息
            self.current_community = None
            self.target = {}  # 节点到社区的映射
            self.oldpos = []  # 已插入的节点
            self.oldneg = []
            self.oldres = []  # 当前社区结果
            self.allnode = list(self.graph.nodes())  # 所有节点
            
            # 状态回调相关
            self.state_callback = None
            self._initialized = True
            
        except Exception as e:
            print(f"Error initializing ICSGNNWrapper: {str(e)}")
            traceback.print_exc()
            raise

    def create_recommender(self):
        """
        创建推荐器实例
        如果已存在，则保留现有的回调函数
        """
        try:
            # 直接创建新的推荐器，不设置回调
            from src.recommend import PPRRecommend
            self.recommender = PPRRecommend(self.args, self)
            
            print(f"推荐器已创建，不设置回调 - 改为直接使用state_callback")
            return True
        except Exception as e:
            print(f"Error creating recommender: {str(e)}")
            traceback.print_exc()
            return False

    def set_state_callback(self, callback):
        """
        设置状态更新回调函数
        Args:
            callback: 回调函数，接收一个状态参数
        """
        print(f"设置状态回调函数")
        self.state_callback = callback
        print(f"状态回调函数已设置: {self.state_callback is not None}")

    def reset_state(self):
        """
        重置当前状态
        """
        self.current_community = None
        self.target = {}
        self.oldpos = []
        self.oldneg = []
        self.oldres = []
        self.allnode = []

    def search_community(self, query_node):
        """
        Search community for a given node
        Args:
            query_node: Node ID or author name to search for
        Returns:
            dict: Search results containing community information and recommendations
        """
        try:
            # 检查 query_node 是否是作者名
            if isinstance(query_node, str):
                # 在作者名列表中查找
                for node_id, name in enumerate(self.authorname):
                    if name.lower() == query_node.lower():
                        query_node = node_id
                        print(f"Found author name '{query_node}' with node ID: {node_id}")
                        break
                else:
                    return {"status": "error", "message": f"Author name '{query_node}' not found"}
            
            # 调用 main.py 中的 search_community 方法
            result = search_community(self.args, query_node)
            
            if result["status"] == "success":
                self.current_community = result["data"]["community"]
                return result
            else:
                return result
                
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_community(self, positive_nodes, negative_nodes, iteration):
        """
        更新社区
        Args:
            positive_nodes: 要插入的节点列表
            negative_nodes: 要删除的节点列表
            iteration: 当前迭代次数
        Returns:
            dict: 更新结果
        """
        try:
            if not hasattr(self, 'current_community') or not self.current_community:
                return {"error": "没有当前社区数据可更新"}
            
            # 更新社区
            updated_community = self.current_community.copy()
            
            # 添加正向节点
            for node in positive_nodes:
                if node not in updated_community:
                    updated_community.append(node)
                    
            # 移除负向节点
            for node in negative_nodes:
                if node in updated_community:
                    updated_community.remove(node)
            
            # 更新当前社区
            self.current_community = updated_community
            self.oldres = updated_community
            
            # 格式化返回结果
            nodes = []
            for node in updated_community:
                node_info = {
                    "id": node
                }
                
                # 处理authorname可能是列表的情况
                if hasattr(self, 'authorname'):
                    if isinstance(self.authorname, list) and node < len(self.authorname):
                        node_info["name"] = self.authorname[node]
                    elif isinstance(self.authorname, dict) and node in self.authorname:
                        node_info["name"] = self.authorname[node]
                    else:
                        node_info["name"] = f"Node {node}"
                else:
                    node_info["name"] = f"Node {node}"
                
                # 处理keywords可能是列表的情况
                if hasattr(self, 'keywords'):
                    if isinstance(self.keywords, list) and node < len(self.keywords):
                        node_info["keywords"] = self.keywords[node]
                    elif isinstance(self.keywords, dict) and node in self.keywords:
                        node_info["keywords"] = self.keywords[node]
                    else:
                        node_info["keywords"] = []
                else:
                    node_info["keywords"] = []
                    
                nodes.append(node_info)
            
            community_info = {
                "nodes": nodes,
                "size": len(updated_community),
                "iteration": iteration + 1
            }
            
            return community_info
        except Exception as e:
            print(f"更新社区时出错: {str(e)}")
            traceback.print_exc()
            return {"error": str(e)}

    def get_recommendations(self):
        """
        Get node recommendations
        Returns:
            dict: Node recommendations
        """
        try:
            if self.current_community is None:
                return {"status": "error", "message": "No community found"}
            # 使用search_community获取推荐
            result = search_community(self.args)
            
            if result["status"] == "success":
                return result["data"]["recommendations"]
            else:
                return result
                
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_community_info(self) -> Dict[str, Any]:
        """
        获取当前社区信息
        Returns:
            Dict: 包含社区信息的字典
        """
        if not self.current_community:
            return {"error": "No community found"}
            
        return {
            "nodes": [{
                "id": node,
                "name": self.authorname[node],
                "keywords": self.keywords[node]
            } for node in self.current_community],
            "size": len(self.current_community),
            "positive_nodes": self.oldpos,
            "negative_nodes": self.oldneg
        }

    def _convert_to_api_format(self, nodes: List[int], edges: List[tuple], rec_insert: List[int] = None, rec_delete: List[int] = None) -> Dict[str, Any]:
        """
        将图数据转换为 API 所需的格式
        """
        api_nodes = []
        api_edges = []
        
        # 转换节点
        for node_id in nodes:
            node_type = "normal"
            if rec_insert and node_id in rec_insert:
                node_type = "recommendedInsert"
            elif rec_delete and node_id in rec_delete:
                node_type = "recommendedDelete"
            elif self.current_community and node_id in self.current_community:
                node_type = "community"
                
            # 获取作者名称，如果索引超出范围则使用默认名称
            author_name = self.authorname[node_id] if node_id < len(self.authorname) else f"Author {node_id}"
                
            api_nodes.append({
                "id": str(node_id),
                "label": author_name,
                "type": node_type
            })
            
        # 转换边
        for u, v in edges:
            if str(u) in [node["id"] for node in api_nodes] and str(v) in [node["id"] for node in api_nodes]:
                api_edges.append({
                    "from": str(u),
                    "to": str(v),
                    "type": "normal"
                })
                
        return {
            "nodes": api_nodes,
            "edges": api_edges,
            "recommendedInsert": [str(x) for x in (rec_insert or [])],
            "recommendedDelete": [str(x) for x in (rec_delete or [])]
        }
    
    def get_initial_graph(self):
        """
        获取初始图数据
        Returns:
            dict: 包含初始图数据的字典
        """
        try:
            if not hasattr(self, 'graph') or self.graph is None:
                return {
                    "status": "error",
                    "message": "图数据尚未加载"
                }
            
            # 返回简单的图统计信息
            node_count = len(self.graph.nodes())
            edge_count = len(self.graph.edges())
            
            # 返回一些示例节点和边
            sample_nodes = []
            sample_size = min(10, node_count)
            nodes = list(self.graph.nodes())
            random_nodes = random.sample(nodes, sample_size) if nodes else []
            
            for node in random_nodes:
                node_info = {
                    "id": node
                }
                
                # 处理authorname可能是列表的情况
                if hasattr(self, 'authorname'):
                    if isinstance(self.authorname, list) and node < len(self.authorname):
                        node_info["name"] = self.authorname[node]
                    elif isinstance(self.authorname, dict) and node in self.authorname:
                        node_info["name"] = self.authorname[node]
                    else:
                        node_info["name"] = f"Node {node}"
                else:
                    node_info["name"] = f"Node {node}"
                
                # 处理keywords可能是列表的情况
                if hasattr(self, 'keywords'):
                    if isinstance(self.keywords, list) and node < len(self.keywords):
                        node_info["keywords"] = self.keywords[node]
                    elif isinstance(self.keywords, dict) and node in self.keywords:
                        node_info["keywords"] = self.keywords[node]
                    else:
                        node_info["keywords"] = []
                else:
                    node_info["keywords"] = []
                    
                sample_nodes.append(node_info)
            
            # 构造初始图数据
            return {
                "status": "success",
                "data": {
                    "statistics": {
                        "node_count": node_count,
                        "edge_count": edge_count
                    },
                    "sample_nodes": sample_nodes
                }
            }
        except Exception as e:
            print(f"获取初始图数据时出错: {str(e)}")
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e)
            }
    
    def insert_node(self, node_id):
        """
        Insert a node into the current community
        Args:
            node_id: Node ID to insert
        Returns:
            dict: Updated community information and recommendations
        """
        try:
            if self.current_community is None:
                return {"status": "error", "message": "No community found"}
            
            if node_id in self.current_community:
                return {"status": "error", "message": "Node already in community"}
            
            # 调用 main.py 中的 search_community 方法，使用插入后的节点作为查询节点
            result = search_community(self.args, node_id)
            
            if result["status"] == "success":
                self.current_community = result["data"]["community"]
                return result
            else:
                return result
                
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def delete_node(self, node_id):
        """
        Delete a node from the current community
        Args:
            node_id: Node ID to delete
        Returns:
            dict: Updated community information and recommendations
        """
        try:
            if self.current_community is None:
                return {"status": "error", "message": "No community found"}
            
            if node_id not in self.current_community:
                return {"status": "error", "message": "Node not in community"}
            
            # 从当前社区中移除节点
            self.current_community.remove(node_id)
            
            # 使用社区中的另一个节点作为查询节点重新搜索
            if self.current_community:
                result = search_community(self.args, self.current_community[0])
                if result["status"] == "success":
                    self.current_community = result["data"]["community"]
                    return result
            
            return {"status": "success", "data": {"community": self.current_community, "recommendations": []}}
                
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_query_nodes(self, query: str):
        """
        根据查询文本获取匹配的节点
        Args:
            query: 查询文本
        Returns:
            List[int]: 匹配的节点ID列表
        """
        try:
            matched_nodes = []
            query = query.lower()
            
            # 在作者名列表中搜索
            for node_id, name in enumerate(self.authorname):
                if query in name.lower():
                    matched_nodes.append(node_id)
                    print(f"Found match in author name: {name} (ID: {node_id})")
            
            # 在关键词中搜索
            for node_id, keywords in self.keywords.items():
                if node_id not in matched_nodes and any(query in k.lower() for k in keywords):
                    matched_nodes.append(node_id)
                    print(f"Found match in keywords: {keywords} (ID: {node_id})")
            
            print(f"Total matched nodes: {len(matched_nodes)}")
            return matched_nodes
            
        except Exception as e:
            print(f"Error in get_query_nodes: {str(e)}")
            traceback.print_exc()
            return []

    def get_node_id_by_name(self, name, strict=False):
        """
        根据作者名查找对应的节点ID
        Args:
            name: 作者名
            strict: 为 True 时不使用默认节点回退
        Returns:
            int or None: 节点ID，如果找不到则返回None
        """
        try:
            if hasattr(self, 'authorname') and self.authorname is not None:
                # 处理authorname是列表的情况
                if isinstance(self.authorname, list):
                    for node_id, author_name in enumerate(self.authorname):
                        if name.lower() in author_name.lower():
                            return node_id
                # 处理authorname是字典的情况
                elif isinstance(self.authorname, dict):
                    for node_id, author_name in self.authorname.items():
                        if name.lower() in author_name.lower():
                            return node_id
            
            # 如果没有找到精确匹配，尝试模糊匹配
            if hasattr(self, 'authorname') and self.authorname is not None:
                if isinstance(self.authorname, list):
                    for node_id, author_name in enumerate(self.authorname):
                        if name.split()[0].lower() in author_name.lower():
                            return node_id
                elif isinstance(self.authorname, dict):
                    for node_id, author_name in self.authorname.items():
                        if name.split()[0].lower() in author_name.lower():
                            return node_id
            
            if strict:
                print(f"错误: 找不到作者 '{name}'")
                return None

            # 如果还是找不到，尝试在图中搜索第一个可用的节点
            if hasattr(self, 'graph') and self.graph is not None:
                nodes = list(self.graph.nodes())
                if nodes:
                    print(f"警告: 找不到作者 '{name}'，使用默认节点 {nodes[0]}")
                    return nodes[0]
            
            # 完全找不到时返回None
            print(f"错误: 找不到作者 '{name}'，返回None")
            return None
        except Exception as e:
            print(f"查找作者名时出错: {str(e)}")
            traceback.print_exc()
            return None 

    def load_dataset(self, dataset_name):
        """
        加载指定的数据集
        Args:
            dataset_name: 数据集名称，如'com-dblpname'
        Returns:
            bool: 加载是否成功
        """
        try:
            # 检查是否已经加载了数据集
            if hasattr(self, 'graph') and self.graph is not None and \
               hasattr(self, 'features') and self.features is not None and \
               hasattr(self, 'authorname') and self.authorname is not None:
                print(f"Dataset already loaded with {len(self.graph.nodes())} nodes, skipping...")
                return True
            
            print(f"Loading dataset: {dataset_name}")
            if "dblp" in dataset_name.lower():
                # 使用load_data加载数据
                self.args.data_set = "dblpname"
                self.args.iteration = True
                
                # 调用main.py中的load_data函数
                graph, features, target, _, _, _, authorname, keywords, mapper = load_data(self.args)
                
                # 保存数据到实例变量
                self.graph = graph
                self.features = features
                self.authorname = authorname  # 注意authorname可能是列表或字典
                self.keywords = keywords      # 确保keywords的类型与authorname匹配
                self.mapper = mapper
                
                # 初始化一些其他必要的属性
                self.current_community = []
                self.oldres = []
                
                print(f"Successfully loaded dataset {dataset_name} with {len(graph.nodes())} nodes and {len(graph.edges())} edges")
                return True
            else:
                print(f"Unsupported dataset: {dataset_name}")
                return False
        except Exception as e:
            print(f"Error loading dataset {dataset_name}: {str(e)}")
            traceback.print_exc()
            return False

    def debug_keywords(self):
        """
        打印关键词信息，用于调试
        """
        print("\n==== 关键词调试信息 ====")
        if not hasattr(self, 'keywords'):
            print("没有找到keywords属性")
            return
            
        print(f"keywords类型: {type(self.keywords).__name__}")
        
        if isinstance(self.keywords, dict):
            print(f"keywords字典大小: {len(self.keywords)}")
            # 打印前5个关键词
            sample_keys = list(self.keywords.keys())[:5]
            print("前5个关键词样例:")
            for key in sample_keys:
                print(f"  节点 {key}: {self.keywords[key]}")
        elif isinstance(self.keywords, list):
            print(f"keywords列表长度: {len(self.keywords)}")
            # 打印前5个非空关键词
            count = 0
            for i, keyword in enumerate(self.keywords):
                if keyword and count < 5:
                    print(f"  索引 {i}: {keyword}")
                    count += 1
                if count >= 5:
                    break
        else:
            print(f"不支持的keywords类型: {type(self.keywords).__name__}")
            
        # 检查一些特定节点
        test_nodes = [0, 1, 10, 100, 1000]
        print("\n测试特定节点关键词:")
        for node in test_nodes:
            if isinstance(self.keywords, dict):
                if node in self.keywords:
                    print(f"  节点 {node}: {self.keywords[node]}")
                else:
                    print(f"  节点 {node}: 不在keywords字典中")
            elif isinstance(self.keywords, list) and node < len(self.keywords):
                print(f"  节点 {node}: {self.keywords[node]}")
            else:
                print(f"  节点 {node}: 无法获取关键词")
        print("==== 调试信息结束 ====\n") 