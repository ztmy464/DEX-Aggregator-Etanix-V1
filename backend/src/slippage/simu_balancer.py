from slippage.type_pool.balancer.stable.stable import Stable
from slippage.type_pool.balancer.weight.weighted import Weighted
from slippage.type_pool.balancer.gyro.gyroECLP import GyroECLP

pool_classes = {
        "WEIGHTED": Weighted,
        "STABLE": Stable,
        # "CONCENTRATED": Concentrated,
        # "CPMM": CPMM,
        # "GYRO": Gyro2CLP,
        "GYROE": GyroECLP,
}

from slippage.type_pool.balancer.math.maths import div_down_fixed, mul_down_fixed, mul_up_fixed

WAD = 10**18
RAY = 10**38  


# @ztmy
# WEIGHTED 
# STABLE    META_STABLE       COMPOSABLE_STABLE 
# GYROE     COW_AMM    ELEMENT   LIQUIDITY_BOOTSTRAPPING

def swap_blancer(pool, amount_in, input_index, output_index):

    # ---------------- reform pool ----------------
    pool_state,input_index, output_index = reform_pool_blancer(pool,input_index, output_index)
    amount_in = int(amount_in * WAD)

    # ---------------- calc amount_in ----------------
    amount_given_scaled18 = _compute_amount_given_scaled18(
        amount_in,
        input_index,
        output_index,
        pool_state["scalingFactors"],
        pool_state["tokenRates"],
    )

    # ---------------- swap_params ----------------
    swap_params = {
        "amount_given_scaled18": amount_given_scaled18,
        "balances_live_scaled18": pool_state["balancesLiveScaled18"][:],
        "index_in": input_index,
        "index_out": output_index,
    }

    # ---------------- subtract swap_fee ----------------
    swap_fee = pool_state["swapFee"]
    total_swap_fee_amount_scaled18 = 0
    # Round up to avoid losses during precision loss.
    total_swap_fee_amount_scaled18 = mul_up_fixed(
        amount_given_scaled18,
        swap_fee,
    )
    swap_params["amount_given_scaled18"] -= total_swap_fee_amount_scaled18

    # ---------------- on_swap ----------------
    pool_type = pool_state["type"]
    if pool_type not in pool_classes:
        raise SystemError("Unsupported Pool Type: ", pool_state["type"])

    pool_class = pool_classes[pool_type]
    compute_out = pool_class(pool_state).on_swap(swap_params)

    # QUEST: 为什么这里对结果影响这么大
    amount_out_raw = _to_raw_undo_rate_round_down(
        compute_out,
        pool_state["scalingFactors"][output_index],
        # If the swap is ExactIn, the amountCalculated is the amount of tokenOut. So, we want to use the rate
        # rounded up to calculate the amountCalculatedRaw, because scale down (undo rate) is a division, the
        # larger the rate, the smaller the amountCalculatedRaw. So, any rounding imprecision will stay in the
        # Vault and not be drained by the user.
        _compute_rate_round_up(pool_state["tokenRates"][output_index]),
    )

    amount_out = amount_out_raw/WAD

    return amount_out


def reform_pool_blancer(pool,input_index, output_index):

    if "STABLE" in pool["type"]:
        pool["type"] = "STABLE"

    pool = adjust_precision(pool)

    scaling_factors = []
    weights = []
    balancesLiveScaled18 = []
    token_rates = []
    bptindex = 1

    for i, token in enumerate(pool['poolTokens']):
        if float(token.get('balanceUSD', 0)) == 0 or float(token.get('balance', 0)) == 0:
            bptindex = i
            input_index = _skipBptIndex(bptindex,input_index);
            output_index = _skipBptIndex(bptindex,output_index);
            continue
        # scaling factor 
        scaling_factors.append(int(float(token["scalingFactor"])) if token["scalingFactor"] else 1)

        weights.append(int(float(token["weight"]) * WAD) if token["weight"] else 1)

        # balance × 1e18
        balancesLiveScaled18.append(int(float(token["balance"]) * WAD))

        # priceRate × 1e18
        token_rates.append(int(float(token["priceRate"]) * WAD))

    pool.pop('poolTokens')
    # 构建结果 JSON
    pool["scalingFactors"] = scaling_factors
    pool["weights"] = weights
    pool["balancesLiveScaled18"] = balancesLiveScaled18
    pool["tokenRates"] = token_rates

    return pool,input_index, output_index


