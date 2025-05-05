'''
This module acts as the central orchestrator for the smart order router.
It coordinates fetching pool data, constructing graphs, finding paths,
calculating route outcomes, and potentially splitting trades across multiple paths.
'''


from pool_collector import (
    get_latest_pool_data,       
    collect_curve_pools        
)
from graph_constructor import construct_pool_graph, pool_graph_to_dict
from pathfinder import find_shortest_paths, validate_all_paths, create_path_graph, path_graph_to_dict
from path_crawler import calculate_routes, get_final_route

# ------------------------ Third Party Imports ------------------------
import logging
from constants import PANCAKESWAP_V3, UNISWAP_V2, UNISWAP_V3, SUSHISWAP_V2, CURVE, BALANCER_V3, MAX_ROUTES, UNISWAPV3_ENDPOINT
from constants import DEX_LIST, BLACKLISTED_TOKENS, DEX_ORDER_BY, DEX_METRIC
from heapq import merge
import json
import time

from slippage.type_pool.uni_v3.batchTicks import add_ticks

# ------------------------ Global In-Memory Pool Cache ------------------------
# Flat dictionary mapping unique key to pool data for quick lookups
pool_dict = {}

# Nested dictionary as primary cache, organized by DEX protocol
pools = {
    exch: {
        'metric': DEX_METRIC[exch],
        'pools': []
    } for exch in DEX_LIST
}


# ------------------------ Pool Data Refresh Function ------------------------
async def refresh_pools(protocol: str):
    global pools
    global pool_dict

    # ------------------------ Special Handling for Curve ------------------------
    if protocol == CURVE:
        new_curve_pools = await collect_curve_pools()
        for pool in new_curve_pools:
            token0_id = pool['token0']['id']
            token1_id = pool['token1']['id']
            key = f"{pool['id']}_{token0_id}_{token1_id}"
            pool_dict[key] = pool
            pools[protocol]['pools'].append(pool)

        if protocol in pools:
             print(f'{protocol} pool count: {len(pools[protocol]["pools"])}')
        return
    
    # ------------------------ Special Handling for Balancer V3 ------------------------
    if protocol == BALANCER_V3:
        new_balancer_v3_pools = await get_latest_pool_data(protocol=BALANCER_V3, X=260)
        for pool in new_balancer_v3_pools:
            token0_id = pool['token0']['id']
            token1_id = pool['token1']['id']
            key = f"{pool['id']}_{token0_id}_{token1_id}"
            pool_dict[key] = pool
            pools[protocol]['pools'].append(pool)

        if protocol in pools:
             print(f'{protocol} pool count: {len(pools[protocol]["pools"])}')
        return

    # ------------------------ General Pool Fetching Logic (for other DEXs) ------------------------
    new_pools = []
    metric_to_use = pools[protocol]['metric']
    last_pool_metric = None

    for i in range(0, 1):
        batch_size = 1000
        max_pools = 1000

        for skip in range(0, max_pools, batch_size):
            new_pools = await get_latest_pool_data(protocol=protocol, X=batch_size, skip=skip, max_metric=last_pool_metric)

            if new_pools:
                for pool in new_pools:
                    token0_id = pool['token0']['id']
                    token1_id = pool['token1']['id']
                    key = f"{pool['id']}_{token0_id}_{token1_id}"
                    pool_dict[key] = pool
                    pools[protocol]['pools'].append(pool)

                last_pool = new_pools[-1]
                last_pool_metric = float(last_pool[metric_to_use])
                logging.info(
                    f'{protocol} pool count: {len(pools[protocol]["pools"])} | last pool metric: {metric_to_use} : {last_pool_metric}'
                )
    logging.info("Total pairs collected: "+str(len(pool_dict)))

