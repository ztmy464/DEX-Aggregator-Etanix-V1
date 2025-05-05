import json
import math
import os # For precise calculations if needed, but stick to integer math mostly

# Constants
PRECISION = 10**18
FEE_DENOMINATOR = 10**10
MAX_ITERATIONS = 255

# --- Simulation Helpers (get_D, xp_mem, get_y adapted for variable N_COINS) ---

def xp_mem_rate(balances, rates, n_coins):
    """Normalizes balances using specific rates array"""
    xp = [0] * n_coins
    for i in range(n_coins):
        # Handle potential zero rate if virtual price is missing/zero
        if rates[i] == 0: rates[i] = 1 # Avoid division by zero, though problematic
        xp[i] = balances[i] * rates[i] // PRECISION
    return xp

def calculate_rates_from_decimals(decimals, n_coins):
    """Calculates RATES based on token decimals relative to 1e18"""
    rates = []
    precision_mul = []
    for i in range(n_coins):
        dec = decimals[i]
        pm = 10**(18 - int(dec))
        precision_mul.append(pm)
        rates.append(PRECISION * pm)
    return rates, precision_mul

def get_D(xp, amp, n_coins):
    """Calculates the invariant D using Newton's method."""
    S = sum(xp)
    if S == 0:
        return 0

    Dprev = 0
    D = S
    Ann = amp * n_coins # Use actual n_coins

    for _i in range(MAX_ITERATIONS):
        D_P = D
        for _x in xp:
            if _x == 0: _x = 1 # Prevent division by zero
            # Ensure D_P doesn't grow excessively large before division
            try:
                 # Calculate D_P = D_P * D / (_x * n_coins) safely
                 D_P = (D_P * D) // (_x * n_coins)
            except ZeroDivisionError:
                 print(f"Warning: Division by zero avoided in get_D loop (_x={_x}, n_coins={n_coins})")
                 D_P = 0 # Or handle differently
                 break # Exit loop if state is problematic


        Dprev = D
        numerator = (Ann * S + D_P * n_coins) * D
        denominator = (Ann - 1) * D + (n_coins + 1) * D_P
        if denominator == 0:
             print("Warning: Zero denominator in D calculation")
             D = Dprev # Fallback or error handling might be needed.
             break
        D = numerator // denominator

        if abs(D - Dprev) <= 1:
            break
    return D

def get_y(i: int, j: int, x: int, xp_: list[int], amp: int, n_coins: int) -> int:
    """Calculate the new balance of coin j (`y`)"""
    assert i != j
    assert 0 <= j < n_coins
    assert 0 <= i < n_coins

    D = get_D(xp_, amp, n_coins) # Use current balances for D
    if D == 0:
         print("Warning: D=0 in get_y")
         return 0 # Cannot calculate y if D is 0

    c = D
    S_ = 0
    Ann = amp * n_coins

    _x = 0
    for _i in range(n_coins):
        if _i == i:
            _x = x
        elif _i != j:
            _x = xp_[_i]
        else:
            continue
        S_ += _x
        if _x == 0: _x = 1 # Prevent division by zero
        # c = c * D // (_x * n_coins)
        try:
             c = (c * D) // (_x * n_coins)
        except ZeroDivisionError:
             print(f"Warning: Division by zero avoided in get_y loop 1 (_x={_x}, n_coins={n_coins})")
             c = 0
             break


    if Ann == 0: Ann = 1 # Prevent division by zero if A=0
    # c = c * D // (Ann * n_coins)
    try:
        c = (c * D) // (Ann * n_coins)
    except ZeroDivisionError:
         print(f"Warning: Division by zero avoided in get_y loop 2 (Ann={Ann}, n_coins={n_coins})")
         c = 0

    # b = S_ + D // Ann
    try:
        b = S_ + D // Ann
    except ZeroDivisionError:
         print(f"Warning: Division by zero avoided in get_y calculating b (Ann={Ann})")
         # Fallback: assume b is just S_ if Ann is effectively zero
         b = S_

    y_prev = 0
    y = D

    for _i in range(MAX_ITERATIONS):
        y_prev = y
        numerator = y*y + c
        denominator = 2 * y + b - D
        if denominator == 0:
            print("Warning: Zero denominator in y calculation loop")
            y = y_prev # Fallback
            break
        y = numerator // denominator

        if abs(y - y_prev) <= 1:
            break
    return y

