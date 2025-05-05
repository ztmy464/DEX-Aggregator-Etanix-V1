import logging
from slippage.type_pool.uni_v3 import TickMath, SwapMath, FullMath, LiquidityMath
from slippage.type_pool.uni_v3 import SafeMath

# from src.slippage.type_pool.uni_v3 import TickMath, SwapMath, FullMath, LiquidityMath
# from src.slippage.type_pool.uni_v3 import SafeMath


# class TickMath:
#     MIN_TICK = -887272
#     MAX_TICK = 887272
#     MIN_SQRT_RATIO = 4295128739
#     MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342

class SwapCache:
    def __init__(self, feeProtocol, liquidityStart):
        self.feeProtocol = feeProtocol
        self.liquidityStart = liquidityStart

class SwapState:
    def __init__(self, amountSpecifiedRemaining, amountCalculated, sqrtPriceX96, tick, feeGrowthGlobalX128, protocolFee, liquidity, tickList=None):
        self.amountSpecifiedRemaining = amountSpecifiedRemaining
        self.amountCalculated = amountCalculated
        self.sqrtPriceX96 = sqrtPriceX96
        self.tick = tick
        self.feeGrowthGlobalX128 = feeGrowthGlobalX128
        self.protocolFee = protocolFee
        self.liquidity = liquidity
        self.tickList = tickList or []

class StepComputations:
    def __init__(self, sqrtPriceStartX96=0, tickNext=0, initialized=False, sqrtPriceNextX96=0, amountIn=0, amountOut=0, feeAmount=0):
        self.sqrtPriceStartX96 = sqrtPriceStartX96
        self.tickNext = tickNext
        self.initialized = initialized
        self.sqrtPriceNextX96 = sqrtPriceNextX96
        self.amountIn = amountIn
        self.amountOut = amountOut
        self.feeAmount = feeAmount

# Modified functions to handle ticks data structure
def nextTick(ticks_data, tick, lte):
    sorted_ticks = sorted(ticks_data, key=lambda x: int(x["tickIdx"]))
    tick_indices = [int(t["tickIdx"]) for t in sorted_ticks]
    
    if lte:
        valid_ticks = [t for t in tick_indices if t <= tick]
        if not valid_ticks:
            return TickMath.MIN_TICK, False
        next_tick = max(valid_ticks)
    else:
        valid_ticks = [t for t in tick_indices if t > tick]
        if not valid_ticks:
            return TickMath.MAX_TICK, False
        next_tick = min(valid_ticks)
    
    return next_tick, True

def cross(ticks_data, tick):
    # Find the tick in ticks_data
    for tick_info in ticks_data:
        if int(tick_info["tickIdx"]) == tick:
            # Return liquidityNet converted to int
            return int(tick_info["liquidityNet"])
    
    return 0  # Default if tick not found

