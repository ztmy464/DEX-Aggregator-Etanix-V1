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

from src.slippage.type_pool.uni_v3.v3swap import swap_amount_out
from src.slippage.type_pool.uni_v3.batchTicks import add_ticks
from src.slippage.type_pool.uni_v3.v3swap_single import on_swap_single_tick
from src.constants import UNISWAP_V3

# -------------------------- test --------------------------

# load the filt_pools from the test_out folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
filt_pools_path = os.path.join(BASE_DIR,'test_out', f'processed_pools_Uniswap_V3.json')
with open(filt_pools_path, "r", encoding="utf-8") as f:
    filt_pools = json.load(f)

target_address = "0xcbcdf9626bc03e24f779434178a73a0b4bad62ed"
matched_pools = [pool for pool in filt_pools if pool["id"].lower() == target_address.lower()][0]


amount_in_wei = int(2000 * (10**int(matched_pools['token1']['decimals'])))
input_index = 1
output_index = 0
matched_pools = add_ticks(matched_pools,UNISWAP_V3)
calculated_token1_out = swap_amount_out(matched_pools, amount_in_wei, input_index, output_index)
print("1 weth -> wbtc",calculated_token1_out)

calculated_token1_out = on_swap_single_tick(matched_pools, amount_in_wei, input_index, output_index)
print("1 weth -> wbtc",calculated_token1_out)