def merge_and_sort_all_pools(pools_data):
    """
    Merges pools from all protocols and sorts them based on their specific metric.
    Returns:
        A single list containing all pool dictionaries, sorted in descending
        order according to each pool's protocol-specific metric.
    """
    all_pools_with_metric = []

    for protocol, data in pools_data.items():
        metric_key = data.get('metric')
        pool_list = data.get('pools', [])

        if not metric_key:
            print(f"Warning: Metric key not defined for protocol {protocol}. Skipping its pools.")
            continue

        for pool in pool_list:
            if isinstance(pool, dict):
                 all_pools_with_metric.append((pool, metric_key))
            else:
                 print(f"Warning: Found non-dictionary item in {protocol} pools: {pool}")

    try:
        sorted_pools_with_metric = sorted(
            all_pools_with_metric,
            key=lambda item: float(item[0].get(item[1], '0')),
            reverse=True
        )
    except ValueError as e:
        print(f"Error converting metric value to float during sorting: {e}")

    merged_sorted_pools = [item[0] for item in sorted_pools_with_metric]

    return merged_sorted_pools


# ------------------------ Pool Filtering (Default Strategy) ------------------------
def filter_pools(sell_ID: str, sell_amount: float, buy_ID: str, exchanges=None, X: int = 20) -> list:
    filtered_pools = []

    full_pools = merge_and_sort_all_pools(pools)

    sell_count = 0
    buy_count = 0
    min_count = 1

    for pool in full_pools:
        if not pool or exchanges is not None and pool['protocol'] not in exchanges:
            continue
        if sell_count >= X and buy_count >= X:
            break

        if sell_ID in (pool['token0']['id'], pool['token1']['id']):
            if pool['token0']['id'] in BLACKLISTED_TOKENS or pool['token1']['id'] in BLACKLISTED_TOKENS:
                continue

            if sell_count < X:
                sell_count += 1
                if pool not in filtered_pools:
                    filtered_pools.append(pool)

        if buy_ID in (pool['token0']['id'], pool['token1']['id']):
            if pool['token0']['id'] in BLACKLISTED_TOKENS or pool['token1']['id'] in BLACKLISTED_TOKENS:
                continue

            if buy_count < X:
                buy_count += 1
                if pool not in filtered_pools:
                    filtered_pools.append(pool)

    if buy_count < min_count or sell_count < min_count:
        logging.warning(f'Insufficient pools found for {sell_ID}->{buy_ID} (Sell:{sell_count}, Buy:{buy_count}). May need to refresh pool data.')
        return []

    print(f"Filtered {len(filtered_pools)} pools for {sell_ID} -> {buy_ID} (Target {X} each, Found S:{sell_count}, B:{buy_count})")
    return filtered_pools


# ------------------------ Alternative USD Price Estimation ------------------------
def get_token_price_usd(token_id: str) -> float:
    """
    Estimates the USD price of a token by averaging the USD prices found
    in all cached pools that contain this token.
    NOTE: This is an approximation and relies on the accuracy and availability
          of 'priceUSD' fields within the cached pool data.
    """
    global pool_dict
    
    pools_with_token = [pool for pool in pool_dict.values() if pool and token_id in (pool.get('token0', {}).get('id'), pool.get('token1', {}).get('id'))]
    
    total_price_usd = 0.0
    num_prices_found = 0

    for pool in pools_with_token:
        token0 = pool.get('token0', {})
        token1 = pool.get('token1', {})

        if token0.get('id') == token_id and 'priceUSD' in token0:
            try:
                total_price_usd += float(token0['priceUSD'])
                num_prices_found += 1
            except (ValueError, TypeError):
                pass

        elif token1.get('id') == token_id and 'priceUSD' in token1:
             try:
                total_price_usd += float(token1['priceUSD'])
                num_prices_found += 1
             except (ValueError, TypeError):
                 pass

    average_price_usd = total_price_usd / num_prices_found if num_prices_found > 0 else 0.0
    return average_price_usd

# ------------------------ Helper Functions for 'best_match' Strategy ------------------------

def find_max_liquidity(pool_dict, n=10) -> float:
    """Finds the liquidity of the n-th most liquid pool in the cache."""
    try:
        most_liquid_pools = sorted(
            pool_dict.values(),
            key=lambda pool: float(pool.get(DEX_METRIC.get(pool.get('protocol'), 'reserveUSD'), 0)),
            reverse=True
        )
        pool_to_consider = most_liquid_pools[min(n-1, len(most_liquid_pools)-1)] if most_liquid_pools else None
        
        if pool_to_consider:
             metric_key = DEX_METRIC.get(pool_to_consider.get('protocol'), 'reserveUSD')
             return float(pool_to_consider.get(metric_key, 0))
        else:
             return 0.0
    except Exception as e:
        logging.error(f"Error finding max liquidity: {e}")
        return 0.0


