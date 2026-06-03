from src.parser import parameter_parser
from src.subgraph import SubGraph
import torch
import random
import numpy as np
from src.pre_community import load_dblpname
import networkx as nx
from src.utils import tab_printer
from src.subgraph import LocalCommunity

# 全局变量存储数据
global_data = {
    'graph': None,
    'features': None,
    'authorname': None,
    'keywords': None,
    'mapper': None
}

def inittrain(args, seed, seedLabel, graph, target):
    posNodes = []
    negNodes = []
    allNodes = []
    length = args.subgraph_size   
    allNodes.append(seed)
    numLabel = int(length * args.train_ratio / 2)
    pos = 0
    while pos < len(allNodes) and pos < length and len(allNodes) < length:
        cnode = allNodes[pos]
        for nb in graph.neighbors(cnode):
            if nb not in allNodes and len(allNodes) < length:
                allNodes.append(nb)
        pos = pos + 1
    for node in allNodes:
        if node == seed or target[node] == seedLabel:
            posNodes.append(node)
        elif target[node] != seedLabel:
            negNodes.append(node)
    random.shuffle(posNodes)
    random.shuffle(negNodes)
    posNodes = posNodes[:numLabel]
    negNodes = negNodes[:numLabel]
    if (len(posNodes) < numLabel):
        print('e1')
        return 0, 0
    if (seed not in posNodes):
        posNodes[0] = seed
    if (len(negNodes) < numLabel):
        print('e2')
        return 0, 0
    return posNodes, negNodes   

def load_data(args):
    '''
    Load data
    '''
    seed_list = None
    train_nodes = None
    labels= None
    authorname=None
    keywords=None
    mapper=None
    if args.data_set in ["dblpname"]:
        if args.iteration:
            edge, feature, authorname, keywords, mapper = load_dblpname(data_set='com_' + args.data_set)
            graph = nx.from_edgelist(edge)
            n = graph.number_of_nodes()
            features = np.array(feature)
            target = None
            labels = None
            
            # 更新全局数据
            global_data['graph'] = graph
            global_data['features'] = features
            global_data['authorname'] = authorname
            global_data['keywords'] = keywords
            global_data['mapper'] = mapper
            
            return graph, features, target, None, None, None, authorname, keywords, mapper
    return graph, features, target, seed_list, train_nodes, labels, authorname, keywords, mapper

def get_global_data():
    '''
    获取全局数据
    Returns:
        dict: 包含图数据的字典
    '''
    return global_data

def search_community(args, query_node):
    
    '''
    Search community for a given node
    Args:
        args: Arguments containing model parameters
        query_node: Optional query node ID. If None, will use default test nodes
    Returns:
        dict: Search results containing community information and recommendations
    '''
    # 设置默认参数
    # args = parameter_parser()
    
    # 使用全局数据
    graph = global_data['graph']
    features = global_data['features']
    authorname = global_data['authorname']
    keywords = global_data['keywords']
    mapper = global_data['mapper']
    
    if graph is None:
        return {"status": "error", "message": "Failed to load data"}
    
    subg = SubGraph(args, graph, features, None, authorname, keywords)

    # Default test nodes if no query node provided
    if query_node is None:
        seed_list = [mapper[48104], mapper[48014], mapper[48014]]
        com_len_list = [1,1,1]
        target_list = []
        posNodes_list = [[mapper[48104], mapper[136292], mapper[65115]], 
                        [mapper[48014], mapper[26726]], 
                        [mapper[48014], mapper[85695], mapper[449156], mapper[66776], mapper[37198]]]
        negNodes_list = [[], [], []]
        
        for i in range(len(seed_list)):
            tg =[ 1 if t in posNodes_list[i] else 0 for t in range(len(graph.nodes))]
            target_list.append(np.array(tg)[:, np.newaxis])
        
        # Use first test case as default
        subg.target = target_list[0]
        result = subg.community_search_iteration(seed_list[0], com_len_list[0], 
                                               posNodes_list[0], negNodes_list[0], 0)
    else:
        
        # Create target vector for the query node
        target = np.zeros((len(graph.nodes), 1))
        target[query_node] = 1
        subg.target = target
        
        # Perform community search
        result = subg.community_search_iteration(query_node, 1, [query_node], [], 0)
    
    if result:
        return {
            "status": "success",
            "data": {
                "community": subg.old_res,
                "recommendations": subg.old_pos,
            }
        }
    else:
        return {"status": "error", "message": "Community search failed"}

def main():
    '''
    Command line interface for community search
    '''
    args = parameter_parser()
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    
    if args.iteration and args.data_set == 'dblpname':
        run_userstudy(args)
    else:
        print("This script is only for dblpname dataset with iteration mode")

def run_userstudy(args):
    '''
    Run community search with iteration for user study
    '''
    graph, features, target, _ ,_ ,com_list,authorname, keywords, mapper= load_data(args)
    
    subg = SubGraph(args, graph, features, target, authorname, keywords)
    itr = 0
    
    sugpaper = "Suggested query papers:\n 1. Lei Chen, Yafei Li, [Jianliang Xu], Christian S. Jensen: \n Direction-Aware Why-Not Spatial Keyword Top-k Queries. \n 2. Jiaxin Jiang, Peipei Yi, [Byron Choi], Zhiwei Zhang, Xiaohui Yu: \n Privacy-Preserving Reachability Query Services for Massive Networks.\n 3. [Xin Huang], Hong Cheng, Rong-Hua Li, Lu Qin, Jeffrey Xu Yu: \n Top-K structural diversity search in large networks \n 4. Geoffrey E. Hinton, Oriol Vinyals, Jeffrey Dean: Distilling the Knowledge in a Neural Network \n5. Jiawei Han, Micheline Kamber, Jian Pei: \n Data Mining: Concepts and Techniques. \n6. Xin Yao, Zhenyu Yang, Ke Tang: \n Large scale evolutionary optimization using cooperative coevolution \n"
    
    while itr < args.seed_cnt:
        seed_list = [mapper[48104], mapper[48014], mapper[48014]]
        com_len_list = [1,1,1]
        target_list = []
        posNodes_list = [[mapper[48104], mapper[136292], mapper[65115]], 
                        [mapper[48014], mapper[26726]], 
                        [mapper[48014], mapper[85695], mapper[449156], mapper[66776], mapper[37198]]]
        negNodes_list = [[], [], []]
        
        for i in range(len(seed_list)):
            tg =[ 1 if t in posNodes_list[i] else 0 for t in range(len(graph.nodes))]
            target_list.append(np.array(tg)[:, np.newaxis])
        
        print(sugpaper)
        q = int(input("Enter a number to select the query paper:"))-1
        if q < 0:
            subg.user_study_eva(itr)
            break
        subg.target = target_list[q]
        isOK = subg.community_search_iteration(seed_list[q], com_len_list[q], 
                                             posNodes_list[q], negNodes_list[q], itr)
        itr = itr + isOK
    
    print("Search End. Thank you for your participant.")

if __name__ == "__main__":	
    main()
