   # test/conftest.py
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
         

from src.slippage.simu_uni_v2 import swap_uni_v2
from src.slippage.simu_uni_v3 import swap_uni_v3
from src.slippage.type_pool.uni_v3.v3swap_single import on_swap_single_tick
from src.slippage.simu_balancer import swap_blancer
from src.slippage.simu_curve import swap_curve

# ---------------------------------------- UNISWAP V2 ----------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
filt_pools_path = os.path.join(BASE_DIR, 'test_out', f'processed_pools_Uniswap_V2.json')
with open(filt_pools_path, "r", encoding="utf-8") as f:
    filt_pools = json.load(f)

target_address = "0xb4e16d0168e52d35cacd2c6185b44281ec28c9dc"

pool = [pool for pool in filt_pools if pool["id"].lower() == target_address.lower()][0]

input_index = 1
output_index = 0
input_amount_human = 1

input_symbol = pool[f"token{input_index}"]["symbol"]
output_symbol = pool[f"token{output_index}"]["symbol"]

amount_out = swap_uni_v2(pool, input_amount_human, input_index, output_index)

print(f"Change from {input_symbol} to {output_symbol}, change {input_amount_human}, and end up with {amount_out}.")
print("-"*50, "uniswap v2 swap_uni_v2 end", "-"*50)

# ---------------------------------------- UNISWAP V3 ----------------------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
filt_pools_path = os.path.join(BASE_DIR, 'test_out', f'processed_pools_Uniswap_V3.json')
with open(filt_pools_path, "r", encoding="utf-8") as f:
    filt_pools = json.load(f)

target_address = '0x9db9e0e53058c89e5b94e29621a205198648425b'

pool = [pool for pool in filt_pools if pool["id"].lower() == target_address.lower()][0]

input_index = 1
output_index = 0
input_amount_human = 2000
amount_in_wei = int(input_amount_human * (10**int(pool[f"token{input_index}"]['decimals'])))

input_symbol = pool[f"token{input_index}"]["symbol"]
output_symbol = pool[f"token{output_index}"]["symbol"]

amount_out_in_wei = on_swap_single_tick(pool, amount_in_wei, input_index, output_index)
amount_out = amount_out_in_wei / (10**int(pool[f"token{output_index}"]['decimals']))

print(f"Change from {input_symbol} to {output_symbol}, change {input_amount_human}, and end up with {amount_out}.")
print("-"*50, "uniswap v3 on_swap_single_tick end", "-"*50)

# ---------------------------------------- BALANCER ----------------------------------------
"""
There are three situations for balaner:
1.weighted pool
2.stable pool
3.gyro pool
"""

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
filt_pools_path = os.path.join(BASE_DIR, 'test_out', f'processed_pools_Balancer_V3.json')
with open(filt_pools_path, "r", encoding="utf-8") as f:
    filt_pools = json.load(f)

# pool_weighted
# target_address = "0x3de27efa2f1aa663ae5d458857e731c129069f29"

# pool_stable with BPT token
# output_index = 2
# output_symbol = pool[f"token{output_index-1}"]["symbol"]
# target_address = "0xdacf5fa19b1f720111609043ac67a9818262850c"

# pool_gyro
target_address = "0x2191df821c198600499aa1f0031b1a7514d7a7d9"
pool = [pool for pool in filt_pools if pool["id"].lower() == target_address.lower()][0]

input_index = 0
output_index = 1
input_amount_human = 1

amount_out = swap_blancer(pool['pool_data'], input_amount_human, input_index, output_index)

input_symbol = pool[f"token{input_index}"]["symbol"]
output_symbol = pool[f"token{output_index}"]["symbol"]

print(f"Change from {input_symbol} to {output_symbol}, change {input_amount_human}, and end up with {amount_out}.")
print("-"*50, "balancer swap_blancer end", "-"*50)

# ---------------------------------------- CURVE ----------------------------------------
"""
There are three situations for curve:
1. mult-stablepool->find the corresponding multi-stable pool->call simulate_exchange to calculate
2. dynamic fee->provide parameters about dynamic fee rate
3. metapool->find the corresponding basepool->call simulate_exchange_underlying to calculate
3. cryptopool->
"""

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
filt_pools_path = os.path.join(BASE_DIR, 'test_out', f'processed_pools_Curve.json')
with open(filt_pools_path, "r", encoding="utf-8") as f:
    filt_pools = json.load(f)

# mult-stablepool DAI USDC USDT
target_address = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
# cryptoswap usdc wbtc eth
# target_address = "0x7F86Bf177Dd4F3494b841a37e810A34dD56c829B"
# underlying MIM DAI USDC USDT 
# target_address = "0x5a6A4D54456819380173272A5E8E9B9904BdF41B"
pool = [pool for pool in filt_pools if pool["id"].lower() == target_address.lower()][0]
# --- Run the Test Case ---
input_index = 0
output_index = 1
input_amount_human = 1000000
input_symbol = pool[f"token{input_index}"]["symbol"]
output_symbol = pool[f"token{output_index}"]["symbol"]
amount_out = swap_curve(pool['pool_data'], input_amount_human, input_index, output_index)
print(f"Change from {input_symbol} to {output_symbol}, change {input_amount_human}, and end up with {amount_out}.")
print("-"*50,"curve swap_curve end","-"*50)




