# @version ^0.3.7
# (c) Curve.Fi, 2023
# SafeMath Implementation of AMM Math for 3-coin Curve Cryptoswap Pools
#
# Unless otherwise agreed on, only contracts owned by Curve DAO or
# Swiss Stake GmbH are allowed to call this contract.

"""
@title CurveTricryptoMathOptimized
@license MIT
@author Curve.Fi
@notice Curve AMM Math for 3 unpegged assets (e.g. ETH, BTC, USD).
"""
from math import isqrt

N_COINS: int = 3
A_MULTIPLIER: int = 10000
MIN_GAMMA: int = 10**10
MAX_GAMMA: int = 5 * 10**16

MIN_A: int = N_COINS**N_COINS * A_MULTIPLIER / 100
MAX_A: int = N_COINS**N_COINS * A_MULTIPLIER * 1000

version = "v2.0.0"


# ------------------------ AMM math functions --------------------------------



def get_y(
    _ANN: int, _gamma: int, x: list[int], _D: int, i: int
) -> tuple[int, int]:
    """
    @notice Calculate x[i] given other balances x[0..N_COINS-1] and invariant D.
    @dev ANN = A * N**N . AMM contract's A is actuall ANN.
    @param _ANN AMM.A() value.
    @param _gamma AMM.gamma() value.
    @param x Balances multiplied by prices and precisions of all coins.
    @param _D Invariant.
    @param i Index of coin to calculate y.
    """

    # Safety checks
    assert _ANN > MIN_A - 1 and _ANN < MAX_A + 1, "dev: unsafe values A"
    assert _gamma > MIN_GAMMA - 1 and _gamma < MAX_GAMMA + 1, "dev: unsafe values gamma"
    assert _D > 10**17 - 1 and _D < 10**15 * 10**18 + 1, "dev: unsafe values D"

    for k in range(3):
        if k != i:
            frac: int = x[k] * 10**18 / _D
            assert frac > 10**16 - 1 and frac < 10**20 + 1, "dev: unsafe values x[i]"

    j: int = 0
    k: int = 0
    if i == 0:
        j = 1
        k = 2
    elif i == 1:
        j = 0
        k = 2
    elif i == 2:
        j = 0
        k = 1

    ANN: int = int(_ANN)
    gamma: int = int(_gamma)
    D: int = int(_D)
    x_j: int = int(x[j])
    x_k: int = int(x[k])

    a: int = 10**36 / 27
    b: int = 10**36/9 + 2*10**18*gamma/27 - D**2/x_j*gamma**2*ANN/27**2/int(A_MULTIPLIER)/x_k
    c: int = 10**36/9 + gamma*(gamma + 4*10**18)/27 + gamma**2*(x_j+x_k-D)/D*ANN/27/int(A_MULTIPLIER)
    d: int = (10**18 + gamma)**2/27
    d0: int = abs(3*a*c/b - b)

    divider: int = 0
    if d0 > 10**48:
        divider = 10**30
    elif d0 > 10**44:
        divider = 10**26
    elif d0 > 10**40:
        divider = 10**22
    elif d0 > 10**36:
        divider = 10**18
    elif d0 > 10**32:
        divider = 10**14
    elif d0 > 10**28:
        divider = 10**10
    elif d0 > 10**24:
        divider = 10**6
    elif d0 > 10**20:
        divider = 10**2
    else:
        divider = 1

    additional_prec: int = 0
    if abs(a) > abs(b):
        additional_prec = abs(a) / abs(b)
        a = a * additional_prec / divider
        b = b * additional_prec / divider
        c = c * additional_prec / divider
        d = d * additional_prec / divider
    else:
        additional_prec = abs(b) / abs(a)
        a = a / additional_prec / divider
        b = b / additional_prec / divider
        c = c / additional_prec / divider
        d = d / additional_prec / divider

    delta0: int = 3*a*c/b - b
    delta1: int = 9*a*c/b - 2*b - 27*a**2/b*d/b

    sqrt_arg: int = delta1**2 + 4*delta0**2/b*delta0
    sqrt_val: int = 0
    if sqrt_arg > 0:
        sqrt_val = int(isqrt(int(sqrt_arg)))
    else:
        return [_newton_y(_ANN, _gamma, x, _D, i), 0]

    b_cbrt: int = 0
    if b >= 0:
        b_cbrt = int(_cbrt(int(b)))
    else:
        b_cbrt = -int(_cbrt(int(-b)))

    second_cbrt: int = 0
    if delta1 > 0:
        second_cbrt = int(_cbrt(int((delta1 + sqrt_val)/2)))
    else:
        second_cbrt = -int(_cbrt(int(-(delta1 - sqrt_val)/2)))

    C1: int = b_cbrt*b_cbrt/10**18*second_cbrt/10**18

    root_K0: int = (b + b*delta0/C1 - C1)/3
    root: int = int(D*D/27/x_k*D/x_j*root_K0/a)

    return [
        root,
        int(10**18*root_K0/a)
    ]


