import logging
import requests
import json
import math
from constants import UNISWAPV3_ENDPOINT,PANCAKESWAP_V3_ENDPOINT,API_KEY

def ticks_bound(current_tick, total_value_locked_usd, tick_spacing):
    """
    Calculate tick bounds based on pool TVL and tick spacing count.
    - Higher TVL => fewer ticks around current tick
    - Lower TVL => wider range (more tickSpacing intervals)
    """
    if isinstance(current_tick, str):
        current_tick = int(current_tick)

    not_zero_liquidity = False
    # Determine how many tick_spacing units to include on each side
    if total_value_locked_usd >= 500_000_000:  # $500M+
        spacing_count = 3
    elif total_value_locked_usd >= 100_000_000:  # $100M+
        spacing_count = 5
    elif total_value_locked_usd >= 50_000_000:  # $50M+
        spacing_count = 10
    elif total_value_locked_usd >= 10_000_000:  # $10M+
        spacing_count = 20
    else:  # <$10M
        spacing_count = 1000
        not_zero_liquidity = True

    lower_bound = current_tick - spacing_count * tick_spacing
    upper_bound = current_tick + spacing_count * tick_spacing

    # Round to nearest tickSpacing just to be safe
    lower_bound = math.floor(lower_bound / tick_spacing) * tick_spacing
    upper_bound = math.ceil(upper_bound / tick_spacing) * tick_spacing

    return lower_bound, upper_bound, not_zero_liquidity

def build_graphql_query(pools_data):
    """
    Build a batch GraphQL query for multiple pools
    """
    query_parts = []
    
    for i, pool in enumerate(pools_data):
        pool_id = pool['id']
        tick_lower = pool['tick_lower']
        tick_upper = pool['tick_upper']
        not_zero_liquidity = pool['not_zero_liquidity']
        
        if not_zero_liquidity:
            query_part = f"""
                pool{i}: pool(id: "{pool_id}") {{
                tick
                ticks(where: {{
                    liquidityNet_not:"0"
                }}) {{
                    tickIdx
                    liquidityNet
                }}
                }}
                """
        else:
            query_part = f"""
                pool{i}: pool(id: "{pool_id}") {{
                tick
                ticks(where: {{
                    tickIdx_gte: {tick_lower},
                    tickIdx_lte: {tick_upper}
                    liquidityNet_not:"0"
                }}) {{
                    tickIdx
                    liquidityNet
                }}
                }}
                """
        query_parts.append(query_part)
    
    query = f"""
    query BatchTickQuery {{
      {" ".join(query_parts)}
    }}
    """
    return query

def fetch_ticks_data(endpoint, query):
    """
    Send GraphQL query to the specified endpoint and return response
    """
    headers = {
        'Content-Type': 'application/json',
        "Authorization": f"Bearer {API_KEY}"
    }
    
    data = {
        'query': query
    }
    
    response = requests.post(endpoint, headers=headers, json=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data: {response.status_code}, {response.text}")
        return None

def add_ticks_to_pools(pools, ticks_data,protocol):

    if not ticks_data or 'data' not in ticks_data:
        print("No ticks data found")
        return pools
    
    i = 0
    for pool in pools:
        if pool['protocol'] not in protocol:
            continue

        pool_key = f'pool{i}'
        pool_data = ticks_data['data'].get(pool_key)

        if pool_data is None:
            print(f"Warning:！！！！！！！！！！！！！！ No tick data for {ticks_data}")
            print(f"Warning:！！！！！！！！！！！！！！ No tick data for {pool}")
            i += 1
            continue
        pool['ticks'] = ticks_data['data'][f'pool{i}']['ticks']
        i+=1
    # # Create a mapping of pool indices
    # pool_indices = {}
    # for i, pool in enumerate(pools):
    #     if pool['protocol'] in ['Uniswap_V3', 'Pancakeswap_V3']:
    #         pool_indices[f"pool{i}"] = i
    
    # # Add ticks data to each pool
    # for pool_key, data in ticks_data['data'].items():
    #     if pool_key in pool_indices and data and 'ticks' in data:
    #         pool_index = pool_indices[pool_key]
    #         pools[pool_index]['ticks'] = data['ticks']
    
    return pools

# def remove_no_liquidity_ticks(data):
#     for pool in data.get('data', {}).values():
#         if 'ticks' in pool and isinstance(pool['ticks'], list):
#             pool['ticks'] = [tick for tick in pool['ticks'] if tick.get('liquidityNet') != '0']
#     return data

def add_ticks(filt_pools,protocol):
    """
    Add ticks data to the filtered pools
    """
    # Prepare pools that need tick data (Uniswap V3 and Pancakeswap V3)
    v3_pools = []

    # If there is only one pool (that is, filt_pools is a dictionary), 
    # in fact, when traversing the keys of the dictionary, we are not dealing with the pools themselves.
    if isinstance(filt_pools, dict):
        filt_pools = [filt_pools]
    
    for pool in filt_pools:
        if pool['protocol'] in protocol:
            # Get current tick
            current_tick = int(pool['tick'])
            
            # Get tick spacing based on fee tier
            fee_tier = int(pool['feeTier'])
            tick_spacing = get_tick_spacing(fee_tier)
            
            # Calculate tick range based on TVL and tick spacing
            total_value_locked_usd = float(pool['totalValueLockedUSD'])
            lower_bound, upper_bound, not_zero_liquidity = ticks_bound(current_tick, total_value_locked_usd, tick_spacing)
            
            # Store bounds for query building
            pool['tick_lower'] = lower_bound
            pool['tick_upper'] = upper_bound
            pool['not_zero_liquidity'] = not_zero_liquidity

            v3_pools.append(pool)
    
    if not v3_pools:
        logging.info(f"No {protocol} pools used")
        
        if isinstance(filt_pools, list):
            if len(filt_pools) == 1 and isinstance(filt_pools[0], dict):
                filt_pools = filt_pools[0]
        return filt_pools
    
    # Build GraphQL query for all V3 pools
    query = build_graphql_query(v3_pools)
    
    # Fetch ticks data
    if protocol == 'Uniswap_V3':
        ticks_data = fetch_ticks_data(UNISWAPV3_ENDPOINT, query)
    elif protocol == 'Pancakeswap_V3':
        ticks_data = fetch_ticks_data(PANCAKESWAP_V3_ENDPOINT, query)

    # remove the tick which liquidityNet = 0
    # have removed in build_graphql_query
    # ticks_data = remove_no_liquidity_ticks(ticks_data)
    
    # Add ticks data to pools
    if ticks_data:
        filt_pools = add_ticks_to_pools(filt_pools, ticks_data,protocol)
    
    # Remove temporary tick bounds used for queries
    for pool in filt_pools:
        if 'tick_lower' in pool:
            del pool['tick_lower']
        if 'tick_upper' in pool:
            del pool['tick_upper']

    if isinstance(filt_pools, list):
        if len(filt_pools) == 1 and isinstance(filt_pools[0], dict):
            filt_pools = filt_pools[0]
    return filt_pools


def get_tick_spacing(fee: int) -> int:
    try:
        return {
        100: 1,      # 0.01% fee
        500: 10,     # 0.05% fee
        2500: 50,    # 0.25% fee
        3000: 60,    # 0.30% fee
        10000: 200   # 1.00% fee
        }[fee]
    except KeyError:
        raise ValueError(f"Invalid fee tier: {fee}")