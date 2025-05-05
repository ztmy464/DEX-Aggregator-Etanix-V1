'''
This file handles the querying of liquidity pool data from various DEXs,
primarily using The Graph Subgraphs and specific DEX APIs (like Curve).
It also includes logic to reformat data from protocols like Balancer and Curve
into a more standardized pair format.
'''

from constants import UNISWAP_V2, UNISWAP_V3, SUSHISWAP_V2, CURVE, BALANCER_V3, PANCAKESWAP_V3
from constants import UNISWAPV2_ENDPOINT, UNISWAPV3_ENDPOINT, SUSHISWAPV2_ENDPOINT, PANCAKESWAP_V3_ENDPOINT, CURVE_ENDPOINT, BALANCER_V3_ENDPOINT
from constants import PROXY
from constants import DEX_ORDER_BY
from constants import API_KEY

import asyncio 
import aiohttp 
import json   
from itertools import combinations
import logging 
import requests
import os

# -- Initialization --
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
test_out_path = os.path.abspath(os.path.join(BASE_DIR, '..', 'test', 'test_out'))
fee_data_file = os.path.join(BASE_DIR, 'data', '.', 'curve_pool_fees.json')
logging.basicConfig(
    level=logging.INFO,  # INFO
    format="%(asctime)s - %(levelname)s - %(message)s"
)

bad_token_path = os.path.join(BASE_DIR, 'data', 'bad_tokens.json')
with open(bad_token_path,'r') as f:
    BAD_TOKENS = json.load(f)
    # Extract just the symbols for quick checking later
    BAD_TOKEN_SYMS = [token['symbol'] for token in BAD_TOKENS['tokens']]

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# -------------------- GraphQL Query Generation Functions --------------------


# -------------------- Uniswap V3 Data QL --------------------

# LIVED:
def uniswap_v3_query(X: int, skip: int, orderBy: str):
    return f"""
        {{
        pools(first:{X}, skip: {skip}, orderDirection: desc, orderBy: {orderBy},
        where: {{ 
            totalValueLockedUSD_gte: 1000,
            liquidity_not:0 
        }}) 
        {{
            token0 {{
                id
                symbol
                decimals
                derivedETH 
            }}
            token1 {{
                symbol
                id
                decimals
                derivedETH 
            }}
            id
            totalValueLockedToken0
            totalValueLockedToken1
            totalValueLockedUSD
            token0Price         # Price of token0 in terms of token1
            token1Price         # Price of token1 in terms of token0
            liquidity           # V3 liquidity value
            sqrtPrice           # V3 sqrtPrice value
            tick
            feeTier
        }}
        bundle(id: "1") {{
            ethPriceUSD
        }}
        }}
        """

# -------------------- Balancer V3 Data QL and Reformatting --------------------

# LIVED:
def balancer_v3_query(X: int, skip: int, orderBy: str):
    return f"""
        {{
        aggregatorPools(
            first: {X}, 
            orderBy: {orderBy}, 
            orderDirection: desc, 
            skip: {skip}, 
            where: {{ chainIn: [MAINNET], minTvl: 3000}}
        ) {{
            address
            type
            amp

            # Gyro-specific fields you want
            paramsAlpha:alpha
            paramsBeta:beta
            paramsC:c
            paramsS:s
            paramsLambda:lambda
            tauAlphaX
            tauAlphaY
            tauBetaX
            tauBetaY
            u
            v
            w
            z
            dSq

            poolTokens {{
            address
            symbol
            balance
            weight
            balanceUSD
            scalingFactor
            priceRate
            decimals
            # isAllowed The token xxx is currently not supported.
            }}
            dynamicData {{
            swapFee
            totalLiquidity
            }}
        }}
        }}
        """