def _newton_y(
    ANN: int, gamma: int, x: list[int], D: int, i: int
) -> int:

    # Calculate x[i] given A, gamma, xp and D using newton's method.
    # This is the original method; get_y replaces it, but defaults to
    # this version conditionally.

    # Safety checks
    assert ANN > MIN_A - 1 and ANN < MAX_A + 1, "dev: unsafe values A"
    assert gamma > MIN_GAMMA - 1 and gamma < MAX_GAMMA + 1, "dev: unsafe values gamma"
    assert D > 10**17 - 1 and D < 10**15 * 10**18 + 1, "dev: unsafe values D"

    for k in range(3):
        if k != i:
            frac: int = x[k] * 10**18 / D
            assert frac > 10**16 - 1 and frac < 10**20 + 1, "dev: unsafe values x[i]"

    y: int = D / N_COINS
    K0_i: int = 10**18
    S_i: int = 0

    x_sorted: int[N_COINS] = x
    x_sorted[i] = 0
    x_sorted = _sort(x_sorted)  # From high to low

    convergence_limit: int = max(max(x_sorted[0] / 10**14, D / 10**14), 100)
    for j in range(2, N_COINS + 1):
        _x: int = x_sorted[N_COINS - j]
        y = y * D / (_x * N_COINS)  # Small _x first
        S_i += _x
    for j in range(N_COINS - 1):
        K0_i = K0_i * x_sorted[j] * N_COINS / D  # Large _x first

    # initialise variables:
    diff: int = 0
    y_prev: int = 0
    K0: int = 0
    S: int = 0
    _g1k0: int = 0
    mul1: int = 0
    mul2: int = 0
    yfprime: int = 0
    _dyfprime: int = 0
    fprime: int = 0
    y_minus: int = 0
    y_plus: int = 0

    for j in range(255):

        y_prev = y

        K0 = K0_i * y * N_COINS / D
        S = S_i + y

        _g1k0 = gamma + 10**18
        if _g1k0 > K0:
            _g1k0 = _g1k0 - K0 + 1
        else:
            _g1k0 = K0 - _g1k0 + 1

        mul1 = 10**18 * D / gamma * _g1k0 / gamma * _g1k0 * A_MULTIPLIER / ANN

        # 2*K0 / _g1k0
        mul2 = 10**18 + (2 * 10**18) * K0 / _g1k0

        yfprime = 10**18 * y + S * mul2 + mul1
        _dyfprime = D * mul2
        if yfprime < _dyfprime:
            y = y_prev / 2
            continue
        else:
            yfprime -= _dyfprime

        fprime = yfprime / y

        # y -= f / f_prime;  y = (y * fprime - f) / fprime
        y_minus = mul1 / fprime
        y_plus = (
            yfprime + 10**18 * D
        ) / fprime + y_minus * 10**18 / K0
        y_minus += 10**18 * S / fprime

        if y_plus < y_minus:
            y = y_prev / 2
        else:
            y = y_plus - y_minus

        if y > y_prev:
            diff = y - y_prev
        else:
            diff = y_prev - y

        if diff < max(convergence_limit, y / 10**14):
            frac: int = y * 10**18 / D
            assert (frac > 10**16 - 1) and (frac < 10**20 + 1), "dev: unsafe value for y"
            return y

    raise "Did not converge"


# --------------------------- Math Utils -------------------------------------
def _sort(unsorted_x: list[int]) -> list[int]:

    # Sorts a three-array number in a descending order:

    x: int[N_COINS] = unsorted_x
    temp_var: int = x[0]
    if x[0] < x[1]:
        x[0] = x[1]
        x[1] = temp_var
    if x[0] < x[2]:
        temp_var = x[0]
        x[0] = x[2]
        x[2] = temp_var
    if x[1] < x[2]:
        temp_var = x[1]
        x[1] = x[2]
        x[2] = temp_var

    return x