def swap_amount_out(
    pool: dict,
    amount_in_wei: int,
    input_index: int,
    output_index: int,
) -> int:
    # Extract pool data
    ticks_data = pool["ticks"]
    # {'feeTier': '100', 'id': '0x202a6012894ae5c288ea824cbc8a9bfb26a49b93', 'liquidity': '2355189868088106516912', 'sqrtPrice': '76736736571163204734505063121', 'tick': '-640', 'token0': {'decimals': '18', 'id': '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2', 'symbol': 'WETH', 'priceUSD': 1830.1174484152646},
    # Set basic parameters
    zeroForOne = input_index == 0  # True if swapping token0 for token1
    amountSpecified = amount_in_wei  # Positive for exact input
    
    # Convert string values to integers where needed
    sqrtPriceX96 = int(pool["sqrtPrice"])
    # -48204
    tick = int(pool["tick"])
    liquidity = int(pool["liquidity"])
    if liquidity == 0:
        print(f"liquidity is 0, pool_id: {pool['id']}")
        return 0
    fee = int(pool["feeTier"])
    
    # Set price limits
    sqrtPriceLimitX96 = TickMath.MIN_SQRT_RATIO + 1 if zeroForOne else TickMath.MAX_SQRT_RATIO - 1
    
    # Initialize cache and state
    cache = SwapCache(0, liquidity)  # Simplified: feeProtocol set to 0
    
    exactInput = amountSpecified > 0
    
    state = SwapState(
        amountSpecified,
        0,
        sqrtPriceX96,
        tick,
        0,  # feeGrowthGlobalX128 - simplified
        0,  # protocolFee
        cache.liquidityStart,
        ticks_data
    )

    i = 0
    while state.amountSpecifiedRemaining != 0 and state.sqrtPriceX96 != sqrtPriceLimitX96:
        i = i+1
        step = StepComputations(0, 0, 0, 0, 0, 0, 0)
        step.sqrtPriceStartX96 = state.sqrtPriceX96
        
        #@ztmy Find next tick
        step.tickNext, step.initialized = nextTick(ticks_data, state.tick, zeroForOne)
        if not step.initialized:
            logging.info(f"current tick: {state.tick}, cross out of range, cross ticks: {i}")
            logging.info(f"num of ticks: {len(ticks_data)}")
            logging.info(f"pool: {pool}")
        
        step.sqrtPriceNextX96 = TickMath.getSqrtRatioAtTick(step.tickNext)
        
        if zeroForOne:
            sqrtRatioTargetX96 = (
                sqrtPriceLimitX96
                if step.sqrtPriceNextX96 < sqrtPriceLimitX96
                else step.sqrtPriceNextX96
            )
        else:
            sqrtRatioTargetX96 = (
                sqrtPriceLimitX96
                if step.sqrtPriceNextX96 > sqrtPriceLimitX96
                else step.sqrtPriceNextX96
            )    

        (
            state.sqrtPriceX96,
            step.amountIn,
            step.amountOut,
            step.feeAmount,
        ) = SwapMath.computeSwapStep(
            state.sqrtPriceX96,
            sqrtRatioTargetX96,
            state.liquidity,
            state.amountSpecifiedRemaining,
            fee,
        )
        
        if exactInput:
            state.amountSpecifiedRemaining -= step.amountIn + step.feeAmount
            state.amountCalculated = SafeMath.subInts(
                state.amountCalculated, step.amountOut
            )
        else:
            state.amountSpecifiedRemaining += step.amountOut
            state.amountCalculated = SafeMath.addInts(
                state.amountCalculated, step.amountIn + step.feeAmount
            )

        #@ztmy Handle tick crossing
        if state.sqrtPriceX96 == step.sqrtPriceNextX96:
            if step.initialized:
                liquidityNet = cross(
                    ticks_data,
                    step.tickNext,
                )
                
                if zeroForOne:
                    liquidityNet = -liquidityNet
                
                state.liquidity = LiquidityMath.addDelta(
                    state.liquidity, liquidityNet
                )

                #@ztmy Handle tick crossing when tick is not initialized
                # plan 1:
                # jump to the next tick which has liquidity
                # {have_liquidity}[no_liquidity]
                # |: current tick
                # \: move to tick

                # {_____|_____}[__________][__________]{/__________}
                # temp_tick = (step.tickNext - 1) if zeroForOne else step.tickNext
                # temp_tickNext, step.initialized = nextTick(ticks_data, temp_tick, zeroForOne)
                # state.tickNext = temp_tickNext

                # plan 2:
                # state.liquidity = 0

                # plan 3:
                # derectly fund next initialized tick at nextTick()
                # remove the tick which has no liquidity in ticks_data
            
            state.tick = (step.tickNext - 1) if zeroForOne else step.tickNext
        elif state.sqrtPriceX96 != step.sqrtPriceStartX96:
            state.tick = TickMath.getTickAtSqrtRatio(state.sqrtPriceX96)
    
    # print("cross ticks",i)
    amount0, amount1 = (
        (amountSpecified - state.amountSpecifiedRemaining, state.amountCalculated)
        if (zeroForOne == exactInput)
        else (
            state.amountCalculated,
            amountSpecified - state.amountSpecifiedRemaining,
        )
    )
    
    # Return the output amount
    return abs(amount1) if zeroForOne else abs(amount0)