def find_max_price(pool_dict, n=10) -> float:
    """Finds the maximum USD price of either token among the top n pools sorted by max token price."""
    try:
        most_expensive_pools = sorted(
            pool_dict.values(),
            key=lambda pool: max(float(pool.get('token0', {}).get('priceUSD', 0)), float(pool.get('token1', {}).get('priceUSD', 0))),
            reverse=True
        )
        pool_to_consider = most_expensive_pools[min(n-1, len(most_expensive_pools)-1)] if most_expensive_pools else None
        
        if pool_to_consider:
            return max(float(pool_to_consider.get('token0', {}).get('priceUSD', 0)), float(pool_to_consider.get('token1', {}).get('priceUSD', 0)))
        else:
            return 0.0
    except Exception as e:
         logging.error(f"Error finding max price: {e}")
         return 1.0


def calculate_score(pool, trade_value, max_trade_value, max_price, max_liquidity) -> float:
    """
    Calculates a score for a pool based on normalized liquidity and price,
    weighted potentially by the trade value (although weighting is currently commented out).
    Used by the 'best_match' routing strategy.
    """
    try:
        if max_price == 0: max_price = 1.0
        if max_liquidity == 0: max_liquidity = 1.0

        pool_max_price = max(float(pool.get('token0', {}).get('priceUSD', 0)), float(pool.get('token1', {}).get('priceUSD', 0)))
        normalized_price = pool_max_price / max_price
        
        liquidity_metric_key = DEX_METRIC.get(pool.get('protocol'), 'reserveUSD')
        pool_liquidity = float(pool.get(liquidity_metric_key, 0))
        normalized_liquidity = pool_liquidity / max_liquidity

        score = normalized_liquidity

        return score
    except Exception as e:
        logging.error(f"Error calculating score for pool {pool.get('id', 'N/A')}: {e}")
        return 0.0

# ------------------------ Pool Filtering ('best_match' Strategy) ------------------------
def filter_pools_best_match(sell_ID: str, sell_amount: float, exchanges=None, X: int = 30, Y: int = 30):
    """
    Filters pools based on a scoring system prioritizing liquidity (and potentially price, weighted by trade size).
    Selects top X pools overall by score, and top Y pools containing the sell token by score.
    """
    global pool_dict
    
    avg_sell_token_price_usd = get_token_price_usd(sell_ID)
    trade_value = sell_amount * avg_sell_token_price_usd
    max_trade_value = 100_000_000.0

    max_price = find_max_price(pool_dict)
    max_liquidity = find_max_liquidity(pool_dict)

    pool_scores = []
    protocols_to_search = exchanges if exchanges is not None else DEX_LIST
    for pool in pool_dict.values():
        if not pool: continue
        if pool.get('protocol') not in protocols_to_search:
            continue

        score = calculate_score(pool, trade_value, max_trade_value, max_price, max_liquidity)
        pool_scores.append((pool, score))

    sorted_pool_scores = sorted(pool_scores, key=lambda item: item[1], reverse=True)

    top_X_pools = [pool_score[0] for pool_score in sorted_pool_scores[:X]]

    top_Y_sell_token_pools = [
        pool_score[0] for pool_score in sorted_pool_scores
        if sell_ID in (pool_score[0].get('token0', {}).get('id'), pool_score[0].get('token1', {}).get('id'))
    ][:Y]

    combined_pools = list({f"{p['id']}_{p['token0']['id']}_{p['token1']['id']}": p for p in top_X_pools + top_Y_sell_token_pools}.values())

    print(f"Filtered {len(combined_pools)} pools using 'best_match' strategy.")
    return combined_pools


