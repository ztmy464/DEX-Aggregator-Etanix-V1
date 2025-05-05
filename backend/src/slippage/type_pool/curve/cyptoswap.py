from decimal import Decimal
import json
import os
import time
from slippage.type_pool.curve.CryptoMath import get_y
from constants import ALCHEMY_KEY
# Constants from Vyper contract
PRECISION = 10**18
A_MULTIPLIER = 10000
# N_COINS will be determined from graph_data
# PRICE_SIZE = 256 / (N_COINS - 1) - Need N_COINS first
# PRICE_MASK = 2**PRICE_SIZE - 1 - Need PRICE_SIZE first
MAX_ITERATIONS_NEWTON = 255 # For _newton_y
MIN_GAMMA = 10**10
MAX_GAMMA = 5 * 10**16
MIN_A_CRYPTO = None # N_COINS**N_COINS * A_MULTIPLIER / 100 # Need N_COINS
MAX_A_CRYPTO = None # 1000 * A_MULTIPLIER * N_COINS**N_COINS # Need N_COINS


from web3 import Web3
import json

web3 = Web3(Web3.HTTPProvider(f'https://eth-mainnet.g.alchemy.com/v2/{ALCHEMY_KEY}'))

POOL_ADDRESS = '0x7F86Bf177Dd4F3494b841a37e810A34dD56c829B'

