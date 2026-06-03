from heapq import heappop, heappush, heapify, nlargest, nsmallest
from collections import deque
import random
import networkx as nx
import time
from . import utils

class PPRRecommend(object):

    def __init__(self, args, upgraph):
        self.args = args
        self.upgraph = upgraph
        self.rec_res = []
        self._callback = None  # 使用私有变量存储回调
        print("PPRRecommend initialized")
        
        # 用于异步交互的状态变量
        self.waiting_for_user = False
        self.user_choice_action = "none"  # 可能的值: "insert", "delete", "confirm", "none"
        self.user_choice_position = -1
        self.current_rec_insert_nodes = []
        self.current_rec_delete_nodes = []
        self.current_seed = None
        self.current_round = None

        # 保存推荐的节点，供API使用
        self.rec_insert_nodes = []
        self.rec_delete_nodes = []

    def set_callback(self, callback_function):
        """
        设置回调函数
        Args:
            callback_function: 回调函数，用于更新前端状态
        """
        self._callback = callback_function
        print(f"Callback设置完成: {self._callback is not None}")

    @property
    def callback(self):
        """获取回调函数"""
        return self._callback

    def wait_for_user_choice(self):
        """
        等待用户选择
        这个方法会阻塞执行，直到用户通过API做出选择
        """
        import time
        
        # 设置超时参数
        timeout_seconds = 60  # 60秒超时
        start_time = time.time()
        
        print("等待用户选择...")
        while self.waiting_for_user:
            # 检查是否超时
            if time.time() - start_time > timeout_seconds:
                print("等待用户选择超时，自动继续")
                self.waiting_for_user = False
                self.user_choice_action = "confirm"  # 默认确认
                break
                
            time.sleep(0.5)  # 休眠500ms，避免CPU占用过高
        
        print(f"收到用户选择: {self.user_choice_action}, 位置: {self.user_choice_position}")
        return

    def apply_user_choice(self, action, node_id=None):
        """
        应用用户选择
        Args:
            action: 操作类型，"insert", "delete", "confirm" 或 "none"
            node_id: 节点ID，如果操作是insert或delete
        Returns:
            bool: 成功返回True，失败返回False
        """
        try:
            print(f"正在应用用户选择: {action}, 节点ID: {node_id}")
            
            # 设置操作类型
            self.user_choice_action = action
            
            if action == "insert" and node_id is not None:
                # 查找节点在推荐插入节点列表中的位置
                try:
                    position = self.rec_insert_nodes.index(node_id)
                    self.user_choice_position = position
                    print(f"找到插入节点位置: {position}")
                except ValueError:
                    print(f"无法在推荐插入列表中找到节点 {node_id}")
                    return False
            elif action == "delete" and node_id is not None:
                # 查找节点在推荐删除节点列表中的位置
                try:
                    position = self.rec_delete_nodes.index(node_id)
                    self.user_choice_position = position
                    print(f"找到删除节点位置: {position}")
                except ValueError:
                    print(f"无法在推荐删除列表中找到节点 {node_id}")
                    return False
            elif action == "confirm":
                # 确认操作，不需要节点ID
                self.user_choice_position = -1
            else:
                print(f"无效操作: {action}")
                return False
            
            # 通知等待的线程继续执行
            self.waiting_for_user = False
            return True
        except Exception as e:
            import traceback
            print(f"应用用户选择时出错: {str(e)}")
            traceback.print_exc()
            return False

    def userinter(self, seed, round, rec_pos_nodes, rec_neg_nodes):    
        """
        User interaction method for recommendation process
        Args:
            seed: Seed node ID
            round: Current iteration round
            rec_pos_nodes: Recommended nodes to insert
            rec_neg_nodes: Recommended nodes to delete
        Returns:
            int: Status code (1 for success)
        """
        try:
            print(f"Round {round}: Processing recommendations...")
            
            # Initialize variables if first run
            if round == 1:
                self.chospos = []
                self.chosneg = []
            
            # Log recommended nodes
            utils.printlog("Recommended authors for insertion: \n 0. No insertion.")
            for i, node in enumerate(rec_pos_nodes):
                utils.printlog(str(i+1)+'.'+self.upgraph.authorname[node]+ ' '+self.upgraph.keywords[node])
            # chospos = int(input("Press number to choose the insertion author:"))-1

            utils.printlog("Recommended authors for deletion: \n 0. No deletion.")
            for i, node in enumerate(rec_neg_nodes):
                utils.printlog(str(i+1)+'.'+self.upgraph.authorname[node]+ ' '+self.upgraph.keywords[node])
            # chosneg = int(input("Press number to choose the deletion author:"))-1

            # Save current recommendations for access by API
            self.rec_insert_nodes = rec_pos_nodes
            self.rec_delete_nodes = rec_neg_nodes
            # 生成可视化数据
            print("\n===== 调试: userinter方法中生成可视化数据 =====")
            print(f"当前轮次: {round}")
            print(f"主查询节点: {seed}")
            print(f"推荐插入节点数量: {len(rec_pos_nodes)}")
            print(f"推荐删除节点数量: {len(rec_neg_nodes)}")
            not_insert_nodes = set(self.upgraph.oldpos[:]) - set(self.upgraph.oldres[:])
            community_nodes = self.upgraph.oldres[:] + list(not_insert_nodes)
            print(f"社区节点数量: {len(community_nodes)}")
            # 生成可视化数据
            visualization_data = self.get_2hop_neighbors(rec_pos_nodes, rec_neg_nodes, community_nodes)
            # 保存当前状态
            self.current_seed = seed
            self.current_round = round
            print("\n===== 调试: 准备调用回调函数 =====")
            # 尝试多种方式获取状态回调
            callback_used = False
            # 1. 尝试从upgraph获取state_callback（如果是ICSGNNWrapper实例）
            if hasattr(self.upgraph, 'state_callback') and self.upgraph.state_callback is not None:
                print(f"从upgraph找到状态回调，准备调用")
                try:
                    result = self.upgraph.state_callback(visualization_data)
                    print(f"upgraph回调调用成功，返回结果类型: {type(result).__name__}")
                    callback_used = True
                except Exception as e:
                    print(f"调用upgraph回调时出错: {str(e)}")
            # 2. 如果未成功，尝试获取全局icsgnn_instance
            if not callback_used:
                try:
                    from src.api_routes import icsgnn_instance
                    if hasattr(icsgnn_instance, 'state_callback') and icsgnn_instance.state_callback is not None:
                        print(f"从全局icsgnn_instance找到状态回调，准备调用")
                        try:
                            result = icsgnn_instance.state_callback(visualization_data)
                            print(f"全局icsgnn_instance回调调用成功，返回结果类型: {type(result).__name__}")
                            callback_used = True
                        except Exception as e:
                            print(f"调用全局回调时出错: {str(e)}")
                except Exception as e:
                    print(f"获取全局icsgnn_instance失败: {str(e)}")
            # 3. 最后尝试使用本地回调
            if not callback_used:
                print("无法找到外部状态回调，尝试使用本地回调")
                if self.callback:
                    try:
                        result = self.callback(visualization_data)
                        print(f"本地回调调用成功，返回结果类型: {type(result).__name__}")
                        callback_used = True
                    except Exception as e:
                        print(f"调用本地回调时出错: {str(e)}")
            # 4. 如果所有方法都失败，记录错误
            if not callback_used:
                print("警告：无法调用任何回调函数，可视化数据未发送")
            print("===== 调试: 回调处理完成 =====\n")
            # Wait for user choice - 确保标志被设置为True
            print("Waiting for user choice...")
            self.waiting_for_user = True
            self.wait_for_user_choice()  # 这会阻塞直到用户做出选择
            # Process user choice
            action = self.user_choice_action
            position = self.user_choice_position
            print(f"User action: {action}, Position: {position}")
            # Apply user choice
            if action == "insert" and position < len(rec_pos_nodes):
                node_to_insert = rec_pos_nodes[position]
                print(f"Adding node {node_to_insert} to positive nodes")
                self.chospos.append(node_to_insert)
            elif action == "delete" and position < len(rec_neg_nodes):
                node_to_delete = rec_neg_nodes[position]
                print(f"Adding node {node_to_delete} to negative nodes")
                self.chosneg.append(node_to_delete)
            elif action == "confirm":
                print("User confirmed without modification")
            else:
                    print(f"Invalid action or position: {action}, {position}")

            # Update graph based on choices
            self.upgraph.update(round, self.chospos[:], self.chosneg[:])
            # Reset user choice variables for next round
            self.waiting_for_user = False
            self.user_choice_action = "none"
            self.user_choice_position = -1

            return 1
        except Exception as e:
            import traceback
            print(f"Error in userinter: {str(e)}")
            traceback.print_exc()
            self.waiting_for_user = False  # 确保出错时也重置等待状态
            return 0
    
    def ppr_algo(self, tag, allResNodes, allNodes):
        '''
        Personalized Pagerank recommend posnodes and negnodes
        '''
        # for very small candidate
        if len(allNodes)-len(allResNodes) < 11:
            begin_time = time.time()
            rec_all_candidate = [x for x in allNodes if x not in allResNodes]
            rec_time = time.time() - begin_time
            self.rec_res.append(rec_time)
            return rec_all_candidate
        
        sg_nodes = {}
        sg_edges = {}
        
        subgraph = nx.Graph()
        subgraph.add_nodes_from(allNodes)
        for i in range(len(allNodes)):
            for j in range(i):
                if ((allNodes[i], allNodes[j]) in self.upgraph.graph.edges) or ((allNodes[j], allNodes[i]) in self.upgraph.graph.edges):
                    subgraph.add_edge(allNodes[i], allNodes[j])

        # print("size of nodes %d size of edges %d" % (len(subgraph.nodes), len(subgraph.edges)))
        sg_nodes[0] = [node for node in sorted(subgraph.nodes())]
        mapper = {node: i for i, node in enumerate(sorted(sg_nodes[0]))}
        rmapper = {i: node for i, node in enumerate(sorted(sg_nodes[0]))}
        sg_edges[0] = [[mapper[edge[0]], mapper[edge[1]]] for edge in subgraph.edges()]
        sg_allResNodes = [mapper[node] for node in allResNodes]
        sg_allNodes = [mapper[node] for node in allNodes]
        
        begin_time = time.time()
        # Mark all the vertices as not visited
        # visited = [False] * (len(allNodes))
        level = [-1] * (len(allNodes))
        page_rank = [0.0] * (len(allNodes))
        # Create a queue for BFS
        queue = deque()
        can_pos_nodes = set()
        visited = set(sg_allResNodes)
 
        # Mark the source node as
        # visited and enqueue it
        for i in sg_allResNodes[:]:
            # visited[i] = True
            level[i] = 0
            queue.append(i)
        
        '''Directed Graph part'''
        level_max = 0
        while queue:
 
            # Dequeue a vertex from
            # queue and print it
            s = queue.popleft()
            level_now = level[s] + 1

            # Get all adjacent vertices of the
            # dequeued vertex s. If a adjacent
            # has not been visited, then mark it
            # visited and enqueue it
            for nb in subgraph.neighbors(rmapper[s]):
                sg_nb = mapper[nb]
                if sg_nb not in visited:
                    can_pos_nodes.add(sg_nb)
                    queue.append(sg_nb)
                    visited.add(sg_nb)
                    # visited[sg_nb] = True
                    level[sg_nb] = level_now
                    if level_now>level_max:
                        level_max = level_now

        DG = nx.DiGraph()
        DG.add_nodes_from(sg_allNodes)
        for [i, j] in sg_edges[0]:
            if level[i] > level[j]:
                DG.add_edge(j, i)
            elif level[i] < level[j]:
                DG.add_edge(i, j)
            elif level[i] > 0:
                DG.add_edge(i, j)
                DG.add_edge(j, i)
        
        '''PageRank part'''
            
        damping_factor = 0.85
        max_iterations = level_max + 1
        min_delta = 0.0001
        # damping_value = round((1.0 - damping_factor) / len(allNodes), 6)
        damping_value = (1.0 - damping_factor) / (len(allNodes)-len(allResNodes)+1)
        out_deg = DG.out_degree()
        sumRootOutNbSiz = 0
        for i in sg_allResNodes:
            sumRootOutNbSiz += out_deg[i]
        for i in sg_allResNodes:
            if out_deg[i]>0:
                # page_rank[i] = out_deg[i]
                # if self.args.data_set == 'dblpname':
                # else:
                page_rank[i] = damping_value + damping_factor*out_deg[i]/sumRootOutNbSiz
        out_deg_dict = {node: deg for node, deg in DG.out_degree()}
    
        # pos = 0

        for _ in range(max_iterations):
            # pos = pos + 1
            old_pagerank = page_rank.copy()
            change = 0.0
            for i in can_pos_nodes:
                rank = damping_value
                rank += damping_factor * sum(old_pagerank[j] / out_deg_dict[j] for j in DG.predecessors(i))
                # for j in DG.predecessors(i):
                    # rank = rank + damping_factor * page_rank[j] / out_deg[j]
                change += abs(old_pagerank[i] - rank)
                page_rank[i] = rank
                # page_rank[i] = round(rank, 6)
            if change < min_delta:
                break
        
        
        for i in sg_allResNodes:
            page_rank[i] = 1.0
            
        if tag == 0:
            if self.args.data_set == 'dblpname':
                page_rank = [1.0 / i for i in page_rank]
            else:
                page_rank = [-1 * i for i in page_rank]

        '''Vertex Cover part'''
        cover_dict = {}
        cover_attr_dict = {}
        covered_set = set()
        covered_attr = set()
        attr_set = set()
        ppr_gain = []
        noattr_gain = []
        heapify(ppr_gain)
        heapify(noattr_gain)
        for i in can_pos_nodes:
            rank = page_rank[i]
            cover_set = {i}
            if self.args.data_set == 'dblpname':
               cover_attr = {self.upgraph.keywords[rmapper[i]].split("&",1)[0]}
            for nb in subgraph.neighbors(rmapper[i]):
                sg_nb = mapper[nb]
                rank = rank + page_rank[sg_nb]
                cover_set.add(sg_nb)
                if self.args.data_set == 'dblpname':
                    cover_attr.add(self.upgraph.keywords[nb].split("&",1)[0])
            if self.args.data_set != 'dblpname':
                heappush(ppr_gain, (-1 * rank, 0, i))
                cover_dict[i] = cover_set
            else:
                rank = (rank * (len(cover_attr)))/(rank+(len(cover_attr)))
                heappush(ppr_gain, (-1 * rank, 0, i))
                cover_dict[i] = cover_set
                cover_attr_dict[i] = cover_attr

        rec_num = 0
        rec_budget = 10
        rec_pos_nodes = []
        while rec_num < rec_budget and len(ppr_gain) > 0:
            vg = heappop(ppr_gain)
            if (vg[1] < rec_num):
                cover_set = cover_dict[vg[2]]
                remove_set = cover_set & covered_set
                rank = -1 * vg[0]
                if len(remove_set) > 0:
                    new_cover_set = cover_set - remove_set
                    cover_dict[vg[2]] = new_cover_set
                    for v in remove_set:
                        rank = rank - page_rank[v]
                if self.args.data_set != 'dblpname':
                    heappush(ppr_gain, (-1 * rank, rec_num, vg[2]))
                else:
                    cover_attr = cover_attr_dict[vg[2]]
                    remove_attr = cover_attr & covered_attr
                    new_cover_attr = set()
                    if len(remove_attr) > 0:
                        new_cover_attr = cover_attr - remove_attr
                        cover_attr_dict[vg[2]] = new_cover_attr
                    newrank = (rank * (len(new_cover_attr)))/(rank+(len(new_cover_attr)))
                    if(len(new_cover_attr)>0):
                        heappush(ppr_gain, (-1 * newrank, rec_num, vg[2]))
                    else:
                        # newrank = (rank * 0.9)/(rank+0.9)
                        # heappush(ppr_gain, (-1 * newrank, rec_num, vg[2]))
                        heappush(noattr_gain, (-1 * rank, 0, vg[2]))
            else:
                rec_num = rec_num + 1
                rec_pos_nodes.append(rmapper[vg[2]])
                covered_set_cp = covered_set
                covered_set = covered_set_cp.union(cover_dict[vg[2]])
            if self.args.data_set == 'dblpname':
                covered_attr_cp = covered_attr
                covered_attr = covered_attr_cp.union(cover_attr_dict[vg[2]])
        
        if self.args.data_set == 'dblpname':
            while rec_num < rec_budget and len(noattr_gain) > 0:
                vg = heappop(noattr_gain)
                if (vg[1] < rec_num):
                    cover_set = cover_dict[vg[2]]
                    remove_set = cover_set & covered_set
                    rank = -1 * vg[0]
                    if len(remove_set) > 0:
                        new_cover_set = cover_set - remove_set
                        cover_dict[vg[2]] = new_cover_set
                        for v in remove_set:
                            rank = rank - page_rank[v]
                    heappush(noattr_gain, (-1 * rank, rec_num, vg[2]))
                else:
                    rec_num = rec_num + 1
                    rec_pos_nodes.append(rmapper[vg[2]])
                    covered_set_cp = covered_set
                    covered_set = covered_set_cp.union(cover_dict[vg[2]])
                
        rec_time = time.time() - begin_time
        self.rec_res.append(rec_time)
        
        return rec_pos_nodes
    def random_recommend(self, seed, round):
        '''
        Random recommend posnodes and negnodes
        '''
        can_neg_nodes = []
        can_pos_nodes = []
        begin_time = time.time()
        for node in self.upgraph.allnode:
            if node not in self.upgraph.oldpos and node not in self.upgraph.oldneg:
                can_pos_nodes.append(node)
        random.shuffle(can_pos_nodes)
        rec_pos_nodes = can_pos_nodes[:10]
        rec_time = time.time() - begin_time
        self.rec_res.append(rec_time)

        begin_time = time.time()
        for node in self.upgraph.allnode:
            if node in self.upgraph.oldres and node not in self.upgraph.oldneg and node not in self.upgraph.oldpos:
                can_neg_nodes.append(node)
        random.shuffle(can_neg_nodes)
        rec_neg_nodes = can_neg_nodes[:10]
        rec_time = time.time() - begin_time
        self.rec_res.append(rec_time)
        self.upgraph.recnodes[round-1] = {0 : rec_pos_nodes, 1 : rec_neg_nodes}
        if self.args.data_set == 'dblpname':
            isok = self.userinter(seed, round, rec_pos_nodes, rec_neg_nodes)
        else:
            isok = self.evaluate_recommend(seed, round, rec_pos_nodes, rec_neg_nodes)
        return isok

    def ppr_recommend(self, seed, round):
        """
        Recommend nodes using PPR algorithm with user interaction
        Args:
            seed: Seed node ID
            round: Current iteration round
        Returns:
            int: Status code (1 for success)
        """
        try:
            # Get non-inserted positive nodes
            not_insert_nodes = set(self.upgraph.oldpos[:]) - set(self.upgraph.oldres[:])

                # Get non-removed negative nodes
            not_remove_nodes = set(self.upgraph.oldneg[:]) & set(self.upgraph.oldres[:])

                # Get recommended positive nodes (insertion candidates)
            rec_pos_nodes = self.ppr_algo(1, self.upgraph.oldres[:] + list(not_insert_nodes), self.upgraph.allnode[:])

                # Get recommended negative nodes (deletion candidates)
            rec_neg_nodes = self.ppr_algo(0, self.upgraph.oldpos[:], list(set(self.upgraph.oldres[:]) - not_remove_nodes) + list(not_insert_nodes))
            
            # Save current recommendations for this round
            self.upgraph.recnodes[round-1] = {0: rec_pos_nodes, 1: rec_neg_nodes}

            # Process user interaction
            if self.args.data_set == 'dblpname':
                isok = self.userinter(seed, round, rec_pos_nodes, rec_neg_nodes)
            else:
                isok = self.evaluate_recommend(seed, round, rec_pos_nodes, rec_neg_nodes)
            
            return isok
        except Exception as e:
            import traceback
            print(f"Error in ppr_recommend: {str(e)}")
            traceback.print_exc()
            return 0

    def get_2hop_neighbors(self, rec_insert_nodes, rec_delete_nodes, community_nodes):
        """
        获取社区节点的2-hop邻居信息
        Returns:
            dict: 包含节点和边信息的字典
        """
        # 获取社区节点
        query_nodes = set(self.upgraph.oldpos)
        
        # 获取2-hop邻居
        two_hop_nodes = set()
        for node in community_nodes:
            # 1-hop邻居
            for neighbor in self.upgraph.graph.neighbors(node):
                two_hop_nodes.add(neighbor)
                # 2-hop邻居
                for second_neighbor in self.upgraph.graph.neighbors(neighbor):
                    two_hop_nodes.add(second_neighbor)
        
        # 限制节点数量
        if len(two_hop_nodes) > 500:
            two_hop_nodes = set(list(two_hop_nodes)[:500])
        
        # 移除已经在其他集合中的节点
        two_hop_nodes = two_hop_nodes - set(community_nodes) - set(query_nodes) - set(rec_insert_nodes) - set(rec_delete_nodes)
        
        # 获取所有相关节点
        all_nodes = list(set(community_nodes) | set(query_nodes) | set(rec_insert_nodes) | set(rec_delete_nodes) | two_hop_nodes)
        
        # 构建节点信息
        nodes = []
        seed_nodes = set(query_nodes)
        if hasattr(self.upgraph, 'oldpos') and self.upgraph.oldpos:
            seed_nodes = set(self.upgraph.oldpos)

        for node in all_nodes:
            node_type = "normal"
            if node in seed_nodes:
                node_type = "query"
            elif node in community_nodes:
                node_type = "community"
            elif node in rec_insert_nodes:
                node_type = "insert"
            elif node in rec_delete_nodes:
                node_type = "delete"
                
            nodes.append({
                "id": str(node),
                "label": self.upgraph.authorname[node],
                "type": node_type,
                "keywords": self.upgraph.keywords[node]
            })
        
        # 构建边信息
        edges = []
        for i in range(len(all_nodes)):
            for j in range(i + 1, len(all_nodes)):
                if (all_nodes[i], all_nodes[j]) in self.upgraph.graph.edges:
                    edge_type = "normal"
                    # 如果边的两个端点都在社区中，则为社区边
                    if all_nodes[i] in community_nodes and all_nodes[j] in community_nodes:
                        edge_type = "community"
                    edges.append({
                        "source": str(all_nodes[i]),
                        "target": str(all_nodes[j]),
                        "type": edge_type
                    })
        
        result = {
                "status": "waiting_for_user_input",
                "data": {
                    "nodes": nodes,
                    "edges": edges,
                    "recommendInsert": [str(x) for x in rec_insert_nodes],
                    "recommendDelete": [str(x) for x in rec_delete_nodes],
                    "round": self.current_round if hasattr(self, 'current_round') else round
                }
        }
        
        # 调试日志：输出生成的可视化数据结构
        print("\n===== 调试: get_2hop_neighbors生成的可视化数据 =====")
        print(f"数据状态: {result['status']}")
        print(f"节点数量: {len(result['data']['nodes'])}")
        print(f"边数量: {len(result['data']['edges'])}")
        print(f"推荐插入节点数量: {len(result['data']['recommendInsert'])}")
        print(f"推荐删除节点数量: {len(result['data']['recommendDelete'])}")
        
        # 检查节点数据格式
        if len(result['data']['nodes']) > 0:
            print("\n节点示例:")
            sample_node = result['data']['nodes'][0]
            print(f"  ID: {sample_node.get('id')}")
            print(f"  标签: {sample_node.get('label')}")
            print(f"  类型: {sample_node.get('type')}")
            print(f"  关键词: {sample_node.get('keywords')}")
            
            # 检查关键词存在情况
            nodes_with_keywords = sum(1 for node in result['data']['nodes'] if 'keywords' in node and node['keywords'])
            print(f"\n具有关键词的节点: {nodes_with_keywords}/{len(result['data']['nodes'])}")
            
            # 如果有关键词的节点示例
            if nodes_with_keywords > 0:
                for node in result['data']['nodes']:
                    if 'keywords' in node and node['keywords']:
                        print(f"具有关键词的节点示例: ID={node['id']}, 关键词={node['keywords']}")
                        break
        
        # 检查边数据格式
        if len(result['data']['edges']) > 0:
            print("\n边示例:")
            sample_edge = result['data']['edges'][0]
            print(f"  源节点: {sample_edge.get('source')}")
            print(f"  目标节点: {sample_edge.get('target')}")
            print(f"  类型: {sample_edge.get('type')}")
        
        print("======================================\n")
        
        return result

    def get_keywords_for_node(self, node):
        """
        获取节点的关键词
        Args:
            node: 节点ID
        Returns:
            list: 关键词列表
        """
        try:
            # 确保node是整数类型
            if isinstance(node, str):
                try:
                    node = int(node)
                except ValueError:
                    return []  # 如果无法转换为整数，返回空列表
            
            # 从upgraph获取关键词
            if hasattr(self.upgraph, 'keywords'):
                if isinstance(self.upgraph.keywords, dict) and node in self.upgraph.keywords:
                    keyword_str = self.upgraph.keywords[node]
                    if isinstance(keyword_str, str):
                        if "&" in keyword_str:
                            return [kw.strip() for kw in keyword_str.split("&")]
                        elif "," in keyword_str:
                            return [kw.strip() for kw in keyword_str.split(",")]
                        else:
                            return [keyword_str.strip()]
                    elif isinstance(keyword_str, list):
                        return keyword_str
            
            # 直接从全局实例获取
            try:
                from src.api_routes import icsgnn_instance
                if hasattr(icsgnn_instance, 'keywords') and isinstance(icsgnn_instance.keywords, dict) and node in icsgnn_instance.keywords:
                    keyword_str = icsgnn_instance.keywords[node]
                    if isinstance(keyword_str, str):
                        if "&" in keyword_str:
                            return [kw.strip() for kw in keyword_str.split("&")]
                        elif "," in keyword_str:
                            return [kw.strip() for kw in keyword_str.split(",")]
                        else:
                            return [keyword_str.strip()]
            except:
                pass
                
            # 找不到关键词，返回空列表
            return []
        except Exception as e:
            print(f"获取节点{node}关键词时出错: {str(e)}")
            return []