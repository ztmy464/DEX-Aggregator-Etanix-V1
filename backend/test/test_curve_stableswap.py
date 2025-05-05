import json
import os

# Constants from Vyper contract (or derived)
N_COINS = 3
PRECISION = 10**18
FEE_DENOMINATOR = 10**10
# MAX_ITERATIONS for Newton's method to prevent infinite loops
MAX_ITERATIONS = 255

def calculate_rates(decimals):
    """Calculates RATES based on token decimals"""
    rates = []
    precision_mul = []
    for dec in decimals:
        pm = 10**(18 - int(dec))
        precision_mul.append(pm)
        rates.append(PRECISION * pm)
    return rates, precision_mul

def xp_mem(balances, rates):
    """Normalizes balances to PRECISION (1e18)"""
    xp = [0] * N_COINS
    for i in range(N_COINS):
        xp[i] = balances[i] * rates[i] // PRECISION
    return xp

def get_D(xp, amp):
    """
    Calculates the invariant D using Newton's method.
    xp: list of normalized balances
    amp: Amplification coefficient (A)
    """
    S = sum(xp)
    if S == 0:
        return 0

    Dprev = 0
    D = S
    Ann = amp * N_COINS

    for _i in range(MAX_ITERATIONS):
        D_P = D
        for _x in xp:
            # Avoid division by zero if a balance is zero
            if _x == 0:
                 # In reality, this case might require special handling or revert,
                 # but for simulation, we can try to continue or return an error.
                 # Let's prevent division by zero. A pool with 0 balance for a coin
                 # shouldn't allow swaps involving that coin in one direction.
                 # Returning 0 might be misleading. Let's assume valid state for simulation.
                 # A very small number might be safer than division by zero.
                 _x = 1 # Use 1 wei instead of 0 to avoid division error, though this isn't perfect.
            D_P = D_P * D // (_x * N_COINS)

        Dprev = D
        # Calculate D = (Ann * S + D_P * N_COINS) * D // ((Ann - 1) * D + (N_COINS + 1) * D_P)
        numerator = (Ann * S + D_P * N_COINS) * D
        denominator = (Ann - 1) * D + (N_COINS + 1) * D_P
        if denominator == 0:
             # Handle potential division by zero in the denominator as well
             print("Warning: Zero denominator in D calculation")
             # Fallback or error handling might be needed. Using previous D.
             D = Dprev
             break

        D = numerator // denominator

        if abs(D - Dprev) <= 1:
            break
    return D

def get_y(i: int, j: int, x: int, xp_: list[int], amp: int) -> int:

    # Should be unreachable, but good for safety
    assert i != j
    assert 0 <= j < N_COINS
    assert 0 <= i < N_COINS
                           
    D = get_D(xp_, amp) # Calculate D based on the state *before* input x is added.

    c = D
    S_ = 0
    Ann = amp * N_COINS

    _x = 0
    for _i in range(N_COINS):
        if _i == i:
            _x = x  # Use the new balance for the input coin
        elif _i != j:
            _x = xp_[_i] # Use the original balance for other coins
        else:
            continue # Skip the output coin j for now
        S_ += _x
        # c = c * D // (_x * N_COINS)
        if _x == 0: _x = 1 # Prevent division by zero
        c = c * D // (_x * N_COINS)

    # c = c * D // (Ann * N_COINS)
    if Ann == 0: Ann = 1 # Prevent division by zero
    c = c * D // (Ann * N_COINS)

    # b = S_ + D // Ann
    if Ann == 0: Ann = 1 # Prevent division by zero
    b = S_ + D // Ann  # D is subtracted in the main loop equation

    y_prev = 0
    y = D # Initial guess for y

    for _i in range(MAX_ITERATIONS):
        y_prev = y
        # y = (y*y + c) // (2 * y + b - D)
        numerator = y*y + c
        denominator = 2 * y + b - D
        if denominator == 0:
            # Handle potential division by zero
            print("Warning: Zero denominator in y calculation")
            y = y_prev # Fallback to previous value
            break
        y = numerator // denominator

        if abs(y - y_prev) <= 1:
            break

    return y

