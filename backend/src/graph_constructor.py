'''
This script constructs a graph of Uniswap pools which were collected from pool_collector.py.
'''

# third party imports
import networkx as nx
# import matplotlib.pyplot as plt
import matplotlib.pyplot as plt

# standard library imports
import json

# create a graph where each pool is a node
def construct_pool_graph(pools: json) -> nx.classes.graph.Graph:
    # create a graph
    G = nx.DiGraph()
    # add a node for each pool
    for pool in pools:
        '''# if at least one of the pool's symbols are tokens A or B
        if pool['token0']['symbol'] == tokenA or pool['token0']['symbol'] == tokenB or pool['token1']['symbol'] == tokenA or pool['token1']['symbol'] == tokenB:'''
        # check if the pool has reserveUSD or liquidityUSD
        if 'trackedReserveETH' in pool:
            metric = pool['trackedReserveETH'] 
        elif 'liquidityUSD' in pool:
            metric = pool['liquidityUSD']
        elif 'totalValueLockedUSD' in pool:
            metric = pool['totalValueLockedUSD']
        elif 'liquidity' in pool:
            metric = pool['liquidity']
        elif 'reserveUSD' in pool:
            metric = pool['reserveUSD']
        # make the node SYMBOL1_SYMBOL2_ID
        G.add_node(
            pool['token0']['id'] + '_' + pool['token1']['id'] + '_' + pool['id'], 
            id=pool['id'], 
            metric=metric,
            token0=pool['token0'],
            token1=pool['token1'],
            price_impact=0,
            pool=pool)

    # connect the nodes if they share a token
    for node in list(G.nodes):
        for node2 in list(G.nodes):
            # check for common tokens
            if G.nodes[node]['token0']['id'] == G.nodes[node2]['token0']['id'] or G.nodes[node]['token0']['id'] == G.nodes[node2]['token1']['id'] or G.nodes[node]['token1']['id'] == G.nodes[node2]['token0']['id'] or G.nodes[node]['token1']['id'] == G.nodes[node2]['token1']['id']:
                # add an edge in both directions
                G.add_edge(node, node2)
                G.add_edge(node2, node)

    # remove nodes that can't form a path
    for node in list(G.nodes):
        if len(list(G.edges(node))) < 3:
            G.remove_node(node)

    # return the graph
    return G

def pool_graph_to_dict(G: nx.DiGraph()) -> dict:
    return nx.to_dict_of_lists(G)


def draw_pool_graph(G: nx.DiGraph):

    plt.figure(figsize=(12, 12)) # Increase figure size for better visibility
    pos = nx.circular_layout(G)

    node_sizes = [
        float(G.nodes[node].get("metric", 1)) ** 0.5
        for node in G.nodes
    ]

    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color='skyblue', alpha=0.8)
    nx.draw_networkx_edges(G, pos, width=0.5, edge_color='gray', alpha=0.5, arrows=False) # Add arrows for DiGraph

    # token0/token1
    labels = {
        node: node.split('_')[0] + '/' + node.split('_')[1]
        for node in G.nodes
    }
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_color='black')

    # --- Display ---

    plt.tight_layout() # Adjust layout to prevent labels overlapping figure boundaries
    plt.savefig("Pool Graph.png") # Display the plot


def draw_multi_layer_path_graph(G: nx.Graph):
    # 获取所有节点的 layer 信息
    layers = nx.get_node_attributes(G, 'layer')

    # 使用 multipartite layout 自动布局每层
    pos = nx.multipartite_layout(G, subset_key='layer')

    # 设置图形尺寸
    plt.figure(figsize=(12, 6))
    node_sizes = [
        float(G.nodes[node].get("metric", 1)) ** 0.5
        for node in G.nodes
    ]

    nx.draw_networkx_nodes(G, pos, node_color='skyblue', node_size=200)
    nx.draw_networkx_edges(G, pos, width=0.5, edge_color='green', alpha=0.5, arrows=False)

    # 绘制标签：使用 symbol+id 字段，或者 node 名字
    labels = {node: f"{G.nodes[node]['symbol']}\n{G.nodes[node]['id']}" for node in G.nodes}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=8)

    # 去掉坐标轴
    plt.axis('off')

    # 展示图形
    plt.title("Multi-layer Path Graph", fontsize=14)
    plt.tight_layout()
    plt.savefig("Multi-layer Path Graph.png") # Display the plot