
import asyncio
import json
import os
import sys
import networkx as nx

test_dir_path = os.path.dirname(os.path.abspath(__file__))
project_root_path = os.path.dirname(test_dir_path)

if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path)
src_path = os.path.join(project_root_path, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from src.constants import BALANCER_V3, UNISWAP_V2, UNISWAP_V3, SUSHISWAP_V2, CURVE, MAX_ROUTES,DEX_LIST,MAX_ORDERS
from src.pool_collector import get_latest_pool_data, collect_curve_pools
from src.graph_constructor import construct_pool_graph, draw_multi_layer_path_graph,draw_pool_graph, pool_graph_to_dict
from src.path_crawler import calculate_routes, get_final_route
from src.smart_order_router import filter_pools, filter_pools_best_match, find_shortest_paths, refresh_pools, route_orders, validate_all_paths, create_path_graph, path_graph_to_dict


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
read_pools_path = os.path.join(BASE_DIR, 'test_out', 'processed_pools_uniswap_v2.json')
write_graph_path = os.path.join(BASE_DIR, 'test_out', 'pools_uniswap_v2_graph.json')
filt_pools_path = os.path.join(BASE_DIR, 'test_out', f'filt_pools.json')
write_routes_path = os.path.join(BASE_DIR, 'test_out', f'routes.json')

# this is what the route_orders function do
async def all_paths(sell_symbol, sell_ID, sell_amount, buy_symbol, buy_ID):
    for dex in DEX_LIST:
        print(f"Refreshing {dex} pools")
        await refresh_pools(dex)

    filt_pools = filter_pools(sell_symbol, sell_ID, buy_symbol, buy_ID, X=20)
    result = {}
    # ---------------- select and build the pool graph ----------------
    # with open(filt_pools_path, "r", encoding="utf-8") as f:
    #     filt_pools = json.load(f)
    # with open(filt_pools_path, "w", encoding="utf-8") as f:
    #     json.dump(filt_pools, f, ensure_ascii=False, indent=2)
    # construct the pool graph
    G = construct_pool_graph(filt_pools)
    draw_pool_graph(G)

    # get the graph dict
    graph_dict = pool_graph_to_dict(G)
    result['pool_graph'] = graph_dict
    
    # ---------------- filter and build the path graph ----------------
    paths = find_shortest_paths(G, sell_symbol, buy_symbol)
    valid_paths = validate_all_paths(G, paths, sell_ID, buy_ID)
    path_graph = create_path_graph(valid_paths)
    draw_multi_layer_path_graph(path_graph)
    # get the path graph dict
    path_graph_dict = path_graph_to_dict(path_graph)
    # append the dict to the result
    result['path_graph'] = path_graph_dict

    # ---------------- calculate the routes ----------------
    routes = calculate_routes(G, valid_paths, sell_amount, sell_symbol, buy_symbol)
    with open(write_routes_path, "w", encoding="utf-8") as f:
        json.dump(routes, f, ensure_ascii=False, indent=2)

async def test_route_orders(sell_ID, sell_amount,buy_ID, exchanges, split=False):
    for dex in exchanges:
        await refresh_pools(dex)
    result = await route_orders(sell_ID, sell_amount, buy_ID, exchanges,20, split=False)
    with open(write_routes_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":

    # asyncio.run(all_paths('USDT', '0xdac17f958d2ee523a2206206994597c13d831ec7', 100, 'WETH', '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'))
    # asyncio.run(test_route_orders('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', 100,'0xdAC17F958D2ee523a2206206994597C13D831ec7',DEX_LIST))
    # asyncio.run(test_route_orders('0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2', 11,'0x6982508145454ce325ddbe47a25d4ec3d2311933',DEX_LIST))
    asyncio.run(test_route_orders('0xfaba6f8e4a5e8ab82f62fe7c39859fa577269be3', 11,'0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf',DEX_LIST))



# output_amount is
"""
bug logging:
1.
for balancer, pools with in bgt token, bgt token need been excluded
3. 
need to set up another query for querying pankeswap ticks
4.
The scaleTokenAmount function is compatible with scientific notation (such as "1.23e-5").
5.
If there is only one pool (that is, filt_pools is a dictionary), 
in fact, when traversing the keys of the dictionary, we are not dealing with the pools themselves.
6.
Handle tick crossing when tick is not initialized
7.
handle the reserve number of CPAMM pool which is not in wei 0xd75ea151a61d06868e31f8988d28dfe5e9df57b4
8.
Adjust the strategy for query ticks, query the ticks with liquidityNet not 0 when the pool value is less than 10M
9.
output_amount is 0, because the liquidity is 0 0x18645a4a6b70fdb959221be0be2091fbe17dc7c1
10.?
sell_ID=0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2&sell_amount=1&buy_ID=0x6982508145454ce325ddbe47a25d4ec3d2311933
currently liquidity is big enough, so sub side of multiple liquidityNet is still > 0,
the rest of liquidity is use from current tick to max tick or min tick ??

/ethereum/0xfaba6f8e4a5e8ab82f62fe7c39859fa577269be3/0xcbb7c0000ab88b473b1f5afd9ef808440eed33bf/100
"""


