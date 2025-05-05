def on_swap(pool: dict, amount_in: int, input_index: int, output_index: int) -> dict:
    """
    Simulate a swap on Uniswap V2 and return the amount out and price impact.
    """
    FEE_RATE = 0.003  # 0.3% Uniswap fee

    # handle reserve is not wei 0xd75ea151a61d06868e31f8988d28dfe5e9df57b4
    if pool['token0']['decimals'] == "0": 
        print("the token symbol of this pool is empty",pool['id'])
        pool['reserve0'] = int(pool['reserve0']) / 10 ** 18
    elif pool['token1']['decimals'] == "0":
        print("the token symbol of this pool is empty",pool['id'])
        pool['reserve1'] = int(pool['reserve1']) / 10 ** 18
            
    # Reserves before swap
    x = float(pool[f'reserve{input_index}'])  # input reserve
    y = float(pool[f'reserve{output_index}'])  # output reserve

    # Apply fee
    amount_in_with_fee = amount_in * (1 - FEE_RATE)

    # Calculate output amount using Uniswap V2 formula
    numerator = amount_in_with_fee * y
    denominator = x + amount_in_with_fee
    amount_out = numerator / denominator if denominator > 0 else 0

    # Calculate spot price before swap
    spot_price_before = y / x if x > 0 else float('inf')
    # Effective price paid
    effective_price = amount_in / amount_out if amount_out > 0 else float('inf')
    # Price impact
    price_impact = (effective_price / spot_price_before - 1) * 100 if spot_price_before > 0 else float('inf')

    return amount_out