def cbrt(x: int) -> int:
    """
    @notice Calculate the cubic root of a number in 1e18 precision
    @dev Consumes around 1500 gas units
    @param x The number to calculate the cubic root of
    """
    return _cbrt(x)



def _log2(x: int) -> int:

    # Compute the binary logarithm of `x`

    # This was inspired from Stanford's 'Bit Twiddling Hacks' by Sean Eron Anderson:
    # https://graphics.stanford.edu/~seander/bithacks.html#IntegerLog
    #
    # More inspiration was derived from:
    # https://github.com/transmissions11/solmate/blob/main/src/utils/SignedWadMath.sol

    log2x: int = 0
    if x > 340282366920938463463374607431768211455:
        log2x = 128
    if unsafe_div(x, shift(2, log2x)) > 18446744073709551615:
        log2x = log2x | 64
    if unsafe_div(x, shift(2, log2x)) > 4294967295:
        log2x = log2x | 32
    if unsafe_div(x, shift(2, log2x)) > 65535:
        log2x = log2x | 16
    if unsafe_div(x, shift(2, log2x)) > 255:
        log2x = log2x | 8
    if unsafe_div(x, shift(2, log2x)) > 15:
        log2x = log2x | 4
    if unsafe_div(x, shift(2, log2x)) > 3:
        log2x = log2x | 2
    if unsafe_div(x, shift(2, log2x)) > 1:
        log2x = log2x | 1

    return log2x

def unsafe_div(x: int, y: int) -> int:
    return x // y

def unsafe_mul(x: int, y: int) -> int:
    return x * y

def unsafe_add(x: int, y: int) -> int:
    return x + y

def pow_mod256(x: int, y: int) -> int:
    return x ** y

def shift(a: int, b: int) -> int:
    return a << b if b >= 0 else a >> -b

def _cbrt(x: int) -> int:

    xx: int = 0
    if x >= 115792089237316195423570985008687907853269 * 10**18:
        xx = x
    elif x >= 115792089237316195423570985008687907853269:
        xx = unsafe_mul(x, 10**18)
    else:
        xx = unsafe_mul(x, 10**36)

    log2x: int = _log2(xx)

    # When we divide log2x by 3, the remainder is (log2x % 3).
    # So if we just multiply 2**(log2x/3) and discard the remainder to calculate our
    # guess, the newton method will need more iterations to converge to a solution,
    # since it is missing that precision. It's a few more calculations now to do less
    # calculations later:
    # pow = log2(x) // 3
    # remainder = log2(x) % 3
    # initial_guess = 2 ** pow * cbrt(2) ** remainder
    # substituting -> 2 = 1.26 ≈ 1260 / 1000, we get:
    #
    # initial_guess = 2 ** pow * 1260 ** remainder // 1000 ** remainder

    remainder: int = int(log2x) % 3
    a: int = unsafe_div(
        unsafe_mul(
            pow_mod256(2, unsafe_div(int(log2x), 3)),  # <- pow
            pow_mod256(1260, remainder),
        ),
        pow_mod256(1000, remainder),
    )

    # Because we chose good initial values for cube roots, 7 newton raphson iterations
    # are just about sufficient. 6 iterations would result in non-convergences, and 8
    # would be one too many iterations. Without initial values, the iteration count
    # can go up to 20 or greater. The iterations are unrolled. This reduces gas costs
    # but takes up more bytecode:
    a = unsafe_div(unsafe_add(unsafe_mul(2, a), unsafe_div(xx, unsafe_mul(a, a))), 3)
    a = unsafe_div(unsafe_add(unsafe_mul(2, a), unsafe_div(xx, unsafe_mul(a, a))), 3)
    a = unsafe_div(unsafe_add(unsafe_mul(2, a), unsafe_div(xx, unsafe_mul(a, a))), 3)
    a = unsafe_div(unsafe_add(unsafe_mul(2, a), unsafe_div(xx, unsafe_mul(a, a))), 3)
    a = unsafe_div(unsafe_add(unsafe_mul(2, a), unsafe_div(xx, unsafe_mul(a, a))), 3)
    a = unsafe_div(unsafe_add(unsafe_mul(2, a), unsafe_div(xx, unsafe_mul(a, a))), 3)
    a = unsafe_div(unsafe_add(unsafe_mul(2, a), unsafe_div(xx, unsafe_mul(a, a))), 3)

    if x >= 115792089237316195423570985008687907853269 * 10**18:
        return a * 10**12
    elif x >= 115792089237316195423570985008687907853269:
        return a * 10**6

    return a
