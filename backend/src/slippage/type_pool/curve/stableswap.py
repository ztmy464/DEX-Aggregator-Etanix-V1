
# TODO:Constants
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
# --- Simulation Function: add_liquidity ---

def simulate_add_liquidity(
    pool_data: dict,
    amounts: list[int],
) -> int: # Returns estimated LP tokens minted
    """Simulates the add_liquidity function for a given pool."""

    balances = [int(c['poolBalance']) for c in pool_data['coins']]
    amp = int(pool_data['amplificationCoefficient'])
    total_supply = int(pool_data['totalSupply'])
    decimals = [int(d) for d in pool_data['decimals']]
    n_coins = len(pool_data['coins']) # Determine N_COINS from data
    # Assume fee structure if not present
    fee = pool_data.get('fee', 4000000) # Default to 0.04% if missing

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

    
            ideal_balance_xp = D1 * xp0[i] // D0
            diff_xp = abs(ideal_balance_xp - xp1[i])

            fees[i] = imbalance_fee_rate * diff_xp // FEE_DENOMINATOR # Fee in normalized units

            xp1[i] -= fees[i] # Reduce the normalized balance by the normalized fee

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
    fee = pool_data.get('fee', 4000000)
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
    dy_0_underlying = dy_0_normalized // precision_mul[i] 
    if rates[i] == 0: rates[i] = 1
    dy_0_underlying = dy_0_normalized * PRECISION // rates[i]


    # --- Calculate balances after fees (xp_reduced) ---
    xp_reduced = xp[:] # Copy
    for j in range(n_coins):
        # dx_expected: uint256 = 0 (This is the normalized difference)
        dx_expected_normalized = 0
        if j == i:
            dx_expected_normalized = xp[j] * D1 // D0 - new_y # How much coin j *should* have changed (neg change = reduction) -> This seems wrong.
                                                            
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

    return dy_underlying

# --- Simulation Function: exchange (for base pool) ---
# This is similar to the previous example, adapted slightly

def simulate_exchange(
        pool_data: dict, 
        dx: int,
        i: int, 
        j: int 
        ) -> int:
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
    N_COINS = len(pool_data['coins'])
    decimals = [int(d) for d in pool_data['decimals'][:N_COINS]]
    balances_str = [c['poolBalance'] for c in pool_data['coins'][:N_COINS]]
    balances = [int(b) for b in balances_str]
    # Use the amplification coefficient directly from graph data
    amp = int(pool_data['amplificationCoefficient'])

    # TODO: get fee from graph data
    fee = pool_data.get('fee', 4000000)   # fee * 1e10 = 0.01% * 1e10 = 1,000,000

    rates, _ = calculate_rates_from_decimals(decimals, N_COINS)

    # --- 2. Normalize Balances ---
    xp = xp_mem_rate(balances, rates, N_COINS)

    # --- 3. Normalize Input Amount ---
    dx_normalized = dx * rates[i] // PRECISION

    # --- 4. Calculate New Input Balance (Normalized) ---
    x_normalized = xp[i] + dx_normalized

    # --- 5. Calculate Output Balance (Normalized) using get_y ---
    # We pass the *original* normalized balances `xp` and the *new* input value `x_normalized`
    y_normalized = get_y(i, j, x_normalized, xp, amp, N_COINS)

    # --- 6. Calculate Output Amount (Normalized) ---

    if y_normalized >= xp[j]:
         print(f"Warning: Calculated new balance y ({y_normalized}) >= old balance xp[j] ({xp[j]}). Negative/zero output before fees.")
         # This might happen with tiny swaps or rounding issues. Assume 0 output.
         dy_normalized = 0
    else:
         dy_normalized = xp[j] - y_normalized -1 # Keep the -1 as per Vyper code for conservatism

    # --- 7. Calculate Fee ---

    # TODO:NOTE:dynamic fee
    offpeg_fee_multiplier = pool_data.get('offpeg_fee_multiplier', 1)
    # Calculate average balances
    xpi_avg = (xp[i] + x_normalized) // 2
    xpj_avg = (xp[j] + y_normalized) // 2

    # Calculate dynamic fee rate
    dynamic_fee_rate = calculate_dynamic_fee(
        xpi_avg,
        xpj_avg,
        fee,
        offpeg_fee_multiplier,
        FEE_DENOMINATOR
    )

    # Apply dynamic fee
    fee_amount_normalized = dy_normalized * dynamic_fee_rate // FEE_DENOMINATOR

    # --- 8. After Fee ---
    dy_after_fee_normalized = dy_normalized - fee_amount_normalized
    amount_output_wei = dy_after_fee_normalized * PRECISION // rates[j]

    return amount_output_wei


# --- Main Simulation Function: exchange_underlying ---

