import copy
from slippage.simu_balancer import swap_blancer
from slippage.simu_curve import swap_curve
from slippage.simu_uni_v2 import swap_uni_v2
from slippage.simu_uni_v3 import swap_uni_v3
""" 
@ztmy:
this file is used to simulate the swap, it contains the following functions:
1. find_token_indices: find the index of the input and output token in the pool data
2. simulateSwap: simulate the swap
"""

def find_token_indices(data, input_index, output_index):

    if input_index == 0:
        input_token = data["token0"]
        output_token = data["token1"]
    else:
        input_token = data["token1"]
        output_token = data["token0"]
    
    input_address = input_token["id"].lower()
    output_address = output_token["id"].lower()
    
    input_token_idx = None
    output_token_idx = None
    
    if data.get('pool_data').get('coins'):
        coins = data["pool_data"]["coins"]
    elif data.get('pool_data').get('poolTokens'):
        coins = data["pool_data"]["poolTokens"]

    for idx, coin in enumerate(coins):
        coin_address = coin["address"].lower()
        
        if coin_address == input_address:
            input_token_idx = idx
        elif coin_address == output_address:
            output_token_idx = idx
    
    return input_token_idx, output_token_idx

# @ztmy: the entrance of the price impact calculation
def simulateSwap(pool_data, amount_in, input_index, output_index):
    pool_copy = copy.deepcopy(pool_data)

    protocol = pool_copy['protocol']

    # ------------------------ Select Price Impact Function Based on Protocol ------------------------
    if protocol == 'Uniswap_V2' or protocol == 'Sushiswap_V2':
        price_impact_function = swap_uni_v2
    elif protocol == 'Uniswap_V3' or protocol == 'Pancakeswap_V3':
        price_impact_function = swap_uni_v3
    elif protocol == 'Balancer_V3':
        price_impact_function = swap_blancer
    elif protocol == 'Curve':
        price_impact_function = swap_curve

    # ------------------------ Process First Swap in the Path ------------------------
    # '0x5c6ee304399dbdb9c8ef030ab642b10820db8f56'
    if pool_copy.get('pool_data'):
        input_index, output_index = find_token_indices(pool_copy, input_index, output_index)
        actual_pool_copy = pool_copy.get('pool_data')
    else:
        actual_pool_copy = pool_copy

    amount_out = price_impact_function(
        actual_pool_copy, amount_in, input_index, output_index)

    amount_out_zero = abs(amount_out) < 1e-12
    if amount_out_zero:
        amount_out = 0

    return amount_out