def get_y_D(A_: int, i: int, xp: list[int], D: int, n_coins: int) -> int:
    """Calculate x[i] if D changes"""
    assert 0 <= i < n_coins

    if D == 0:
        print("Warning: D=0 in get_y_D")
        return 0 # Balance must be 0 if target D is 0

    c = D
    S_ = 0
    Ann = A_ * n_coins

    _x = 0
    for _i in range(n_coins):
        if _i != i:
            _x = xp[_i]
        else:
            continue
        S_ += _x
        if _x == 0: _x = 1 # Prevent division by zero
        # c = c * D // (_x * n_coins)
        try:
             c = (c * D) // (_x * n_coins)
        except ZeroDivisionError:
             print(f"Warning: Division by zero avoided in get_y_D loop 1 (_x={_x}, n_coins={n_coins})")
             c = 0
             break

    if Ann == 0: Ann = 1
    # c = c * D // (Ann * n_coins)
    try:
         c = (c * D) // (Ann * n_coins)
    except ZeroDivisionError:
         print(f"Warning: Division by zero avoided in get_y_D loop 2 (Ann={Ann}, n_coins={n_coins})")
         c = 0


    # b = S_ + D // Ann
    try:
        b = S_ + D // Ann
    except ZeroDivisionError:
         print(f"Warning: Division by zero avoided in get_y_D calculating b (Ann={Ann})")
         b = S_

    y_prev = 0
    y = D

    for _i in range(MAX_ITERATIONS):
        y_prev = y
        numerator = y*y + c
        denominator = 2 * y + b - D
        if denominator == 0:
            print("Warning: Zero denominator in y_D calculation loop")
            y = y_prev
            break
        y = numerator // denominator
        if abs(y - y_prev) <= 1:
            break
    return y

# --- Simulation Function: add_liquidity ---