ABI = [ 
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "index",
                "type": "uint256"
            }
        ],
        "name": "balances",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {
                "internalType": "uint256",
                "name": "k",
                "type": "uint256"
            }
        ],
        "name": "price_scale",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "precisions",
        "outputs": [
            {
                "internalType": "uint256[3]",
                "name": "",
                "type": "uint256[3]"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "D",
        "outputs": [
            {
                "internalType": "uint256",
                "name": "",
                "type": "uint256"
            }
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "stateMutability": "view",
        "type": "function",
        "name": "packed_fee_params",
        "inputs": [],
        "outputs": [
            {
                "name": "",
                "type": "uint256"
            }
        ]
    },
    {
        "stateMutability":"view",
        "type":"function",
        "name":"get_dy",
        "inputs":[{"name":"i","type":"uint256"},{"name":"j","type":"uint256"},{"name":"dx","type":"uint256"}],
        "outputs":[{"name":"","type":"uint256"}]
    }
]

def get_pool_data(graph_data, contract):
    
    # 获取D
    D = contract.functions.D().call()
    
    # 获取price_scales
    price_scales = []
    for i in range(2):
        price_scale = contract.functions.price_scale(i).call()
        price_scales.append(price_scale)
    
    # 获取balances
    balances = []
    # for i in range(3):
    #     balance = contract.functions.balances(i).call()
    #     balances.append(balance)

    # packed_fee_params = contract.functions.packed_fee_params().call()

    graph_data['D'] = D
    graph_data['price_scales'] = price_scales
    graph_data['balances'] = balances
    # graph_data['packed_fee_params'] = packed_fee_params

    return graph_data

# --- Packing/Unpacking Helpers ---

def _unpack_A_gamma(packed_A_gamma):
    """Unpacks A and gamma."""
    gamma = packed_A_gamma & (2**128 - 1)
    A = packed_A_gamma >> 128
    return A, gamma

def _pack_A_gamma(A, gamma):
    """Packs A and gamma."""
    return (A << 128) | gamma

def _unpack_fee_params(packed_fee_params):
    """Unpacks mid_fee, out_fee, fee_gamma (assuming 3x uint64 packing)."""
    # Adjust mask if packing differs (e.g., if sizes aren't 64 bits)
    mask64 = (1 << 64) - 1
    mid_fee = (packed_fee_params >> 128) & mask64
    out_fee = (packed_fee_params >> 64) & mask64
    fee_gamma = packed_fee_params & mask64
    return mid_fee, out_fee, fee_gamma

def _pack_fee_params(mid_fee, out_fee, fee_gamma):
    """Packs mid_fee, out_fee, fee_gamma (assuming 3x uint64 packing)."""
    return (mid_fee << 128) | (out_fee << 64) | fee_gamma


def calculate_precisions(decimals, n_coins):
     """Calculate precision multipliers 10**(18-dec)"""
     precisions = [0] * n_coins
     for i in range(n_coins):
          precisions[i] = 10**(18 - decimals[i])
     return precisions

# --- Simulation of _fee ---
def math_reduction_coefficient_stub(xp, fee_gamma):
     """Placeholder for MATH.reduction_coefficient."""
     # Simplification: Assume no fee reduction based on imbalance.
     # A real implementation would need the complex math from the Math contract.
     return PRECISION # Return 1e18 => f = 1

def simulate_fee(xp_transformed, packed_fee_params):
     """Calculates the current dynamic fee rate."""
     mid_fee, out_fee, fee_gamma = _unpack_fee_params(packed_fee_params)

     # Call the (stubbed) reduction coefficient function
     f = math_reduction_coefficient_stub(xp_transformed, fee_gamma)

     # fee = (mid_fee * f + out_fee * (10**18 - f)) / 10**18
     fee_rate = (mid_fee * f + out_fee * (PRECISION - f)) // PRECISION
     return fee_rate

def simulate_exchange_crypto(
    graph_data: dict, 
    i: int,
    j: int, 
    dx_wei: float, 
) -> float:

    # ------ get data from abi ------
    POOL_ADDRESS = graph_data['address']
    contract = web3.eth.contract(address=POOL_ADDRESS, abi=ABI)
    start_time = time.time()
    pool_data = get_pool_data(graph_data, contract)
    end_time = time.time()
    print(f"time of cyptoswap get Price Scale and D: {end_time - start_time}秒")

    # Price Scale
    print(f"Price Scale: {pool_data['price_scales']}")
    # graph_data['price_scales'] = [87270075348870116906536, 1617902091481643950292]

    # Gamma & D
    graph_data['gamma'] = 11809167828997
    # graph_data['D'] = 10881703172801507158339723

    # Fee Params
    # mid_fee=3000000, out_fee=30000000, fee_gamma=500000000000000
    graph_data['packed_fee_params'] = 1020847100762815390943526144507091182848000000
    mid_fee, out_fee, fee_gamma = _unpack_fee_params(graph_data['packed_fee_params'])
    print(f"Fee Params: mid_fee={mid_fee}, out_fee={out_fee}, fee_gamma={fee_gamma}")

    # ------ reformat data ------
    n_coins = len(graph_data['coins'])
    balances = [int(c['poolBalance']) for c in graph_data['coins']]
    decimals = [int(d) for d in graph_data['decimals'][:n_coins]]

    precisions = calculate_precisions(decimals, n_coins)

    price_scales = graph_data['price_scales']
    print(f"Price Scale_in: {price_scales}")
    A, gamma = int(graph_data.get('amplificationCoefficient')), int(graph_data.get('gamma'))
    D = graph_data.get('D')
    # Unpack fee parameters
    if 'packed_fee_params' not in graph_data:
         print("Warning: 'packed_fee_params' missing. Using defaults.")
         mid_fee_def = 5 * 10**6 # 0.05%
         out_fee_def = 40 * 10**6 # 0.4%
         fee_gamma_def = 10**14 # 0.0001
         graph_data['packed_fee_params'] = _pack_fee_params(mid_fee_def, out_fee_def, fee_gamma_def)
    packed_fee_params = graph_data['packed_fee_params']


    # 
    xp = balances[:] # Create copy for calculations
    xp[i] += dx_wei
    print(f"Balances: {balances}")

    # ------ Calculate dy  ------
    xp_transformed = [0] * n_coins
    xp_transformed[0] = xp[0] * precisions[0] # Coin 0 doesn't use price_scales
    for k in range(1, n_coins):
         numerator = xp[k] * price_scales[k-1] * precisions[k]
         xp_transformed[k] = numerator // PRECISION

    print(f"A: {A}, gamma: {gamma}, xp_transformed: {xp_transformed}, D: {D}, j: {j}")
    # --- 4. Calculate Output y (Transformed) ---
    # @ztmyNOTE: Very sensitive to data
    # xp_transformed = [3636773717319000000000000, 3623502399087111374658793, 3644597404980384155843172] Output Amount (dy_transformed) = 26513461
    # xp_transformed = [3645971954936000000000000, 3605643365110515245119673, 3640101016789000861975746] Output Amount (dy_transformed) = 11409406
    y_transformed = get_y(A, gamma, xp_transformed, D, j)
    print(f"Output Balance (y_transformed): {y_transformed}")

    if y_transformed[0] >= xp_transformed[j]:
         print("Warning: Calculated y_transformed >= xp_transformed[j]. Likely zero output.")
         dy_transformed = 0
    else:
         dy_transformed = xp_transformed[j] - y_transformed[0] - 1

    # Update the transformed balance list for fee calculation
    xp_transformed[j] -= (dy_transformed + 1) # Update with the actual change
    print(f"Output Amount (dy_transformed): {dy_transformed}")


    # ------ Detransform dy to Underlying Units ------
    dy_detransformed = dy_transformed
    if j > 0:
         # dy = dy * PRECISION / price_scales[j-1]
         if price_scales[j-1] == 0: price_scales[j-1] = 1 # Avoid div zero
         dy_detransformed = dy_detransformed * PRECISION // price_scales[j-1]

    # dy /= prec_j
    if precisions[j] == 0: precisions[j] = 1 # Avoid div zero
    dy_underlying_wei = dy_detransformed // precisions[j]
    print(f"Output Amount (dy_underlying_wei, pre-fee): {dy_underlying_wei}")

    # ------ Subtract Fee ------
    fee_rate = simulate_fee(xp_transformed, packed_fee_params) # Pass final transformed balances
    fee_rate = graph_data.get('fee', fee_rate)
    fee_amount_wei = dy_underlying_wei * fee_rate // 10**10 # Apply fee rate
    print(f"Fee Rate: {fee_rate/10**10:.4%}, Fee Amount (wei): {fee_amount_wei}")

    amount_output_wei = dy_underlying_wei - fee_amount_wei

    return amount_output_wei

"""
the implementation get_dy in cyptoswap is in the views_implementation contract of the factory contract:

view_contract: address = Factory(self.factory).views_implementation()  = 0x064253915b8449fdEFac2c4A74aA9fdF56691a31
Views(view_contract).get_dy(i, j, dx, self)
"""
def simulate_exchange_crypto_get_dy(   
    graph_data: dict,
    dx_wei: float, 
    i: int,
    j: int, 
):
    start_time = time.time()
    POOL_ADDRESS = graph_data['address']
    contract = web3.eth.contract(address=POOL_ADDRESS, abi=ABI)
    amount_output_wei = contract.functions.get_dy(i, j, dx_wei).call()
    end_time = time.time()
    print(f"time of cyptoswap get dy: {end_time - start_time}秒")
    return amount_output_wei