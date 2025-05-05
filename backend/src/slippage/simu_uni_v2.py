from slippage.type_pool.uni_v2.v2swap import on_swap

def swap_uni_v2(pool, amount_in, input_index, output_index):
    # 0xd75ea151a61d06868e31f8988d28dfe5e9df57b4
    amount_out = on_swap(pool, amount_in, input_index, output_index)
    return amount_out