# --- Dynamic fee calculation function ---
def calculate_dynamic_fee(xpi_avg, xpj_avg, base_fee, offpeg_fee_multiplier, fee_denominator):
    """Calculate dynamic fee based on average balances."""
    if offpeg_fee_multiplier <= fee_denominator:
        return base_fee

    xps2 = (xpi_avg + xpj_avg) ** 2
    if xps2 == 0:
        print("Warning: xps2 is zero.")
        term_numerator = 0
        term_denominator = 1
    else:
        term_numerator = 4 * xpi_avg * xpj_avg
        term_denominator = xps2

    part1_numerator = (offpeg_fee_multiplier - fee_denominator) * term_numerator
    part1_denominator = term_denominator
    part2_numerator = fee_denominator * part1_denominator
    part2_denominator = part1_denominator

    denominator_sum_numerator = part1_numerator + part2_numerator
    denominator_sum_denominator = part1_denominator

    final_numerator = offpeg_fee_multiplier * base_fee * denominator_sum_denominator
    final_denominator = denominator_sum_numerator

    if final_denominator == 0:
        print("Warning: Final denominator is zero.")
        return base_fee

    dynamic_fee_rate = final_numerator // final_denominator
    return dynamic_fee_rate

def simulate_exchange(graph_data: dict, i: int, j: int, dx_underlying: int) -> int:
    """
    Simulates the Curve exchange function.

    Args:
        graph_data: Dictionary containing pool data from The Graph.
        i: Index of the input coin (e.g., 0 for DAI).
        j: Index of the output coin (e.g., 1 for USDC).
        dx_underlying: Amount of input coin in its native decimals (e.g., 1000 * 10**18 for 1000 DAI).

    Returns:
        Estimated amount of output coin in its native decimals.
    """
    # --- 1. Extract Data & Initialize ---
    decimals = [int(d) for d in graph_data['decimals'][:N_COINS]]
    balances_str = [c['poolBalance'] for c in graph_data['coins'][:N_COINS]]
    balances = [int(b) for b in balances_str]
    # Use the amplification coefficient directly from graph data
    amp = int(graph_data['amplificationCoefficient'])

    # TODO: get fee from graph data
    pool_fee = 4 * 10**6   # fee * 1e10 = 0.01% * 1e10 = 1,000,000

    rates, _ = calculate_rates(decimals)

    print(f"Simulating exchange: {dx_underlying / (10**decimals[i])} {graph_data['coins'][i]['symbol']} -> {graph_data['coins'][j]['symbol']}")
    print(f"Pool Balances: {[f'{b / (10**decimals[k]):,.2f}' for k, b in enumerate(balances)]}")

    # --- 2. Normalize Balances ---
    xp = xp_mem(balances, rates)
    print(f"balances: {balances}")
    print(f"rates: {rates}")
    print(f"Normalized Balances (xp): {xp}")

    # --- 3. Normalize Input Amount ---
    dx_normalized = dx_underlying * rates[i] // PRECISION
    print(f"Normalized Input (dx_normalized): {dx_normalized}")

    # --- 4. Calculate New Input Balance (Normalized) ---
    x_normalized = xp[i] + dx_normalized
    print(f"New Input Balance (x_normalized): {x_normalized}")

    # --- 5. Calculate Output Balance (Normalized) using get_y ---
    # We pass the *original* normalized balances `xp` and the *new* input value `x_normalized`
    y_normalized = get_y(i, j, x_normalized, xp, amp)
    print(f"New Output Balance (y_normalized): {y_normalized}")

    # --- 6. Calculate Output Amount (Normalized) ---
    # dy_normalized = xp[j] - y_normalized - 1 <-- Need to handle potential negative if pool improves?
    # Should be xp[j] - y_normalized. The -1 is a Vyper adjustment.
    # Ensure y < xp[j]
    if y_normalized >= xp[j]:
         print(f"Warning: Calculated new balance y ({y_normalized}) >= old balance xp[j] ({xp[j]}). Negative/zero output before fees.")
         # This might happen with tiny swaps or rounding issues. Assume 0 output.
         dy_normalized = 0
    else:
         dy_normalized = xp[j] - y_normalized -1 # Keep the -1 as per Vyper code for conservatism
         print(f"xp[j] - y_normalized: {xp[j]} - {y_normalized} - 1 = {dy_normalized}")

    print(f"Output Amount Before Fee (dy_normalized): {dy_normalized}")


    # --- 7. Calculate Fee ---
    # fixd fee
    # fee_amount_normalized = dy_normalized * pool_fee // FEE_DENOMINATOR
    # print(f"Fee Amount (fee_amount_normalized): {fee_amount_normalized}")

    # NOTE:dynamic fee
    offpeg_fee_multiplier = 500000
    # Calculate average balances
    xpi_avg = (xp[i] + x_normalized) // 2
    xpj_avg = (xp[j] + y_normalized) // 2
    print(f"Average Balances for Fee Calc: xpi_avg={xpi_avg}, xpj_avg={xpj_avg}")

    # Calculate dynamic fee rate
    dynamic_fee_rate = calculate_dynamic_fee(
        xpi_avg,
        xpj_avg,
        pool_fee,
        offpeg_fee_multiplier,
        FEE_DENOMINATOR
    )
    print(f"Base Fee Rate: {pool_fee} ({pool_fee / FEE_DENOMINATOR * 100:.4f}%)")
    print(f"Calculated Dynamic Fee Rate: {dynamic_fee_rate} ({dynamic_fee_rate / FEE_DENOMINATOR * 100:.4f}%)")
    print(f"  Metapool Swap Output (dy_meta_normalized, pre-fee): {dy_normalized}")

    # Apply dynamic fee
    fee_amount_normalized = dy_normalized * dynamic_fee_rate // FEE_DENOMINATOR

    # --- 8. After Fee ---
    dy_after_fee_normalized = dy_normalized - fee_amount_normalized
    print(f"Output Amount After Fee (dy_after_fee_normalized): {dy_after_fee_normalized}")

    dy_underlying = dy_after_fee_normalized * PRECISION // rates[j]
    print(f"Denormalized Output (dy_underlying): {dy_underlying}")

    output_coin_symbol = graph_data['coins'][j]['symbol']
    output_decimals = decimals[j]
    print(f"\nEstimated output: {dy_underlying / (10**output_decimals):.6f} {output_coin_symbol}")

    return dy_underlying



