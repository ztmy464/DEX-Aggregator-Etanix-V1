from src.slippage.type_pool.uni_v3 import TickMath, SwapMath

def on_swap_single_tick(
    pool: dict,
    amount_in_wei: int,
    input_index: int,
    output_index: int,
) -> int:
    # ---------------- data processing ----------------

    current_tick = int(pool['tick'])
    sqrtPriceCurrentX96 = int(pool['sqrtPrice'])
    liquidity = int(pool['liquidity'])
    fee = int(pool['feeTier'])
    # zeroForOne = True  Swapping token0 for token1
    zeroForOne = input_index < output_index
    tickSpacing = get_tick_spacing(fee)
 
    # ---------------------- Calc next tick ----------------------
    if zeroForOne:
        # If swapping token0 → token1, we go left (price decreases)
        tickNext = (current_tick // tickSpacing) * tickSpacing
        if tickNext == current_tick:
            tickNext -= tickSpacing
    else:
        # Swapping token1 → token0, price increases
        tickNext = (current_tick // tickSpacing) * tickSpacing + tickSpacing

    sqrtPriceNextTickX96 = TickMath.getSqrtRatioAtTick(tickNext)

    # ---------------------- Sanity check ----------------------
    if zeroForOne and not (sqrtPriceNextTickX96 < sqrtPriceCurrentX96):
        raise RuntimeError(
            f"Expected next tick price < current price, got {sqrtPriceNextTickX96} ≥ {sqrtPriceCurrentX96}"
        )
    if not zeroForOne and not (sqrtPriceNextTickX96 > sqrtPriceCurrentX96):
        raise RuntimeError(
            f"Expected next tick price > current price, got {sqrtPriceNextTickX96} ≤ {sqrtPriceCurrentX96}"
        )
        # Calculate the max amount possible within the current tick
    max_amount_in = calc_tick_remain(
        sqrtPriceCurrentX96,
        sqrtPriceNextTickX96,
        liquidity,
        fee,
        zeroForOne
    )
    if amount_in_wei > max_amount_in:
        print(f"Warning: Requested swap amount {amount_in_wei} exceeds the maximum possible within the current tick: {max_amount_in}")
        # Limit the amount to what can be swapped within the current tick
        amount_in_wei = max_amount_in

    # ----------------------  Compute Swap Step ----------------------
    (
        sqrtPriceFinalX96,
        amountIn_used, 
        amountOut_calculated,
        feeAmount_charged,    
    ) = SwapMath.computeSwapStep(
        sqrtPriceCurrentX96,   # Starting price
        sqrtPriceNextTickX96,  # Target price (the boundary)
        liquidity,             # Current liquidity
        amount_in_wei,            # Amount of token0 available for the swap
        fee,                   # Pool fee
    )

    # ---------------------- Check if tick crossed ----------------------

    if zeroForOne and sqrtPriceFinalX96 <= sqrtPriceNextTickX96:
        raise ValueError("Swap would cross tick to the left, not allowed in single-tick simulation")
    if not zeroForOne and sqrtPriceFinalX96 >= sqrtPriceNextTickX96:
        raise ValueError("Swap would cross tick to the right, not allowed in single-tick simulation")

    return abs(amountOut_calculated)


def calc_tick_remain(
    sqrtPriceCurrentX96: int,
    sqrtPriceNextTickX96: int,
    liquidity: int,
    fee: int,
    zeroForOne: bool
) -> int:
    """
    Calculate the maximum amount of tokens that can be swapped within the current tick.
    """
    if zeroForOne:
        # For token0 -> token1 (price decreases)
        # Formula: Δx = L * (1/√P_next - 1/√P_current)
        numerator1 = liquidity << 96
        numerator2 = sqrtPriceCurrentX96 - sqrtPriceNextTickX96
        
        # Calculate the token0 amount needed to move to the next tick boundary
        # This is the maximum amount before hitting the tick boundary
        max_amount_in = (
            (numerator1 * numerator2) // 
            (sqrtPriceNextTickX96 * sqrtPriceCurrentX96)
        )
    else:
        # For token1 -> token0 (price increases)
        # Formula: Δy = L * (√P_next - √P_current)
        max_amount_in = liquidity * (sqrtPriceNextTickX96 - sqrtPriceCurrentX96) // (1 << 96)
    
    # Consider the fee - adjust the maximum input amount
    # The fee is in hundredths of a bip (1/1000000)
    # We need to adjust the input amount to account for the fee
    max_amount_in_with_fee = (max_amount_in * 1_000_000) // (1_000_000 - fee)
    
    return max_amount_in_with_fee


def get_tick_spacing(fee: int) -> int:
    try:
        return {
        100: 1,      # 0.01% fee
        500: 10,     # 0.05% fee
        3000: 60,    # 0.30% fee
        10000: 200   # 1.00% fee
        }[fee]
    except KeyError:
        raise ValueError(f"Invalid fee tier: {fee}")