# ------------------------ Main Routing Function ------------------------
async def route_orders(sell_ID: str, sell_amount: float, buy_ID: str, exchanges, X, split=False, routing_strategy='default') -> dict:
    if sell_ID == '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee':
        sell_ID = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
    if buy_ID == '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee':
        buy_ID = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'

    sell_ID = sell_ID.lower()
    buy_ID = buy_ID.lower()
    """
    The main function to find and calculate the best swap routes.

    Returns:
        dict: A result dictionary containing:
              'pool_graph': Dictionary representation of the graph used for routing.
              'path_graph': Dictionary representation of the paths found.
              'routes': If split=False, a list of the top N calculated routes (sorted by amount_out).
                        If split=True, a dictionary representing the final split execution plan from get_final_route.
    """
    result = {}

    # ------------------------ Step 1: Filter Relevant Pools ------------------------
    filt_pools = []
    if routing_strategy == 'best_match':
        filt_pools = filter_pools_best_match(sell_ID, sell_amount, exchanges=exchanges)
    else:
        filt_pools = filter_pools(sell_ID, sell_amount, buy_ID, exchanges=exchanges,X=X)
        filt_pools = add_ticks(filt_pools,UNISWAP_V3)
        filt_pools = add_ticks(filt_pools,PANCAKESWAP_V3)

    if len(filt_pools) < 5:
        logging.warning(f"Initial filtering yielded only {len(filt_pools)} pools. Retrying with all DEXs after 5s sleep.")
        time.sleep(5)
        filt_pools = filter_pools(sell_ID, sell_amount, buy_ID, exchanges=DEX_LIST)
        if len(filt_pools) < 5:
             logging.error(f"Still insufficient pools ({len(filt_pools)}) after retry. Cannot proceed with routing.")
             return {"error": "Insufficient pool data available", "pool_graph": {}, "path_graph": {}, "routes": []}


    # ------------------------ Step 2: Construct Pool Graph ------------------------
    G = construct_pool_graph(filt_pools)
    graph_dict = pool_graph_to_dict(G)

    # ------------------------ Step 3: Find Paths ------------------------
    paths = find_shortest_paths(G, sell_ID, buy_ID)
    print('🔍 len(graph_dict):----------------------------', len(graph_dict))
    print('🔍 len(filt_pools):----------------------------', len(filt_pools))
    print('🔍 len(paths):---------------------------------', len(paths))
    print('🔍 len(pool_dict):-----------------------------', len(pool_dict))
    print('🔍 len(pools["Uniswap_V3"]["pools"]:----------------------------', len(pools["Uniswap_V3"]["pools"]))

    if not paths:
        logging.warning(f"No paths found between {sell_ID} and {buy_ID}.")
        return {"error": f"No paths found between {sell_ID} and {buy_ID}", "pool_graph": graph_dict, "path_graph": {}, "routes": []}

    # ------------------------ Step 4: Validate Paths ------------------------
    valid_paths = []
    if routing_strategy == 'best_match':
        logging.info("Skipping strict path validation for 'best_match' strategy.")
        valid_paths = paths
    else:
        valid_paths = validate_all_paths(G, paths, sell_ID, buy_ID)
        if not valid_paths:
             logging.warning(f"No *valid* paths found connecting {sell_ID} to {buy_ID}.")
             return {"error": f"No valid paths found connecting {sell_ID} to {buy_ID}", "pool_graph": graph_dict, "path_graph": {}, "routes": []}


    # ------------------------ Step 5: Create and Store Path Graph ------------------------
    path_graph = create_path_graph(valid_paths)
    path_graph_dict = path_graph_to_dict(path_graph)

    # ------------------------ Step 6: Calculate Route Outcomes ------------------------
    routes = calculate_routes(G, valid_paths, sell_amount, sell_ID, buy_ID)
    if not routes:
        logging.warning(f"Path calculation yielded no successful routes for {sell_ID} -> {buy_ID}.")
        return {"error": "Route calculation failed for all paths", "pool_graph": graph_dict, "path_graph": path_graph_dict, "routes": []}

    # ------------------------ Step 7: Post-Calculation Adjustments ------------------------
    routes.sort(key=lambda item: float(item.get('amount_out', 0)), reverse=True)
    if routing_strategy == 'best_match':
        routes.sort(key=lambda item: item[1].get('amount_out_usd', 0), reverse=True)

    # ------------------------ Step 8: Handle Trade Splitting or Select Top Routes ------------------------
    if split:
        final_route_plan = get_final_route(G, routes, sell_amount, sell_ID)
        result['routes'] = final_route_plan
    else:
        result['routes'] = routes[:MAX_ROUTES]

    return result