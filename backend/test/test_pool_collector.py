'''
This script collects the top 1000 Uniswap V2 tokens ordered descending by tradeVolumeUSD, 
it is not used in the final product but is handy for testing.
'''
import json
import os
import sys

test_dir_path = os.path.dirname(os.path.abspath(__file__))
project_root_path = os.path.dirname(test_dir_path)

if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path)
src_path = os.path.join(project_root_path, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# standard library imports
import asyncio
# local imports
from src.pool_collector import get_latest_pool_data
from src.constants import BALANCER_V3, UNISWAP_V2, UNISWAP_V3, SUSHISWAP_V2, CURVE, PANCAKESWAP_V3

async def latest_pool_data(protocol: str):
    # query for USDC and WETH
    tokens = ['USDC', 'WETH']
    # get the top 100 pools
    X = 100
    tokenB = 'USDC'
    ID_B = '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48'
    tokenA = 'WETH'
    ID_A = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
    # get the pools
    pools = await get_latest_pool_data(protocol)
    pool = pools[0]
    print(pool)
    
if __name__ == '__main__':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()) # only need this if running on windows
    asyncio.run(latest_pool_data(UNISWAP_V3))