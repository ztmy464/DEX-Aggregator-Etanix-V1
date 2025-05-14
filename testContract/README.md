## DeFi Swap Protocol Test Suite

This repository contains Foundry tests for swap functionalities across various DeFi protocols.

## Usage

### Build

```shell
$ forge build
```

### Test

```shell
$ forge test --match-path test/aggregator/UniV3Swap_weth_wbtc.t.sol --fork-url $FORK_URL -vvv

$ forge test --match-path test/aggregator/UniV2_swap.t.sol --fork-url $FORK_URL -vvv
$ forge test --match-path test/aggregator/UniV3_swap.t.sol --fork-url $FORK_URL -vvv

$ forge test --match-path test/aggregator/Balancer_ECLP_swap.t.sol --fork-url $FORK_URL -vvv
$ forge test --match-path test/aggregator/Balancer_stable_swap.t.sol --fork-url $FORK_URL -vvv
$ forge test --match-path test/aggregator/Balancer_weighted_swap.t.sol --fork-url $FORK_URL -vvv

$ forge test --match-path test/aggregator/CurveV1_stable_swap.t.sol --fork-url $FORK_URL -vvv
$ forge test --match-path test/aggregator/CurveV2_crypto_swap.t.sol --fork-url $FORK_URL -vvv
```

##  Swap Test List:

### 1. `UniV3Swap_weth_wbtc.t.sol`

* **Protocol:** Uniswap V3 (for WETH/WBTC pair)
* **Pool Characteristics:** Uniswap V3's concentrated liquidity model applied to a specific WETH/WBTC pool with a chosen fee tier.
* **Test Swap Function Call:**
    * Router: `ISwapRouter.exactInputSingle(...)`
    * Direct Pool: `IUniswapV3Pool.swap(...)` (requiring a callback for WETH/WBTC)

---

### 2. `UniV2_swap.t.sol`

* **Protocol:** Uniswap V2
* **Pool Characteristics:** Employs a constant product formula (`x*y=k`) for pairs of two ERC20 tokens.
* **Test Swap Function Call:** `IUniswapV2Router02.swapExactTokensForTokens(...)` (or similar router functions)

---

### 3. `UniV3_swap.t.sol`

* **Protocol:** Uniswap V3
* **Pool Characteristics:** Features concentrated liquidity within specific price ranges (ticks) for enhanced capital efficiency.
* **Test Swap Function Call:**
    * Router: `ISwapRouter.exactInputSingle(...)` or `ISwapRouter.exactInput(...)`
    * Direct Pool: `IUniswapV3Pool.swap(...)` (requiring a callback implementation)

---

### 4. `Balancer_ECLP_swap.t.sol`

* **Protocol:** Balancer (Elastic Concentrated Liquidity Pools - ECLP)
* **Pool Characteristics:** Offers concentrated liquidity similar to Uniswap V3 for higher capital efficiency; may feature dynamic fees.
* **Test Swap Function Call:** `IVault.swap(...)`

---

### 5. `Balancer_stable_swap.t.sol`

* **Protocol:** Balancer (Stable Pools)
* **Pool Characteristics:** Optimized for low-slippage swaps between similarly priced assets (e.g., stablecoins) using StableMath.
* **Test Swap Function Call:** `IVault.swap(...)`

---

### 6. `Balancer_weighted_swap.t.sol`

* **Protocol:** Balancer (Weighted Pools)
* **Pool Characteristics:** Supports multiple tokens with custom, fixed weights, using a weighted geometric mean price formula.
* **Test Swap Function Call:** `IVault.swap(...)`

---

### 7. `CurveV1_stable_swap.t.sol`

* **Protocol:** Curve Finance (V1 StableSwap)
* **Pool Characteristics:** Designed for extremely low slippage between pegged assets (e.g., stablecoins) using the StableSwap invariant.
* **Test Swap Function Call:** `ICurvePool.exchange(...)` `ICurvePool.get_dy(...)` or `ICurvePool.exchange_underlying(...)` `ICurvePool.get_dy_underlying(...)`

---

### 8. `CurveV2_crypto_swap.t.sol`

* **Protocol:** Curve Finance (V2 Crypto Pools)
* **Pool Characteristics:** Efficiently trades non-pegged, volatile assets using concentrated liquidity around an internal oracle price.
* **Test Swap Function Call:** `ICurveCryptoPool.exchange(...)` or `ICurvePool.get_dy(...)`

---



