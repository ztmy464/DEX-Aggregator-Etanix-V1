from slippage.type_pool.uni_v3.v3swap import swap_amount_out

def swap_uni_v3(pool, amount_in, input_index, output_index):
    amount_in_wei = int(amount_in * (10**int(pool[f"token{input_index}"]['decimals'])))
    amount_out_wei = swap_amount_out(pool, amount_in_wei, input_index, output_index)
    amount_out = amount_out_wei / (10**int(pool[f"token{output_index}"]['decimals']))
    return amount_out