def simulate_add_liquidity(
    pool_data: dict, # Contains balances, A, fee, admin_fee, N_COINS, decimals, totalSupply
    amounts: list[int], # Amounts in underlying units
    # min_mint_amount: int = 0 # Less relevant for simulation output
) -> int: # Returns estimated LP tokens minted
    """Simulates the add_liquidity function for a given pool."""

    balances = [int(c['poolBalance']) for c in pool_data['coins']]
    amp = int(pool_data['amplificationCoefficient'])
    total_supply = int(pool_data['totalSupply'])
    decimals = [int(d) for d in pool_data['decimals']]
    n_coins = len(pool_data['coins']) # Determine N_COINS from data
    # Assume fee structure if not present
    fee = pool_data.get('fee', 1 * 10**6) # Default to 0.01% if missing
    admin_fee = pool_data.get('adminFee', 50 * 10**8) # Default to 50% if missing

    # Calculate rates based on decimals for normalization
    rates, _ = calculate_rates_from_decimals(decimals, n_coins)

    # --- Fee for imbalance ---
    # _fee: uint256 = self.fee * N_COINS / (4 * (N_COINS - 1))
    imbalance_fee_rate = 0
    if n_coins > 1:
        imbalance_fee_rate = fee * n_coins // (4 * (n_coins - 1))
    else:
        imbalance_fee_rate = 0 # No imbalance fee for single coin pool

    # --- Initial State ---
    D0 = 0
    old_balances = balances[:] # Copy
    if total_supply > 0:
        # Normalize old balances using appropriate rates
        xp0 = xp_mem_rate(old_balances, rates, n_coins)
        D0 = get_D(xp0, amp, n_coins)

    # --- Calculate New Balances and D1 ---
    new_balances = old_balances[:] # Copy
    for i in range(n_coins):
        # Assuming amounts are already in correct underlying units
        # Note: Vyper code handles fee-on-transfer; we simplify here
        new_balances[i] += amounts[i]

    xp1 = xp_mem_rate(new_balances, rates, n_coins)
    D1 = get_D(xp1, amp, n_coins)

    # --- Calculate Imbalance Fees and D2 ---
    D2 = D1
    fees = [0] * n_coins
    balances_after_fee = new_balances[:] # Start with balances after adding amounts

    if total_supply > 0 and D0 > 0: # Avoid division by zero and skip fee for first deposit
        for i in range(n_coins):
            ideal_balance = D1 * old_balances[i] // D0
            difference = 0
            if ideal_balance > new_balances[i]:
                difference = ideal_balance - new_balances[i]
            else:
                difference = new_balances[i] - ideal_balance

            # Normalize difference to calculate fee based on normalized value change?
            # Vyper uses normalized difference: ideal_balance_xp = D1 * xp0[i] // D0 ... diff_xp = abs(ideal_balance_xp - xp1[i])
            # Let's recalculate based on normalized values for accuracy
            ideal_balance_xp = D1 * xp0[i] // D0
            diff_xp = abs(ideal_balance_xp - xp1[i])

            fees[i] = imbalance_fee_rate * diff_xp // FEE_DENOMINATOR # Fee in normalized units

            # Convert fee back to underlying units to subtract from balance
            # fee_underlying = fees[i] * PRECISION // rates[i] # This seems wrong, fee applies to normalized value change
            # The fee is deducted from the normalized balance implicitly before D2 calc

            # Let's follow the vyper logic more closely: fee affects the balances used for D2 calc
            # balances[i] = new_balances[i] - (fees[i] * _admin_fee / FEE_DENOMINATOR) <-- Vyper updates self.balances for admin fee share
            # new_balances[i] -= fees[i] <-- Vyper updates the array used for D2 calc with total imbalance fee

            # For simulation, we need the balances used for D2.
            # Fee is calculated based on normalized difference, let's apply it to the normalized balance xp1
            xp1[i] -= fees[i] # Reduce the normalized balance by the normalized fee

            # Admin fee part for tracking (less critical for mint amount)
            # admin_fee_share_normalized = fees[i] * admin_fee // FEE_DENOMINATOR
            # xp1[i] += admin_fee_share_normalized # Admin fee stays in pool (effectively) for D2 calc

        D2 = get_D(xp1, amp, n_coins) # Recalculate D with balances after fee deduction

    # --- Calculate Mint Amount ---
    mint_amount = 0
    if total_supply == 0:
        mint_amount = D1 # First depositor gets D LP tokens
    elif D0 > 0: # Ensure D0 is not zero before division
        # mint_amount = token_supply * (D2 - D0) / D0
        # Use uint256 math logic: multiply first
        mint_amount = total_supply * (D2 - D0) // D0
    else:
        mint_amount = 0 # Should not happen if total_supply > 0

    # assert mint_amount >= min_mint_amount
    return mint_amount

# --- Simulation Function: remove_liquidity_one_coin ---