# ---------------------------- Load Data and Run Simulation ----------------------------

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
filt_pools_path = os.path.join(BASE_DIR, 'test_out', f'data_Curve.json')
with open(filt_pools_path, "r", encoding="utf-8") as f:
# with open(filt_pools_path, "w", encoding="utf-8") as f:
    # json.dump(filt_pools, f, ensure_ascii=False, indent=2)
    filt_pools = json.load(f)

target_address = "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7"
matched_pools = [pool for pool in filt_pools if pool["address"].lower() == target_address.lower()]

# if "underlyingDecimals" in matched_pools[0]:
#     print("use underlying----")
#     matched_pools[0]["decimals"] = matched_pools[0].pop("underlyingDecimals")
# if "underlyingCoins" in matched_pools[0]:
#     matched_pools[0]["coins"] = matched_pools[0].pop("underlyingCoins")

graph_data = matched_pools[0]


# Simulation parameters
input_token_index = 0  # DAI
output_token_index = 1 # USDC
input_amount_human = 1000 # 1000 DAI


# Convert input amount to underlying units (wei for DAI)
input_decimals = int(graph_data['decimals'][input_token_index])
input_amount_underlying = int(input_amount_human * (10**input_decimals))

# Run the simulation
estimated_output_underlying = simulate_exchange(
    graph_data=matched_pools[0],
    i=input_token_index,
    j=output_token_index,
    dx_underlying=input_amount_underlying
)