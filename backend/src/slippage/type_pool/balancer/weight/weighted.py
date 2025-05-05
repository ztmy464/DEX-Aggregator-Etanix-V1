
import logging
from slippage.type_pool.balancer.math.maths import (
    mul_down_fixed,
    pow_down_fixed,
    div_up_fixed,
    div_down_fixed,
    pow_up_fixed,
    complement_fixed,
    mul_up_fixed,
)

WAD = int(1e18)

# Pool limits that arise from limitations in the fixed point power function (and the imposed 1:100 maximum weight
# ratio).

# Swap limits: amounts swapped may not be larger than this percentage of the total balance.
_MAX_IN_RATIO = int(0.3e18)
_MAX_OUT_RATIO = int(0.3e18)

# Invariant growth limit: non-proportional joins cannot cause the invariant to increase by more than this ratio.
_MAX_INVARIANT_RATIO = int(3e18)
# Invariant shrink limit: non-proportional exits cannot cause the invariant to decrease by less than this ratio.
_MIN_INVARIANT_RATIO = int(0.7e18)

# About swap fees on joins and exits:
# Any join or exit that is not perfectly balanced (e.g. all single token joins or exits) is mathematically
# equivalent to a perfectly balanced join or exit followed by a series of swaps. Since these swaps would charge
# swap fees, it follows that (some) joins and exits should as well.
# On these operations, we split the token amounts in 'taxable' and 'non-taxable' portions, where the 'taxable' part
# is the one to which swap fees are applied.

class Weighted:
    def __init__(self, pool_state):
        self.normalized_weights = pool_state["weights"]
    
    def on_swap(self, swap_params):
        amount_calculated_scaled18 = self.compute_out_given_exact_in(
            swap_params["balances_live_scaled18"][swap_params["index_in"]],
            self.normalized_weights[swap_params["index_in"]],
            swap_params["balances_live_scaled18"][swap_params["index_out"]],
            self.normalized_weights[swap_params["index_out"]],
            swap_params["amount_given_scaled18"],
            )
        return amount_calculated_scaled18


    def compute_out_given_exact_in(self,
        balance_in: int, weight_in: int, balance_out: int, weight_out: int, amount_in: int
    ) -> int:
        # **********************************************************************************************
        #  outGivenExactIn
        #  aO = amountOut
        #  bO = balanceOut
        #  bI = balanceIn              /      /            bI             \    (wI / wO) \
        #  aI = amountIn    aO = bO * |  1 - | --------------------------  | ^            |
        #  wI = weightIn               \      \       ( bI + aI )         /              /
        #  wO = weightOut
        # **********************************************************************************************

        if amount_in > mul_down_fixed(balance_in, _MAX_IN_RATIO):
            logging.info(f"Input exceeds 30% of balance_in! {amount_in} > {mul_down_fixed(balance_in, _MAX_IN_RATIO)}")
            # raise ValueError("Input exceeds 30% of balance_in!")

        denominator = balance_in + amount_in
        base = div_up_fixed(balance_in, denominator)
        exponent = div_down_fixed(weight_in, weight_out)
        power = pow_up_fixed(base, exponent)

        # Because of rounding up, power can be greater than one. Using complement prevents reverts.
        return mul_down_fixed(balance_out, complement_fixed(power))