def simulate_remove_liquidity_one_coin(
    pool_data: dict, # Contains balances, A, fee, admin_fee, N_COINS, decimals, totalSupply
    token_amount: int, # Amount of LP tokens to burn
    i: int, # Index of the coin to withdraw
    # min_amount: int = 0 # Less relevant for simulation output
) -> int: # Returns estimated amount of coin 'i' received
    """Simulates the remove_liquidity_one_coin function."""

    balances = [int(c['poolBalance']) for c in pool_data['coins']]
    amp = int(pool_data['amplificationCoefficient'])
    total_supply = int(pool_data['totalSupply'])
    decimals = [int(d['decimals']) for d in pool_data['coins']]
    n_coins = len(pool_data['coins'])
    fee = pool_data.get('fee', 800000)
    # admin_fee = pool_data.get('adminFee', 50 * 10**8)

    rates, precision_mul = calculate_rates_from_decimals(decimals, n_coins)

    # --- Fee for imbalance ---
    imbalance_fee_rate = 0
    if n_coins > 1:
        imbalance_fee_rate = fee * n_coins // (4 * (n_coins - 1))
    else:
        imbalance_fee_rate = 0

    # --- Calculate D0, D1 ---
    xp = xp_mem_rate(balances, rates, n_coins)
    D0 = get_D(xp, amp, n_coins)

    if total_supply == 0 or D0 == 0:
         print("Warning: Cannot remove liquidity from empty pool or pool with D=0.")
         return 0

    # D1: uint256 = D0 - _token_amount * D0 / total_supply
    D1 = D0 - token_amount * D0 // total_supply

    # --- Calculate expected output without fees (dy_0) ---
    # new_y: uint256 = self.get_y_D(amp, i, xp, D1)
    new_y = get_y_D(amp, i, xp, D1, n_coins)
    # dy_0: uint256 = (xp[i] - new_y) / precisions[i]
    dy_0_normalized = xp[i] - new_y
    if precision_mul[i] == 0: precision_mul[i] = 1 # Avoid division by zero
    dy_0_underlying = dy_0_normalized // precision_mul[i] # Equivalent to (X * P / R) / (P / R) ?? Let's recheck Vyper.
                                                          # Vyper: (xp[i] - new_y) / precisions[i]
                                                          # xp is normalized (bal * R / P). new_y is normalized.
                                                          # Difference is normalized. Division by precisions[i] (which is P/bal_precision or 10**(18-dec)) converts normalized diff back to underlying.
                                                          # Let's use rates: dy_0_underlying = dy_0_normalized * PRECISION // rates[i] seems more consistent.
    if rates[i] == 0: rates[i] = 1
    dy_0_underlying = dy_0_normalized * PRECISION // rates[i]


    # --- Calculate balances after fees (xp_reduced) ---
    xp_reduced = xp[:] # Copy
    for j in range(n_coins):
        # dx_expected: uint256 = 0 (This is the normalized difference)
        dx_expected_normalized = 0
        if j == i:
            dx_expected_normalized = xp[j] * D1 // D0 - new_y # How much coin j *should* have changed (neg change = reduction) -> This seems wrong.
                                                             # Vyper: xp[j] * D1/D0 is the ideal balance at D1. new_y is actual balance at D1.
                                                             # dx_expected = ideal_balance - actual_balance (difference from ideal for coin i)
            ideal_balance_j = xp[j] * D1 // D0
            dx_expected_normalized = abs(ideal_balance_j - new_y) # Use absolute difference representing imbalance magnitude

        else:
            # dx_expected = xp[j] - xp[j] * D1 / D0 (difference from ideal for other coins)
            ideal_balance_j = xp[j] * D1 // D0
            dx_expected_normalized = abs(xp[j] - ideal_balance_j) # Use absolute difference

        # xp_reduced[j] -= _fee * dx_expected / FEE_DENOMINATOR
        fee_normalized = imbalance_fee_rate * dx_expected_normalized // FEE_DENOMINATOR
        xp_reduced[j] -= fee_normalized # Apply fee deduction to normalized balance

    # --- Calculate actual output dy ---
    # dy: uint256 = xp_reduced[i] - self.get_y_D(amp, i, xp_reduced, D1)
    # dy = (dy - 1) / precisions[i]
    final_y = get_y_D(amp, i, xp_reduced, D1, n_coins)
    dy_normalized = xp_reduced[i] - final_y - 1 # -1 for vyper conservatism

    if dy_normalized < 0: dy_normalized = 0 # Cannot withdraw negative amount

    # Convert normalized dy back to underlying
    if rates[i] == 0: rates[i] = 1
    dy_underlying = dy_normalized * PRECISION // rates[i]

    # Calculate fee component (for info, not needed for return value dy)
    # dy_fee = dy_0_underlying - dy_underlying

    # assert dy >= min_amount
    return dy_underlying

# --- Simulation Function: exchange (for base pool) ---
# This is similar to the previous example, adapted slightly

