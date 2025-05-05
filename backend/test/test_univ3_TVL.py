import decimal
import math

"""
calc TVL, amount0 and amount1 from liquidity and current sqrtPriceX96
"""
# --- Math Helpers ---
# Set high precision for Decimal calculations where needed (outside mulDiv)
decimal.getcontext().prec = 78 # Uniswap uses up to 78 decimal places internally sometimes

Q96 = 2**96
Q192 = 2**192

def mulDiv(a: int, b: int, denominator: int) -> int:

    # Using simple integer math which is sufficient if intermediate product doesn't overflow 512 bits
    # Python integers handle arbitrary size, so overflow isn't an issue like in Solidity
    if denominator == 0:
        raise ValueError("Denominator cannot be zero")
    return (a * b) // denominator # // performs floor division

def get_sqrt_ratio_at_tick(tick: int) -> int:

    if tick < -887272 or tick > 887272:
        raise ValueError("Tick out of range")

    # Using Decimal for intermediate calculation - needs very high precision
    # A direct port of TickMath.sol logic using integer math is preferred for exactness
    try:
        price_ratio = decimal.Decimal(1.0001)**decimal.Decimal(tick)
        sqrt_ratio = price_ratio.sqrt()
        sqrt_ratio_x96 = int(sqrt_ratio * decimal.Decimal(Q96))
        # Clamp to uint160 bounds if necessary (though result should fit)
        # MAX_UINT160 = (1 << 160) - 1
        # MIN_UINT160 = 0 # Not really a min, but for range check
        # if sqrt_ratio_x96 > MAX_UINT160: # Should not happen for valid ticks
        #     sqrt_ratio_x96 = MAX_UINT160
        return sqrt_ratio_x96
    except Exception as e:
        print(f"Error calculating sqrt ratio for tick {tick}: {e}")
        # Fallback or re-raise depending on desired robustness
        # Using math.pow for a potentially faster but potentially less precise float version:
        # return int(math.pow(1.0001, tick / 2) * Q96)
        raise # Re-raise the error as precision is critical

# --- Solidity Logic Implementation ---

def get_amount0_for_liquidity_sol(
    sqrtRatioAX96: int,
    sqrtRatioBX96: int,
    liquidity: int
) -> int:
    """
    Python implementation of Solidity's getAmount0ForLiquidity.
    Calculates amount0 for liquidity L in range [A, B] if price > B.
    """
    if sqrtRatioAX96 > sqrtRatioBX96:
        sqrtRatioAX96, sqrtRatioBX96 = sqrtRatioBX96, sqrtRatioAX96

    if sqrtRatioAX96 <= 0:
         raise ValueError("sqrtRatioAX96 must be > 0")

    # Replicating:
    # return FullMath.mulDiv( uint256(liquidity) << 96, sqrtRatioBX96 - sqrtRatioAX96, sqrtRatioBX96) / sqrtRatioAX96;
    # Note: Solidity uses uint256 for intermediate liquidity calculation
    liquidity_u256 = liquidity # Python ints are arbitrary precision

    intermediate_numerator = liquidity_u256 << 96 # liquidity * Q96
    intermediate_diff = sqrtRatioBX96 - sqrtRatioAX96

    # Perform the first mulDiv
    intermediate_result = mulDiv(intermediate_numerator, intermediate_diff, sqrtRatioBX96)

    # Perform the final division (floor division implied by integer types)
    amount0 = intermediate_result // sqrtRatioAX96
    return amount0

def get_amount1_for_liquidity_sol(
    sqrtRatioAX96: int,
    sqrtRatioBX96: int,
    liquidity: int
) -> int:
    """
    Python implementation of Solidity's getAmount1ForLiquidity.
    Calculates amount1 for liquidity L in range [A, B] if price < A.
    """
    if sqrtRatioAX96 > sqrtRatioBX96:
        sqrtRatioAX96, sqrtRatioBX96 = sqrtRatioBX96, sqrtRatioAX96

    # Replicating:
    # return FullMath.mulDiv(liquidity, sqrtRatioBX96 - sqrtRatioAX96, FixedPoint96.Q96);
    intermediate_diff = sqrtRatioBX96 - sqrtRatioAX96
    amount1 = mulDiv(liquidity, intermediate_diff, Q96)
    return amount1