def _compute_amount_given_scaled18(
    amount_given_raw: int,
    index_in: int,
    index_out: int,
    scaling_factors: list[int],
    token_rates: list[int],
) -> int:
    
    amount_given_scaled_18 = _to_scaled_18_apply_rate_round_down(
        amount_given_raw,
        scaling_factors[index_in],
        token_rates[index_in],
    )
    return amount_given_scaled_18


def _to_scaled_18_apply_rate_round_down(
    amount: int, scaling_factor: int, rate: int
) -> int:
    return mul_down_fixed(amount * scaling_factor, rate)

# /**
# * @notice Rounds up a rate informed by a rate provider.
# * @dev Rates calculated by an external rate provider have rounding errors. Intuitively, a rate provider
# * rounds the rate down so the pool math is executed with conservative amounts. However, when upscaling or
# * downscaling the amount out, the rate should be rounded up to make sure the amounts scaled are conservative.
# */
def _compute_rate_round_up(rate: int) -> int:
    # // If rate is divisible by FixedPoint.ONE, roundedRate and rate will be equal. It means that rate has 18 zeros,
    # // so there's no rounding issue and the rate should not be rounded up.
    rounded_rate = (rate / WAD) * WAD
    return rate if rounded_rate == rate else rate + 1


def _to_raw_undo_rate_round_down(
    amount: int,
    scaling_factor: int,
    token_rate: int,
) -> int:
    # // Do division last. Scaling factor is not a FP18, but a FP18 normalized by FP(1).
    # // `scalingFactor * tokenRate` is a precise FP18, so there is no rounding direction here.
    return div_down_fixed(
        amount,
        scaling_factor * token_rate,
    )


def adjust_precision(pool: dict) -> dict:

    high_precision_keys = {
        "tauAlphaX", "tauAlphaY", "tauBetaX", "tauBetaY",
        "u", "v", "w", "z", "dSq"
    }
    precision_keys = {
        "paramsAlpha", "paramsBeta", "paramsC", "paramsS", "paramsLambda"
    }
    pool["swapFee"] = int(float(pool["dynamicData"]["swapFee"]) * WAD)

    if pool["type"] == "GYROE":
        for key, value in pool.items():
            if key in high_precision_keys:
                pool[key] = int(float(value) * RAY)
            elif key in precision_keys:
                pool[key] = int(float(value) * WAD)
                
    if "amp" in pool and pool["amp"] is not None:
        pool["amp"] = int(float(pool["amp"]) * 1000)

    return pool


# for pools with in bgt token，bgt token has been excluded
#  ComposableStablePool Contract Source Code:
"""
function _onRegularSwap(
    bool isGivenIn,
    uint256 amountGiven,
    uint256[] memory registeredBalances,
    uint256 registeredIndexIn,
    uint256 registeredIndexOut
) private view returns (uint256) {
    // Adjust indices and balances for BPT token
    uint256[] memory balances = _dropBptItem(registeredBalances);
    uint256 indexIn = _skipBptIndex(registeredIndexIn);
    uint256 indexOut = _skipBptIndex(registeredIndexOut);

    (uint256 currentAmp, ) = _getAmplificationParameter();
    uint256 invariant = StableMath._calculateInvariant(currentAmp, balances);

    if (isGivenIn) {
        return StableMath._calcOutGivenIn(currentAmp, balances, indexIn, indexOut, amountGiven, invariant);
    } else {
        return StableMath._calcInGivenOut(currentAmp, balances, indexIn, indexOut, amountGiven, invariant);
    }
}
"""
def _skipBptIndex(bptindex,index): 
    return index if index < bptindex else index - 1