def simulate_exchange(
    pool_data: dict, # Contains balances, A, fee, N_COINS, decimals
    i: int, # Input coin index within this pool
    j: int, # Output coin index within this pool
    dx_underlying: int, # Amount of input coin in its native decimals
    # min_dy: int = 0 # Less relevant for simulation output
) -> int: # Returns estimated dy in native decimals
    """Simulates the basic exchange function for a given pool."""

    balances = [int(c['poolBalance']) for c in pool_data['coins']]
    amp = int(pool_data['amplificationCoefficient'])
    decimals = [int(d) for d in pool_data['decimals']]
    n_coins = len(pool_data['coins'])
    fee = pool_data.get('fee', 1 * 10**6) # Default fee if needed

    rates, _ = calculate_rates_from_decimals(decimals, n_coins)

    # --- Normalize Balances ---
    xp = xp_mem_rate(balances, rates, n_coins)

    # --- Normalize Input ---
    # dx_normalized = dx_underlying * rates[i] // PRECISION
    if rates[i] == 0: rates[i] = 1
    dx_normalized = dx_underlying * rates[i] // PRECISION

    # --- Calculate New Input Balance (Normalized) ---
    x_normalized = xp[i] + dx_normalized

    # --- Calculate Output Balance (Normalized) using get_y ---
    y_normalized = get_y(i, j, x_normalized, xp, amp, n_coins)

    # --- Calculate Output Amount (Normalized, before fee) ---
    if y_normalized >= xp[j]:
        dy_normalized = 0
    else:
        dy_normalized = xp[j] - y_normalized - 1

    # --- Calculate Fee ---
    # Using dynamic fee requires more state (offpeg multiplier) - use simple fee for base pool here
    fee_amount_normalized = dy_normalized * fee // FEE_DENOMINATOR

    # --- Subtract Fee ---
    dy_after_fee_normalized = dy_normalized - fee_amount_normalized
    if dy_after_fee_normalized < 0: dy_after_fee_normalized = 0

    # --- Denormalize Output Amount ---
    if rates[j] == 0: rates[j] = 1
    dy_underlying = dy_after_fee_normalized * PRECISION // rates[j]

    return dy_underlying


# --- Main Simulation Function: exchange_underlying ---