def simulate_exchange_underlying(
    metapool_data: dict, # Graph data for the Metapool
    basepool_data: dict, # Synthesized/fetched data for the Basepool
    dx_underlying_wei: int, # Amount of input coin in its native decimals
    i: int, # Overall input index (0=MIM, 1=DAI, 2=USDC, 3=USDT)
    j: int, # Overall output index
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

    # --- Map Indices ---
    # i/j: 0=Metacoin, 1=BaseCoin0, 2=BaseCoin1, ...
    # meta_i/j: 0=Metacoin, 1=BaseLPToken
    # base_i/j: 0=BaseCoin0, 1=BaseCoin1, ...
    base_i: int = -1
    base_j: int = -1
    meta_i: int = -1
    meta_j: int = -1

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

    # --- Prepare Metapool Rates ---
    # rates: [rate_multiplier for coin0, virtual_price for coin1]
    meta_rates = [PRECISION, base_virtual_price] # Assume rate_multiplier=1e18 for MIM


    amount_out_underlying_wei = 0

    # --- Case 1: Involves Metapool Coin (i=0 or j=0) ---
    if i == 0 or j == 0:
        print(f"Simulating Metapool path: i={i}, j={j}")
        # Normalize metapool balances
        xp_meta = xp_mem_rate(meta_balances, meta_rates, META_N_COINS)

        x_normalized = 0 # This will be the new normalized balance of the input side (meta_i)
        dx_meta_normalized = 0 # Normalized amount added to the metapool input side

        # --- Subcase 1a: Input is Base Pool Coin (i > 0) ---
        if i > 0:
            # Deposit dx into Base Pool to get LP tokens (3CRV)
            base_inputs = [0] * BASE_N_COINS
            base_inputs[base_i] = dx_underlying_wei

            # Simulate add_liquidity on basepool
            # Returns amount of LP token minted
            dx_base_lp_received = simulate_add_liquidity(
                pool_data=basepool_data,
                amounts=base_inputs
            )

            # Normalize the received LP tokens using virtual price (rate for meta_i=1)
            # dx_meta_normalized = dx_base_lp_received * meta_rates[meta_i] // PRECISION
            if meta_rates[meta_i] == 0: meta_rates[meta_i] = 1
            dx_meta_normalized = dx_base_lp_received * meta_rates[meta_i] // PRECISION
            x_normalized = xp_meta[meta_i] + dx_meta_normalized

        # --- Subcase 1b: Input is Metapool Coin (i == 0) ---
        else: # i == 0
            # Normalize input dx (MIM)
            # dx_meta_normalized = dx_underlying_wei * meta_rates[meta_i] // PRECISION
            if meta_rates[meta_i] == 0: meta_rates[meta_i] = 1
            dx_meta_normalized = dx_underlying_wei * meta_rates[meta_i] // PRECISION
            x_normalized = xp_meta[meta_i] + dx_meta_normalized

        # --- Metapool Swap Calculation ---
        # Calculate the output balance 'y' on the other side of the metapool
        y_normalized = get_y(meta_i, meta_j, x_normalized, xp_meta, meta_amp, META_N_COINS)

        # Calculate dy (normalized amount out of metapool, before fees)
        if y_normalized >= xp_meta[meta_j]:
            dy_meta_normalized = 0
        else:
            dy_meta_normalized = xp_meta[meta_j] - y_normalized - 1


        # Apply Metapool fee
        # dy_fee: uint256 = dy * self.fee / FEE_DENOMINATOR
        dy_fee_meta_normalized = dy_meta_normalized * meta_fee // FEE_DENOMINATOR
        dy_meta_after_fee_normalized = dy_meta_normalized - dy_fee_meta_normalized
        if dy_meta_after_fee_normalized < 0: dy_meta_after_fee_normalized = 0


        # Convert metapool output back to underlying units (either MIM or 3CRV)
        # dy = (dy - dy_fee) * PRECISION / rates[meta_j]
        if meta_rates[meta_j] == 0: meta_rates[meta_j] = 1
        dy_metapool_underlying = dy_meta_after_fee_normalized * PRECISION // meta_rates[meta_j]


        # --- Subcase 2a: Output is Metapool Coin (j == 0) ---
        if j == 0:
            amount_out_underlying_wei = dy_metapool_underlying # The output is already the Metapool coin

        # --- Subcase 2b: Output is Base Pool Coin (j > 0) ---
        else: # j > 0
             # dy_metapool_underlying is the amount of Base LP token (3CRV) to remove
             lp_token_to_remove = dy_metapool_underlying

             # Simulate remove_liquidity_one_coin on basepool
             amount_out_underlying_wei = simulate_remove_liquidity_one_coin(
                 pool_data=basepool_data,
                 token_amount=lp_token_to_remove,
                 i=base_j # Index of the target base coin
             )


    # --- Case 2: Both i and j are Base Pool Coins (i > 0 and j > 0) ---
    else:
        # Directly call exchange on the base pool
        amount_out_underlying_wei = simulate_exchange(
            pool_data=basepool_data,
            dx=dx_underlying_wei,
            i=base_i,
            j=base_j,
        )
        
    return amount_out_underlying_wei