def reformat_balancer_v3_pool(pool):
    valid_tokens = [
        t for t in pool['poolTokens']
        if float(t.get('balanceUSD', 0)) > 0 and float(t.get('balance', 0)) > 0
    ]
    token_combinations = list(combinations(valid_tokens, 2))
    reformatted_pools = []

    for combination in token_combinations:
        if not ('STABLE' in pool['type'] or 'GYROE' in pool['type'] or 'WEIGHTED' in pool['type']):
            continue
        token0 = combination[0]
        token1 = combination[1]
        new_pair = {
            'id': pool['address'].lower(),
            'reserve0': token0['balance'],
            'reserve1': token1['balance'],
            "protocol": "Balancer_V3",
            'token0': {
                'id': token0['address'].lower(),
                'symbol': token0['symbol'],
                'priceUSD': float(token0['balanceUSD'])/float(token0['balance']),
                'decimals': token0['decimals'],
            },
            'token1': {
                'id': token1['address'].lower(),
                'symbol': token1['symbol'],
                'priceUSD': float(token1['balanceUSD'])/float(token1['balance']),
                'decimals': token1['decimals'],
            },
            'pool_data': pool
        }
        reformatted_pools.append(new_pair)
        new_pair['dangerous'] = new_pair['token0']['symbol'] in BAD_TOKEN_SYMS or new_pair['token1']['symbol'] in BAD_TOKEN_SYMS
        # check if priceUSD is None and calculate it if it is
        if new_pair['token0']['priceUSD'] is None:
            try:
                new_pair['token0']['priceUSD'] = float(new_pair['token0']['totalBalanceUSD']) / float(new_pair['reserve0'])
            except ZeroDivisionError:
                new_pair['token0']['priceUSD'] = 0
        if new_pair['token1']['priceUSD'] is None:
            try:
                new_pair['token1']['priceUSD'] = float(new_pair['token1']['totalBalanceUSD']) / float(new_pair['reserve1'])
            except ZeroDivisionError:
                new_pair['token1']['priceUSD'] = 0
        totalLiquidity = float(pool['dynamicData']['totalLiquidity'])
        try:
            reserveUSD = float(token0['balanceUSD'])+float(token1['balanceUSD'])
            new_pair['reserveUSD'] = reserveUSD
        except ZeroDivisionError:
            new_pair['reserveUSD'] = 0

    return reformatted_pools

# LIVED:
def reformat_balancer_v3_pools(pool_list):
    all_reformatted_pools = []
    for pool in pool_list:
        reformatted_pools = reformat_balancer_v3_pool(pool)
        all_reformatted_pools.extend(reformatted_pools)
    
    return all_reformatted_pools

# -------------------- Curve Data QL and Reformatting --------------------