def simulate_exchange_underlying(
    metapool_data: dict, # Graph data for the Metapool
    basepool_data: dict, # Synthesized/fetched data for the Basepool
    i: int, # Overall input index (0=MIM, 1=DAI, 2=USDC, 3=USDT)
    j: int, # Overall output index
    dx_underlying: int, # Amount of input coin in its native decimals
    # min_dy: int = 0 # Less relevant for simulation output
) -> int:
    """Simulates the exchange_underlying function of a Metapool."""

    META_N_COINS = 2 # Typically 2 for Metapools (e.g., MIM, 3CRV)
    BASE_N_COINS = 3 # For 3Pool

    # --- Extract Metapool Info ---
    meta_balances = [int(c['poolBalance']) for c in metapool_data['coins']]
    meta_decimals = [int(d) for d in metapool_data['decimals'][:META_N_COINS]]
    meta_amp = int(metapool_data['amplificationCoefficient'])
    meta_fee = metapool_data.get('fee', 4 * 10**6) # Assume 0.04% if missing


    # virtual price from 3CRV price in Metapool data
    base_virtual_price = int(basepool_data.get('virtualPrice'))
    print(f"base_virtual_price: {base_virtual_price}")

    # --- Map Indices ---
    # i/j: 0=Metacoin, 1=BaseCoin0, 2=BaseCoin1, ...
    # meta_i/j: 0=Metacoin, 1=BaseLPToken
    # base_i/j: 0=BaseCoin0, 1=BaseCoin1, ...
    base_i: int = -1
    base_j: int = -1
    meta_i: int = -1
    meta_j: int = -1
    MAX_COIN_META = META_N_COINS # Number of direct coins in Metapool

    if i == 0:
        meta_i = 0
        # Need input decimals for the specific coin i
        input_decimals = int(metapool_data['underlyingCoins'][0]['decimals'])
    else:
        base_i = i - 1 # Convert overall index (1,2,3) to base index (0,1,2)
        meta_i = 1 # Input is via the base LP token position
        input_decimals = int(metapool_data['underlyingCoins'][i]['decimals'])

    if j == 0:
        meta_j = 0
        output_decimals = int(metapool_data['underlyingCoins'][0]['decimals'])
    else:
        base_j = j - 1 # Convert overall index (1,2,3) to base index (0,1,2)
        meta_j = 1 # Output is via the base LP token position
        output_decimals = int(metapool_data['underlyingCoins'][j]['decimals'])

    # Convert dx_underlying from human readable to integer with decimals
    dx_underlying_wei = int(dx_underlying * (10**input_decimals))
    print(f"dx_underlying: {dx_underlying}")
    print(f"input_decimals: {input_decimals}")
    print(f"dx_underlying_wei: {dx_underlying_wei}")

    # --- Prepare Metapool Rates ---
    # rates: [rate_multiplier for coin0, virtual_price for coin1]
    meta_rates = [PRECISION, base_virtual_price] # Assume rate_multiplier=1e18 for MIM


    final_dy_underlying = 0

    # --- Case 1: Involves Metapool Coin (i=0 or j=0) ---
    if i == 0 or j == 0:
        print(f"Simulating Metapool path: i={i}, j={j}")
        # Normalize metapool balances
        xp_meta = xp_mem_rate(meta_balances, meta_rates, META_N_COINS)
        print(f"Metapool Balances: {meta_balances}")
        print(f"Metapool Rates: {meta_rates}")
        print(f"Metapool Normalized Balances (xp_meta): {xp_meta}")

        x_normalized = 0 # This will be the new normalized balance of the input side (meta_i)
        dx_meta_normalized = 0 # Normalized amount added to the metapool input side

        # --- Subcase 1a: Input is Base Pool Coin (i > 0) ---
        if i > 0:
            print(f"  Subpath: Basepool coin ({base_i}) -> Base LP ({meta_i}) -> Metapool coin ({meta_j})")
            # Deposit dx into Base Pool to get LP tokens (3CRV)
            base_inputs = [0] * BASE_N_COINS
            base_inputs[base_i] = dx_underlying_wei

            # Simulate add_liquidity on basepool
            # Returns amount of LP token minted
            dx_base_lp_received = simulate_add_liquidity(
                pool_data=basepool_data,
                amounts=base_inputs
            )
            print(f"  Simulated Basepool add_liquidity: {dx_underlying_wei / (10**input_decimals)} coin {base_i} -> {dx_base_lp_received / PRECISION} Base LP")

            # Normalize the received LP tokens using virtual price (rate for meta_i=1)
            # dx_meta_normalized = dx_base_lp_received * meta_rates[meta_i] // PRECISION
            if meta_rates[meta_i] == 0: meta_rates[meta_i] = 1
            dx_meta_normalized = dx_base_lp_received * meta_rates[meta_i] // PRECISION
            x_normalized = xp_meta[meta_i] + dx_meta_normalized

        # --- Subcase 1b: Input is Metapool Coin (i == 0) ---
        else: # i == 0
            print(f"  Subpath: Metapool coin ({meta_i}) -> Metapool Swap -> Base LP ({meta_j})")
            # Normalize input dx (MIM)
            # dx_meta_normalized = dx_underlying_wei * meta_rates[meta_i] // PRECISION
            if meta_rates[meta_i] == 0: meta_rates[meta_i] = 1
            dx_meta_normalized = dx_underlying_wei * meta_rates[meta_i] // PRECISION
            x_normalized = xp_meta[meta_i] + dx_meta_normalized

        # --- Metapool Swap Calculation ---
        # Calculate the output balance 'y' on the other side of the metapool
        print(f"  Metapool Swap Input: x_normalized={x_normalized} (for index {meta_i})")
        y_normalized = get_y(meta_i, meta_j, x_normalized, xp_meta, meta_amp, META_N_COINS)
        print(f"  Metapool Swap Output: y_normalized={y_normalized} (for index {meta_j})")

        # Calculate dy (normalized amount out of metapool, before fees)
        if y_normalized >= xp_meta[meta_j]:
            dy_meta_normalized = 0
        else:
            dy_meta_normalized = xp_meta[meta_j] - y_normalized - 1
            print(f"xp_meta[meta_j] - y_normalized: {xp_meta[meta_j]} - {y_normalized} - 1 = {dy_meta_normalized}")
        print(f"  Metapool Swap Output (dy_meta_normalized, pre-fee): {dy_meta_normalized}")


        # Apply Metapool fee
        # dy_fee: uint256 = dy * self.fee / FEE_DENOMINATOR
        dy_fee_meta_normalized = dy_meta_normalized * meta_fee // FEE_DENOMINATOR
        print(f"  Metapool Swap Fee (Normalized): {dy_fee_meta_normalized}")
        dy_meta_after_fee_normalized = dy_meta_normalized - dy_fee_meta_normalized
        if dy_meta_after_fee_normalized < 0: dy_meta_after_fee_normalized = 0
        print(f"  Metapool Swap Output (dy_meta_normalized, after-fee): {dy_meta_after_fee_normalized}")


        # Convert metapool output back to underlying units (either MIM or 3CRV)
        # dy = (dy - dy_fee) * PRECISION / rates[meta_j]
        if meta_rates[meta_j] == 0: meta_rates[meta_j] = 1
        dy_metapool_underlying = dy_meta_after_fee_normalized * PRECISION // meta_rates[meta_j]
        print(f"  Metapool Swap Output (Underlying Units): {dy_metapool_underlying}")


        # --- Subcase 2a: Output is Metapool Coin (j == 0) ---
        if j == 0:
            final_dy_underlying = dy_metapool_underlying # The output is already the Metapool coin

        # --- Subcase 2b: Output is Base Pool Coin (j > 0) ---
        else: # j > 0
             print(f"  Subpath: Base LP ({meta_j}) -> Basepool remove_liquidity_one_coin -> Basepool coin ({base_j})")
             # dy_metapool_underlying is the amount of Base LP token (3CRV) to remove
             lp_token_to_remove = dy_metapool_underlying

             # Simulate remove_liquidity_one_coin on basepool
             final_dy_underlying = simulate_remove_liquidity_one_coin(
                 pool_data=basepool_data,
                 token_amount=lp_token_to_remove,
                 i=base_j # Index of the target base coin
             )
             print(f"  Simulated Basepool remove_liquidity_one_coin: {lp_token_to_remove / PRECISION} Base LP -> {final_dy_underlying / (10**output_decimals)} coin {base_j}")


    # --- Case 2: Both i and j are Base Pool Coins (i > 0 and j > 0) ---
    else:
        print(f"Simulating Basepool direct path: i={i}, j={j}")
        # Directly call exchange on the base pool
        final_dy_underlying = simulate_exchange(
            pool_data=basepool_sim_data,
            i=base_i,
            j=base_j,
            dx_underlying=dx_underlying_wei
        )
        print(f"  Simulated Basepool exchange: {dx_underlying_wei / (10**input_decimals)} coin {base_i} -> {final_dy_underlying / (10**output_decimals)} coin {base_j}")


    print("-" * 20)
    print(f"Final Estimated Output (Underlying Wei): {final_dy_underlying}")
    print(f"Final Estimated Output ({metapool_data['underlyingCoins'][j]['symbol']}): {final_dy_underlying / (10**output_decimals):.8f}")
    print("-" * 20)

    # assert dy >= min_dy
    return final_dy_underlying