# --- Revised Calculation Function ---

def calculate_amounts_adjusted_from_tick_range(
    current_sqrtPriceX96: int,
    current_tick: int,
    tickSpacing: int,
    current_liquidity: int,
    token0_decimals: int,
    token1_decimals: int
) -> dict:

    if current_liquidity < 0:
        # Liquidity cannot be negative, but handle defensively
         return {'error': "Liquidity cannot be negative"}
    if current_liquidity == 0:
        # If there's no liquidity, amounts are zero
        return {
            'amount0_adj': decimal.Decimal(0),
            'amount1_adj': decimal.Decimal(0),
            'amount0_raw': 0,
            'amount1_raw': 0
        }

    try:
        # 1. Determine tick boundaries
        tickLower = (current_tick // tickSpacing) * tickSpacing
        tickUpper = tickLower + tickSpacing

        # 2. Get sqrtPriceX96 for boundaries
        #    WARNING: Requires a *precise* implementation of get_sqrt_ratio_at_tick!
        sqrtRatioLowerX96 = get_sqrt_ratio_at_tick(tickLower)
        sqrtRatioUpperX96 = get_sqrt_ratio_at_tick(tickUpper)

        # --- Core Calculation using Solidity Logic ---

        # Calculate amount0 (Token0 is active between current price and upper boundary)
        # Uses getAmount0ForLiquidity logic with current and upper bounds
        # amount0 = getAmount0ForLiquidity(current, upper, L)
        amount0_raw = get_amount0_for_liquidity_sol(
            current_sqrtPriceX96,
            sqrtRatioUpperX96,
            current_liquidity
        )

        # Calculate amount1 (Token1 is active between lower boundary and current price)
        # Uses getAmount1ForLiquidity logic with lower and current bounds
        # amount1 = getAmount1ForLiquidity(lower, current, L)
        amount1_raw = get_amount1_for_liquidity_sol(
            sqrtRatioLowerX96,
            current_sqrtPriceX96,
            current_liquidity
        )

        # --- Adjust for Decimals ---
        amount0_adj = decimal.Decimal(amount0_raw) / (decimal.Decimal(10)**token0_decimals)
        amount1_adj = decimal.Decimal(amount1_raw) / (decimal.Decimal(10)**token1_decimals)

        return {
            'amount0_adj': amount0_adj,
            'amount1_adj': amount1_adj,
            'amount0_raw': amount0_raw, # Also return raw amounts
            'amount1_raw': amount1_raw
        }

    except Exception as e:
        print(f"Error during amount calculation: {e}")
        # Handle potential errors from tick math or mulDiv
        return {'error': str(e)}


# --- Example Usage ---

# Use your previous inputs, but add tick and tickSpacing
example_current_sqrtPriceX96 = 2407016832346560937328687142454 # From your previous example
example_current_liquidity = 1364837034339          # From your previous example

example_token0_decimals = 8 # USDC
example_token1_decimals = 6 # WETH

example_token0_price_usd = 1   # USDC 
example_token1_price_usd = 1622 # WETH 

# !!! You NEED to provide the ACTUAL current tick and tickSpacing for the pool !!!
# These are JUST PLACEHOLDERS - REPLACE THEM
example_current_tick =  68279 # Example tick, MUST correspond to the sqrtPriceX96 above!
example_tickSpacing = 60      # Example tick spacing (e.g., for WETH/USDC 0.05% pool)

# --- Replace the simple calculation lines with a call to the new function ---
print("Calculating using new function based on Solidity logic...")

# --- Run the calculation ---
# WARNING: Result depends heavily on the accuracy of get_sqrt_ratio_at_tick
#          and correctness of example_current_tick / example_tickSpacing

if __name__ == '__main__':
    try:
        calculated_amounts = calculate_amounts_adjusted_from_tick_range(
            example_current_sqrtPriceX96,
            example_current_tick,
            example_tickSpacing,
            example_current_liquidity,
            example_token0_decimals,
            example_token1_decimals
        )

        if 'error' in calculated_amounts:
            print(f"Calculation failed: {calculated_amounts['error']}")
        else:
            amount0_adj_new = calculated_amounts['amount0_adj']
            amount1_adj_new = calculated_amounts['amount1_adj']
            print(f"  New Amount 0: {amount0_adj_new}")
            print(f"  New Amount 1: {amount1_adj_new}")

            # You would then use these new adjusted amounts to calculate TVL
            tvl_usd_new = (amount0_adj_new * decimal.Decimal(example_token0_price_usd)) + \
                          (amount1_adj_new * decimal.Decimal(example_token1_price_usd))
            print(f"  New Estimated TVL (USD): {tvl_usd_new:.2f}")

    except Exception as e:
        # Catch any unexpected error during the call or printing
        print(f"An unexpected error occurred: {e}")

    print("\n--- Comparison Calculation using OLD Simple Method ---")
    # Recalculate using the OLD simple method for comparison
    try:
        sqrtP_old = decimal.Decimal(example_current_sqrtPriceX96) / decimal.Decimal(Q96)
        if sqrtP_old > 0:
            amount0_old_raw = decimal.Decimal(example_current_liquidity) / sqrtP_old
        else:
            amount0_old_raw = decimal.Decimal(0)
        amount1_old_raw = decimal.Decimal(example_current_liquidity) * sqrtP_old

        amount0_old_adj = amount0_old_raw / (decimal.Decimal(10)**example_token0_decimals)
        amount1_old_adj = amount1_old_raw / (decimal.Decimal(10)**example_token1_decimals)
        print(f"  Old Amount 0: {amount0_old_adj}")
        print(f"  Old Amount 1: {amount1_old_adj}")
        TVL = amount0_old_adj * decimal.Decimal(example_token0_price_usd) + amount1_old_adj * decimal.Decimal(example_token1_price_usd)
        print(f"  Old Estimated TVL (USD): {TVL:.2f}")
    except Exception as e:
        print(f"Error during old calculation: {e}")



"""
usdc  1 weth  1622
fee 500: tick spacing 10:
Calculating using new function based on Solidity logic...
  New Amount 0: 60270.280416
  New Amount 1: 9.668465757008706829
  New Estimated TVL (USD): 75952.53

--- Comparison Calculation using OLD Simple Method ---
  Old Amount 0: 151951095.900162017284296246474238406901946075139686058779296734364723355306979
  Old Amount 1: 93642.793029784049876637280605184738202404763495459571807968812074072167562903
  Old Estimated TVL (USD): 303839706.19

fee 3000: tick spacing 60:
Calculating using new function based on Solidity logic...
  New Amount 0: 266412.426566
  New Amount 1: 67.237247597285743736
  New Estimated TVL (USD): 375471.24

fee 100: tick spacing 1:
--- Comparison Calculation using OLD Simple Method ---
  Old Amount 0: 125305553.092433435800245481305077745658032886945752610671491475591859797983226
  Old Amount 1: 77186.1840909381907965366815259975946827941850872506428634544308608994133812792
  Old Estimated TVL (USD): 250501543.69

Calculating using new function based on Solidity logic...
  New Amount 0: 2204634.656786
  New Amount 1: 2802188.738681
  New Estimated TVL (USD): 5006823.40

--- Comparison Calculation using OLD Simple Method ---
  Old Amount 0: 100122798165.63596329204102251311275198142754031113462264140175651648183905844
  Old Amount 1: 100158442307.948681353135096473682403819329975949865966982027745249729392199023
  Old Estimated TVL (USD): 200281240473.58
"""