# LIVED:
async def collect_curve_pools():
    res = []
    async with aiohttp.ClientSession() as session:
        async with session.get(CURVE_ENDPOINT, proxy=PROXY) as response:
            obj = await response.json()
            data = obj['data']['poolData']
            
            # add fee field to the pool data
            data = add_fee_field(data, fee_data_file)
            write_processed_pools_path = os.path.join(test_out_path, f'data_curve.json')
            with open(write_processed_pools_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            for pool in data:
                try:
                    # Check if it's a metapool with base pool and underlying coins
                    if pool.get('isMetaPool') and pool.get('basePoolAddress') and pool.get('underlyingCoins'):
                        # For metapools, pair the first underlying coin with each other underlying coin
                        first_coin = pool['underlyingCoins'][0]
                        other_coins = pool['underlyingCoins'][1:]
                        
                        # Create pairs between the first coin and each other coin
                        for other_coin in other_coins:
                            # Skip if either price is None
                            if first_coin['usdPrice'] is None or other_coin['usdPrice'] is None:
                                continue
                            
                            decimals0 = int(first_coin['decimals'])
                            decimals1 = int(other_coin['decimals'])
                            
                            new_pair = {}
                            new_pair['id'] = pool['address'].lower()
                            new_pair['reserve0'] = float(first_coin['poolBalance']) / 10**decimals0
                            new_pair['reserve1'] = float(other_coin['poolBalance']) / 10**decimals1
                            
                            new_pair['token0'] = {
                                'id': first_coin['address'].lower(),
                                'symbol': first_coin['symbol'],
                                'decimals': decimals0,
                                'priceUSD': first_coin['usdPrice']
                            }
                            new_pair['token1'] = {
                                'id': other_coin['address'].lower(),
                                'symbol': other_coin['symbol'],
                                'decimals': decimals1,
                                'priceUSD': other_coin['usdPrice']
                            }
                            new_pair['reserveUSD'] = new_pair['reserve0'] * first_coin['usdPrice'] + new_pair['reserve1'] * other_coin['usdPrice']
                            new_pair['protocol'] = CURVE
                            new_pair['dangerous'] = new_pair['token0']['symbol'] in BAD_TOKEN_SYMS or new_pair['token1']['symbol'] in BAD_TOKEN_SYMS
                            new_pair['pool_data'] = pool

                            basepool_address = pool['basePoolAddress']
                            new_pair['pool_data']['basepool'] = [pool for pool in data if pool["address"].lower() == basepool_address.lower()][0]
                            res.append(new_pair)
                    else:
                        # Original logic for regular pools
                        pairs = combinations(pool['coins'], 2)
                        for pair in pairs:
                            # Check if either usdPrice is None and skip this pair if true
                            if pair[0]['usdPrice'] is None or pair[1]['usdPrice'] is None:
                                continue
                            
                            decimals0 = int(pair[0]['decimals'])
                            decimals1 = int(pair[1]['decimals'])

                            new_pair = {}
                            new_pair['id'] = pool['address'].lower()
                            new_pair['reserve0'] = int(pair[0]['poolBalance']) / 10**decimals0
                            new_pair['reserve1'] = int(pair[1]['poolBalance']) / 10**decimals1
                            new_pair['token0'] = {
                                'id': pair[0]['address'].lower(),
                                'symbol': pair[0]['symbol'],
                                'decimals': decimals0,
                                'priceUSD': pair[0]['usdPrice']
                            }
                            new_pair['token1'] = {
                                'id': pair[1]['address'].lower(),
                                'symbol': pair[1]['symbol'],
                                'decimals': decimals1,
                                'priceUSD': pair[1]['usdPrice']
                            }
                            new_pair['reserveUSD'] = new_pair['reserve0'] * pair[0]['usdPrice'] + new_pair['reserve1'] * pair[1]['usdPrice']
                            new_pair['protocol'] = CURVE
                            new_pair['dangerous'] = new_pair['token0']['symbol'] in BAD_TOKEN_SYMS or new_pair['token1']['symbol'] in BAD_TOKEN_SYMS
                            new_pair['pool_data'] = pool
                            res.append(new_pair)
                except Exception as e:
                    print(f"Error processing pool: {e}")
                    # print(pool)
                    # Don't break here to continue processing other pools
                    continue
    
    return res

def add_fee_field(graphql_results, fee_data_file):
    try:
        with open(fee_data_file, 'r', encoding="utf-8") as f:
            fee_data = json.load(f)
    except FileNotFoundError:
        fee_data = {}
        print(f"Warning: {fee_data_file} not found. Using default fee values.")

    # Enrich each pool with fee data
    for pool in graphql_results:
        if 'address' in pool:
            pool_id = pool['address'].lower()
            
            if pool_id in fee_data:
                pool['fee'] = fee_data[pool_id]['fee']
                pool['offpeg_fee_multiplier'] = fee_data[pool_id]['offpeg_fee_multiplier']
            else:
                pool['fee'] = 4000000
                pool['offpeg_fee_multiplier'] = 1

    return graphql_results

# -------------------- Main Data Fetching Function --------------------

async def get_latest_pool_data(protocol: str, X: int = 1000, skip: int = 0, max_metric: float = None) -> list:

    endpoint = None
    orderBy = None # It has been hardcoded in the QL.
    data_field = None

    # -------------------- Determine Endpoint and Query based on Protocol --------------------
    if protocol == UNISWAP_V2:
        endpoint = UNISWAPV2_ENDPOINT
        orderBy = DEX_ORDER_BY[UNISWAP_V2]
        data_field = 'pairs' # Data is under the 'pairs' field in the response
    elif protocol == SUSHISWAP_V2:
        endpoint = SUSHISWAPV2_ENDPOINT
        orderBy = DEX_ORDER_BY[SUSHISWAP_V2]
        data_field = 'pairs'
    elif protocol == UNISWAP_V3:
        endpoint = UNISWAPV3_ENDPOINT
        orderBy = DEX_ORDER_BY[UNISWAP_V3]
        data_field = 'pools' # Data is under the 'pools' field
    elif protocol == PANCAKESWAP_V3:
        endpoint = PANCAKESWAP_V3_ENDPOINT
        orderBy = DEX_ORDER_BY[PANCAKESWAP_V3]
        data_field = 'pools'
    elif protocol == BALANCER_V3:
        endpoint = BALANCER_V3_ENDPOINT
        orderBy = DEX_ORDER_BY[BALANCER_V3]

        data_field = 'aggregatorPools'
    elif protocol == PANCAKESWAP_V3:
        endpoint = PANCAKESWAP_V3_ENDPOINT
        data_field = 'pools'
    elif protocol == CURVE:
        # Curve is handled differently, call its dedicated async function
        processed_pools_curve = await collect_curve_pools()
        write_processed_pools_path = os.path.join(test_out_path, f'processed_pools_curve.json')
        with open(write_processed_pools_path, "w", encoding="utf-8") as f:
            json.dump(processed_pools_curve, f, ensure_ascii=False, indent=2)
        return processed_pools_curve
    else:
        logging.error(f"Unknown protocol specified: {protocol}")
        return [] # Return empty list for unknown protocols


    # -------------------- Asynchronous Fetching Loop with Retries --------------------
    while True: # Loop indefinitely until success or unrecoverable error (though no explicit break here)
        try:
            # -------------------- Generate Protocol-Specific GraphQL Query --------------------
            if protocol == UNISWAP_V2:
                query = f"""
                    {{
                    pairs(first: {X}, orderBy: {orderBy}, orderDirection: desc, skip: {skip}) {{
                        id
                        reserveUSD # use trackedReserveETH to order, but need reserveUSD to show USD price
                        reserve0
                        reserve1
                        token0 {{ id symbol decimals }}
                        token1 {{ id symbol decimals }}
                        }}
                    }}
                    """
            elif protocol == SUSHISWAP_V2:
                query = f"""
                {{
                pairs(first: {X}, orderBy: {orderBy}, orderDirection: desc, skip: {skip}) {{
                    id
                    {orderBy} # Include the ordering metric itself
                    reserve0
                    reserve1
                    token0 {{ id symbol decimals }}
                    token1 {{ id symbol decimals }}
                    }}
                }}
                """
            elif protocol in [UNISWAP_V3, PANCAKESWAP_V3]:
                query = uniswap_v3_query(X, skip, orderBy)
            elif protocol == BALANCER_V3:
                query = balancer_v3_query(X, skip, orderBy)

            write_query_path = os.path.join(test_out_path, f'query_{protocol}.graphql')
            with open(write_query_path, "w", encoding="utf-8") as f:
                f.write(query)

            # -------------------- Perform Asynchronous HTTP POST Request --------------------
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        endpoint,
                        json={"query": query},
                        headers=headers
                    ) as response:
                    response.raise_for_status() # Raise error for bad HTTP status
                    obj = await response.json() # Parse JSON response

                    pools = obj.get('data', {}).get(data_field, [])

                    if protocol == UNISWAP_V3 or protocol == PANCAKESWAP_V3:
                        bundle = obj.get('data', {}).get('bundle', {})
                        ethPriceUSD = bundle.get('ethPriceUSD', 0.0)

                    processed_pools = []
                    for pool in pools:
                        try:
                            pool['protocol'] = protocol # Add protocol identifier to each pool dict

                            # -------------------- Calculate missing USD prices (approximations) --------------------
                            # For SushiSwap V2: Use liquidityUSD / reserve
                            if protocol == UNISWAP_V2 or protocol == SUSHISWAP_V2:
                                try:
                                    pool['token0']['priceUSD'] = float(pool['reserveUSD']) / 2/float(pool['reserve0'])
                                    pool['token1']['priceUSD'] = float(pool['reserveUSD']) / 2/float(pool['reserve1'])
                                except (ValueError, TypeError, ZeroDivisionError, KeyError):
                                    pool['token0']['priceUSD'] = 0.0
                                    pool['token1']['priceUSD'] = 0.0

                            # For Uniswap V3: Calculate reserves from liquidity and sqrtPrice
                            if protocol == UNISWAP_V3 or protocol == PANCAKESWAP_V3:
                                try:
                                    Q96 = 1 << 96
                                    # V3 math to convert liquidity and sqrtPrice to reserves
                                    sqrtPriceX96  = float(pool['sqrtPrice'])
                                    liquidity = int(pool['liquidity'])
                                    decimals0 = int(pool['token0']['decimals'])
                                    decimals1 = int(pool['token1']['decimals'])

                                    # Calculate raw reserves (without considering decimals)
                                    reserve0raw = (liquidity * Q96) // sqrtPriceX96
                                    reserve1raw = (liquidity * sqrtPriceX96) // Q96
                                    # Adjust for decimals
                                    pool['reserve0'] = reserve0raw / (10**decimals0)
                                    pool['reserve1'] = reserve1raw / (10**decimals1)

                                    # Calculate the price of each token
                                    pool['token0']['priceUSD'] = float(pool['token0']['derivedETH']) * float(ethPriceUSD)
                                    pool['token1']['priceUSD'] = float(pool['token1']['derivedETH']) * float(ethPriceUSD)
                                    pool['token0'].pop('derivedETH')
                                    pool['token1'].pop('derivedETH')

                                except (ValueError, TypeError, ZeroDivisionError, KeyError, OverflowError) as e:
                                    logging.error(f"Error processing Uniswap V3 pool {pool.get('id', 'N/A')} reserves/prices: {e}")
                                    pool['reserve0'] = 0.0
                                    pool['reserve1'] = 0.0
                                    pool['token0']['priceUSD'] = 0.0
                                    pool['token1']['priceUSD'] = 0.0

                            # For Balancer V3: reformat the pool
                            if protocol == BALANCER_V3:
                                pool_list = reformat_balancer_v3_pool(pool)
                                for pool_i in pool_list:
                                    processed_pools.append(pool_i)
                                    
                            # -------------------- Set 'dangerous' flag --------------------
                            pool['dangerous'] = (
                                (protocol not in (BALANCER_V3) and (
                                    pool['token0']['symbol'] in BAD_TOKEN_SYMS or
                                    pool['token1']['symbol'] in BAD_TOKEN_SYMS or
                                    pool['reserve0'] == 0 or
                                    pool['reserve1'] == 0
                                )))
                            
                            if protocol != BALANCER_V3:
                                processed_pools.append(pool) # Add successfully processed pool

                        except Exception as e:
                            logging.error(f"Error during post-processing of pool {pool.get('id', 'N/A')} for protocol {protocol}: {e}")
                            continue # Skip this pool if post-processing fails
                    
                    if protocol == UNISWAP_V3:
                        processed_pools = sorted(processed_pools, key=lambda p: float(p["totalValueLockedUSD"]), reverse=True)
                    write_processed_pools_path = os.path.join(test_out_path, f'processed_pools_{protocol}.json')
                    with open(write_processed_pools_path, "w", encoding="utf-8") as f:
                        json.dump(processed_pools, f, ensure_ascii=False, indent=2)

                    return processed_pools # Return the processed list for other protocols

        # -------------------- Error Handling for the Fetch Loop --------------------
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logging.error(f"Network error fetching {protocol} pools: {e}. Retrying...")
            await asyncio.sleep(2) # Wait longer for network issues
            continue # Retry the loop
        except (json.JSONDecodeError, KeyError) as e:
            # Errors likely indicate issues with the Subgraph response or structure
            logging.error(f"Data parsing error fetching {protocol} pools: {e}. Retrying...")
            await asyncio.sleep(1)
            continue # Retry the loop
        except Exception as e:
            # Catch any other unexpected errors during the fetch/query process
            logging.exception(f"Unexpected error fetching {protocol} pools: {e}. Retrying...") # Log full traceback
            await asyncio.sleep(5) # Wait longer for unexpected errors
            continue # Retry the loop