# --- Load Data and Run Simulation ---

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
filt_pools_path = os.path.join(BASE_DIR, 'test_out', f'data_Curve.json')
with open(filt_pools_path, "r", encoding="utf-8") as f:
# with open(filt_pools_path, "w", encoding="utf-8") as f:
    # json.dump(filt_pools, f, ensure_ascii=False, indent=2)
    filt_pools = json.load(f)

target_address = "0x5a6A4D54456819380173272A5E8E9B9904BdF41B"
matched_pools = [pool for pool in filt_pools if pool["address"].lower() == target_address.lower()][0]

metapool_graph_data = {
    "id": "40",
    "address": "0x5a6A4D54456819380173272A5E8E9B9904BdF41B",
    "coinsAddresses": [
      "0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3",
      "0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490",
      "0x0000000000000000000000000000000000000000",
      "0x0000000000000000000000000000000000000000"
    ],
    "decimals": [
      "18",
      "18",
      "0",
      "0"
    ],
    "virtualPrice": "1017227965741177344",
    "amplificationCoefficient": "2000",
    "underlyingDecimals": [
      "18",
      "18",
      "6",
      "6",
      "0",
      "0",
      "0",
      "0"
    ],
    "totalSupply": "34065079329812973834178068",
    "name": "Curve.fi Factory USD Metapool: Magic Internet Money 3Pool",
    "assetType": "0",
    "priceOracle": None,
    "implementation": "",
    "zapAddress": "0xa79828df1850e8a3a3064576f380d90aecdd3359",
    "assetTypeName": "usd",
    "coins": [
      {
        "address": "0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3",
        "usdPrice": 1.0000475872841164,
        "decimals": "18",
        "isBasePoolLpToken": False,
        "symbol": "MIM",
        "name": "Magic Internet Money",
        "poolBalance": "15157905236649590199732025"
      },
      {
        "address": "0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490",
        "usdPrice": 1.0397136332751944,
        "decimals": "18",
        "isBasePoolLpToken": True,
        "symbol": "3Crv",
        "name": "Curve.fi DAI/USDC/USDT",
        "poolBalance": "18747316279323561851052971"
      }
    ],
    "poolUrls": {
      "swap": [
        "https://curve.fi/dex/#/ethereum/pools/mim/swap",
        "https://classic.curve.fi/mim"
      ],
      "deposit": [
        "https://curve.fi/dex/#/ethereum/pools/mim/deposit",
        "https://classic.curve.fi/mim/deposit"
      ],
      "withdraw": [
        "https://curve.fi/dex/#/ethereum/pools/mim/withdraw",
        "https://classic.curve.fi/mim/withdraw"
      ]
    },
    "lpTokenAddress": "0x5a6A4D54456819380173272A5E8E9B9904BdF41B",
    "usdTotal": 34650466.88312739,
    "isMetaPool": True,
    "basePoolAddress": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
    "underlyingCoins": [
      {
        "address": "0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3",
        "usdPrice": 1.0000475872841164,
        "decimals": "18",
        "isBasePoolLpToken": False,
        "symbol": "MIM",
        "name": "Magic Internet Money",
        "poolBalance": "15157905236649590199732025"
      },
      {
        "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "usdPrice": 1.000122583197268,
        "decimals": "18",
        "isBasePoolLpToken": False,
        "symbol": "DAI",
        "name": "Dai Stablecoin",
        "poolBalance": "5394782636573904665571605"
      },
      {
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "usdPrice": 1,
        "decimals": "6",
        "isBasePoolLpToken": False,
        "symbol": "USDC",
        "name": "USD Coin",
        "poolBalance": "5932597552310"
      },
      {
        "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "usdPrice": 0.9999472562484096,
        "decimals": "6",
        "isBasePoolLpToken": False,
        "symbol": "USDT",
        "name": "Tether USD",
        "poolBalance": "8166844064344"
      }
    ],
    "usdTotalExcludingBasePool": 15158626.560192695,
    "gaugeAddress": "0xd8b712d29381748db89c36bca0138d7c75866ddf",
    "gaugeRewards": [
      {
        "gaugeAddress": "0xd8b712d29381748db89c36bca0138d7c75866ddf",
        "tokenPrice": 0.0005416537722306512,
        "name": "Spell Token",
        "symbol": "SPELL",
        "decimals": "18",
        "apy": 0,
        "tokenAddress": "0x090185f2135308BaD17527004364eBcC2D37e5F6"
      }
    ],
    "gaugeCrvApy": [
      5.8410047482251075,
      14.602511870562768
    ],
    "gaugeFutureCrvApy": [
      5.832377244648402,
      14.580943111621005
    ],
    "usesRateOracle": False,
    "isBroken": False,
    "hasMethods": {
      "exchange_received": False,
      "exchange_extended": False
    },
    "creationTs": 1622671203,
    "creationBlockNumber": 12557139,
    "blockchainId": "ethereum",
    "registryId": "main"
  }

basepool_address = metapool_graph_data['basePoolAddress']

# get basepool data from the basepool
basepool_data_sim = [pool for pool in filt_pools if pool["address"].lower() == basepool_address.lower()][0]


# --- Run the Test Case ---
input_token_index_overall = 0  # MIM
output_token_index_overall = 1 # DAI (Index 1 overall -> Index 0 in Basepool)
input_amount_human = 1000    # 1000 MIM

print(f"--- Starting Simulation: {input_amount_human} {metapool_graph_data['underlyingCoins'][input_token_index_overall]['symbol']} -> {metapool_graph_data['underlyingCoins'][output_token_index_overall]['symbol']} ---")

estimated_output_underlying = simulate_exchange_underlying(
    metapool_data=matched_pools,
    basepool_data=basepool_data_sim, # Pass the synthesized/assumed basepool data
    i=input_token_index_overall,
    j=output_token_index_overall,
    dx_underlying=input_amount_human # Pass human amount, conversion happens inside
)

print(f"--- Simulation Complete ---")