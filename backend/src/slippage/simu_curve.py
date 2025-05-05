import json
from slippage.type_pool.curve.stableswap import simulate_exchange, simulate_exchange_underlying
from slippage.type_pool.curve.cyptoswap import simulate_exchange_crypto, simulate_exchange_crypto_get_dy


def swap_curve(pool, amount_in, input_index, output_index):

    basepool = pool.get('basepool')
    
    if "crypto" in pool.get("registryId", ""):
      amount_in_wei = int(amount_in * (10**int(pool['coins'][input_index]['decimals'])))
      amount_output_wei = simulate_exchange_crypto_get_dy(
          pool,
          amount_in_wei,
          input_index,
          output_index,
      )

    elif basepool:
      amount_in_wei = int(amount_in * (10**int(pool['underlyingCoins'][input_index]['decimals'])))
      amount_output_wei = simulate_exchange_underlying(
          pool,
          basepool,
          amount_in_wei,
          input_index,
          output_index,
      )
    else:
      try:
        amount_in_wei = int(amount_in * (10**int(pool['coins'][input_index]['decimals'])))
      except:
        print(f"Warning: Failed to convert input amount to wei for {pool['id']}")
        amount_in_wei = int(amount_in * (10**int(pool['underlyingCoins'][input_index]['decimals'])))
      amount_output_wei = simulate_exchange(
          pool,
          amount_in_wei,
          input_index,
          output_index,
      )

    amount_out = amount_output_wei / (10**int(pool['coins'][output_index]['decimals']))
    # input_symbol = pool['coins'][input_index]['symbol']
    # output_symbol = pool['coins'][output_index]['symbol']
    # print(f"从 {input_symbol} 换到 {output_symbol}，换 {amount_in} 个，换到 {amount_out} 个")
    return amount_out

