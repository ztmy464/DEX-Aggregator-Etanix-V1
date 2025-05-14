# process

1. **获取结构化链上数据**
   - **DEX Subgraphs** ：
     - Graph 节点监听链上事件，查询索引好的、结构化的、历史/聚合数据
   - **Multicall**
     - 智能合约模式, 依赖 RPC 节点，读取实时链上状态，不能获取历史数据


2. **construct the graph**
   - **获取报价(转换数据)**
     - `viem` 
     - DEX SDKs :
       - [uniswap sdk](https://docs.uniswap.org/sdk/core/overview)


3. **Smart order routing (SOR)**
   - 参考：
     - `Deeplink Labs: Eta X V1`
     - `DODO Research`
   - **难点**：
     - 订单拆分
     - 多跳路由（需考虑 Gas 优化、Slippage）
     
     - Maximum return
     - Lowest gas cost return

   - 

4. **模拟交易**

----

# progress bar  

Obtain on-chain data？ → The Graph notes  
↓  
Which data should be obtained？##  
↓  
Optimal path discovery?  → materials #   
|  
How to construct the graph (vertex & edges)？  
|  
How to traversing the graph (pathfinding algorithms)?  
DFS、Floyd-Warshall &  Bellman-Ford、heuristic

|
重构 pool_collector : 在curve和balancer的结果中加入查询的原始池子信息和basepool的池子信息
重构 path_crawler : 将计算amount_out 的逻辑重新整理，并封装到simulateswap.py中，不计算price_impact(因为usd价格不准确)
使calculate_routes函数成功执行并输出可行的routes结果

---

## Which data should be obtained？

swap A to B :

1.  **Discover Relevant Pools:** Find the Uniswap V3 liquidity pools that facilitate swaps between the two tokens the user wants to trade. Remember Uniswap V3 has multiple pools for the same pair, differing by fee tier (e.g., 0.05%, 0.3%, 1%).
2.  **Get Current Pool State for Pricing:** For each relevant pool, fetch the necessary real-time (or near real-time) data to calculate the current exchange rate, estimate the output amount, and determine price impact/slippage.


**I. Essential Data Needed:**

1.  **Pools (`Pool` Entity):** 
    * `id`: The contract address of the pool (essential for identifying the pool).
    * `token0`: Information about the first token in the pair.
        * `id`: Token contract address.
        * `symbol`: Token symbol (e.g., "WETH").
        * `decimals`: Token decimals (crucial for converting amounts).
    * `token1`: Information about the second token in the pair (same fields as `token0`).
    * `feeTier`: The fee percentage for this pool (e.g., "500" for 0.05%, "3000" for 0.3%, "10000" for 1%). Used to identify different pools for the same pair.
    * `liquidity`: The *current* total active liquidity in the pool. This is fundamental for V3 price calculations. Represented as a large integer.
    * `sqrtPrice`: The *current* price of token0 in terms of token1, expressed as a square root (√P) in Q64.96 fixed-point format. Crucial for pricing.
    * `tick`: The *current* price tick the pool is operating at. Also essential for V3 calculations.
    * `totalValueLockedUSD` (Optional but Recommended): Total value locked in the pool in USD. Useful for filtering out insignificant pools or displaying pool stats.
    * `volumeUSD` (Optional): Recent trading volume. Also useful for filtering or stats.

2.  **Tokens (`Token` Entity):** 
    * `id`: Token contract address.
    * `symbol`: Symbol.
    * `name`: Full name.
    * `decimals`: Decimals.

**II. How to Build Queries:**

The most common task is finding relevant pools for a given token pair (e.g., Token A and Token B).

**Strategy:** Query pools that contain *at least one* of the tokens, then filter in your backend. Querying for exact pairs directly using `where: {token0: A, token1: B}` can be cumbersome because you also need the `where: {token0: B, token1: A}` case. A more practical approach:

1.  Query all pools where `token0` is Token A.
2.  Query all pools where `token1` is Token A.
3.  **filter** out pools with very low liquidity (`totalValueLockedUSD` or `liquidity`).


**III. Backend Logic After Querying:**
1.  Combine these results in backend.
2.  Filter the combined list to keep only those pools where the *other* token is Token B.
3.  Use the `liquidity`, `sqrtPrice`, `tick`, `feeTier`, and token `decimals` from these pools in your aggregator's pricing/routing algorithm (likely using a Uniswap V3 SDK or library for the complex math).

---

## How to construct the graph?

This kind of problem falls under the category of "Dynamic Graph or State-aware Shortest Path" in graph theory.

## break down DeFi aggregator source code.

### 各 Python 文件功能概览

1.  **`constants.py`**:
    * **用途**: 定义整个项目中使用的常量。这可能包括链 ID、RPC 节点 URL、重要的合约地址（如 WETH、USDC）、API 密钥（**注意：检查是否硬编码，生产中不应如此**）、数值常量（如超时时间、最大跳数）、或者默认配置参数。
    * **算法**: 无，主要是静态数据定义。
    * **解决问题**: 集中管理配置和固定值，避免在代码中散布“魔法数字”或字符串，方便修改和维护。

2.  **`token_collector.py`**:
    * **用途**: 负责收集和管理代币（Token）信息。这可能包括从链上（读取 ERC20 合约的 `name`, `symbol`, `decimals`）、API（如 CoinGecko）或预定义的列表（如 `data/uniswap_v2_tokens.json`, `data/erc_20.json`）获取代币地址、符号、名称、小数位数等元数据。可能还会利用 `data/bad_tokens.json` 来过滤掉不需要或有问题的代币。
    * **算法**: 数据获取逻辑（API 请求、RPC 调用 `web3.py`）、数据解析、过滤。
    * **解决问题**: 为聚合器提供必要的代币基础信息，以便正确处理金额和识别资产。

3.  **`pool_collector.py` / `collect_pools.py`**:
    * **用途**: 这两个文件（或其中一个）负责发现和收集不同 DEX 协议（如 Uniswap V2/V3, SushiSwap, DODO - 从 `ABI/` 目录看支持 DODO）的流动性池（Pool）信息。这通常涉及与 DEX 的工厂合约交互以获取池地址，然后查询每个池合约以获取储备量（Reserves）、费用等级、Tick 数据（V3）或其他相关状态。可能使用了 Subgraphs 或直接的 RPC 调用 (`web3.py`) 配合 `ABI/` 文件。`full_pools.txt` 可能是输入列表或缓存。
    * **算法**: 区块链交互 (RPC 调用，例如使用 `web3.py`)、Subgraph 查询、API 调用、数据解析和存储。可能涉及并发处理以加速数据收集。
    * **解决问题**: 获取进行路由计算所需的所有流动性来源的原始数据。这是聚合器的基础。

4.  **`graph_constructor.py`**:
    * **用途**: 将从 `pool_collector` 和 `token_collector` 获取的原始池和代币数据，构建成一个图（Graph）数据结构。在这个图中，节点通常代表代币，边代表连接这些代币的流动性池。边的权重可能代表价格、流动性或费用等因素，用于后续的路径查找。
    * **算法**: 图数据结构的创建和表示（可能使用字典、邻接列表，或如图 `networkx` 这样的库）。
    * **解决问题**: 将离散的池数据转化为适合路径查找算法处理的结构化表示。

5.  **`gas_fee_estimator.py`**:
    * **用途**: 估算执行某条潜在交易路径所需的 Gas 费用（交易成本）。这需要了解路径涉及的合约交互（跳数、DEX 类型）以及当前链上的 Gas价格（通过 RPC 调用如 `eth_gasPrice` 或 EIP-1559 接口获取）。
    * **算法**: RPC 调用获取 Gas 价格，根据交易路径的复杂性（跳数、合约调用）估算 Gas limit，然后计算总费用。
    * **解决问题**: 在比较不同路径时，不仅考虑换取的代币数量，还要考虑交易成本，从而找到**净收益最高**的路径。

6.  **`price_impact_calculator.py`**:
    * **用途**: 计算在特定流动性池或路径上执行给定交易规模时，预期的价格影响（滑点）。这取决于池的流动性深度和自动做市商（AMM）的具体数学模型（例如 Uniswap V2 的 `x*y=k`，或 DODO 的 PMM 算法）。
    * **算法**: 实现不同 DEX 的 AMM 价格计算公式。
    * **解决问题**: 评估路径的成本效益，避免因滑点过高导致用户损失，是选择最佳路径的关键因素之一。

7.  **`pathfinder.py` / `path_crawler.py`**:
    * **用途**: 在 `graph_constructor` 构建的图上查找从输入代币到输出代币的所有可能交易路径。
    * **算法**: 图遍历算法。可能是：
        * 广度优先搜索（BFS）或深度优先搜索（DFS）：查找所有达到一定深度（跳数）的路径。
        * Dijkstra 或 Bellman-Ford（或其变种）：如果边的权重适合表示“成本”（例如，取对数的价格可以转化为寻找最短路径问题以最大化输出），则用于寻找最优路径。需要注意 DEX 的边权重可能依赖于交易量。
    * **解决问题**: 发现连接起始和目标代币的潜在交易序列（例如 A -> Pool1 -> B -> Pool2 -> C）。

8.  **`smart_order_router.py` (SOR)**:
    * **用途**: 这是聚合器的核心大脑。它接收用户的兑换请求（输入/输出代币、金额），调用 `pathfinder` 获取所有可能的路径，然后对每条路径使用 `price_impact_calculator` 和 `gas_fee_estimator` 进行评估。最关键的是，它可能会决定将一个订单**拆分**到多条路径上执行（订单拆分），以获得比任何单条路径更好的总体价格。最终确定最佳执行策略。
    * **算法**: 整合其他模块的结果；路径评估、排序和过滤；**订单拆分算法**（可能是简单的贪心策略，也可能是更复杂的优化算法，如线性规划或基于边际价格的迭代）；最终决策逻辑，综合考虑输出数量、Gas 成本和价格影响。
    * **解决问题**: 找到最优的方式（可能涉及多路径组合）来执行用户的兑换请求，最大化用户收到的净代币数量。

9.  **`server.py`**:
    * **用途**: 通过 API（很可能是 RESTful API）暴露聚合器的核心功能（主要是 SOR 的报价 `quote` 或执行 `swap` 功能）。它监听 HTTP 请求，解析输入参数，调用 `smart_order_router` 获取最佳路径和报价，并将结果（JSON 格式）返回给前端或其他调用者。可能使用了像 Flask 或 FastAPI 这样的 Web 框架。`static/swagger.yaml` 用于定义和描述这个 API。
    * **算法**: Web 服务器逻辑（路由、请求解析、响应格式化）、输入验证。
    * **解决问题**: 使聚合器后端逻辑能够被外部访问和使用。

10. **`testcases.py`**:
    * **用途**: 包含自动化测试用例，用于验证各个模块（单元测试）或整体路由逻辑（集成测试）的正确性。可能使用了 `pytest` 或 `unittest` 框架。可能会加载 `test_results/` 下的数据进行测试。
    * **算法**: 测试逻辑和断言（Assertions）。
    * **解决问题**: 保证代码质量，防止引入错误（回归），验证算法的有效性。

### 学习源码的步骤：

**阶段一：基础与配置 (Setting the Stage)**

1.  **环境设置**: 确保你的 Python 环境已配置好，并尝试安装项目所需的依赖（通常在 `requirements.txt` 文件中，虽然这里没有列出，但实际项目应该有）。如果项目使用特定工具（如 `web3.py` 等），确保它们已安装。
2.  **阅读 `constants.py`**: 这是最简单的起点。了解项目依赖哪些外部服务（RPC 节点）、哪些是核心代币/合约地址，以及有哪些可配置的参数。这能让你对项目所处的区块链环境和核心交互对象有个初步认识。

**阶段二：数据来源与准备 (Data Foundation)**

3.  **理解代币信息 (`token_collector.py`, `data/*.json`)**: 阅读这个文件，了解它是如何获取和存储代币信息的。查看 `data/` 目录下的 JSON 文件，了解预定义的数据格式。理解代币元数据（特别是 `decimals`）的重要性。
4.  **理解池信息 (`pool_collector.py`/`collect_pools.py`, `ABI/*.json`)**: 这是数据收集的核心。弄清楚代码是如何发现不同 DEX 的池子的（是读取工厂合约？还是依赖 Subgraph/API？）。重点关注它如何获取池的储备量 (reserves) 或其他状态。查看 `ABI/` 目录了解它具体支持与哪些合约交互。理解数据是如何被存储或缓存的。

**阶段三：核心模型与计算 (Modeling & Calculations)**

5.  **图的构建 (`graph_constructor.py`)**: 理解代码如何将收集到的池和代币信息转换成图结构。节点是什么？边是什么？边的权重是如何定义的？这对理解后续的路径查找至关重要。
6.  **核心计算逻辑 (`price_impact_calculator.py`, `gas_fee_estimator.py`)**: 分别阅读这两个模块。理解价格影响是如何根据 AMM 公式计算的，以及 Gas 费用是如何估算的。这是评估路径优劣的基础。

**阶段四：路由算法核心 (The Routing Engine)**

7.  **路径发现 (`pathfinder.py`/`path_crawler.py`)**: 深入研究路径查找算法。代码是使用了标准的图算法（BFS/DFS/Dijkstra）还是自定义的逻辑？它是如何处理多跳路径的？输出是什么（路径列表）？
8.  **智能订单路由 (`smart_order_router.py`)**: **这是最核心、最复杂的部分**。仔细阅读这个模块。
    * 它是如何调用 `pathfinder` 获取路径的？
    * 它是如何使用 `price_impact_calculator` 和 `gas_fee_estimator` 评估每条路径的？
    * **关键：订单拆分逻辑**。代码是否实现了订单拆分？如果是，它是如何决定拆分比例和路径组合的？这是聚合器价值的关键所在。
    * 最终是如何确定最佳报价或执行计划的？

**阶段五：服务暴露与测试 (Exposure & Verification)**

9.  **API 服务 (`server.py`, `static/swagger.yaml`)**: 阅读服务器代码，了解 API 的端点（Endpoints）、请求/响应格式。查看 `swagger.yaml` 可以帮你更快地理解 API 结构。理解它如何接收请求并调用 `smart_order_router`。
10. **测试用例 (`testcases.py`)**: 阅读测试代码是理解模块预期行为和边界情况的好方法。尝试运行测试（如果可以的话），看看它们是如何验证核心逻辑的。

**通用学习技巧:**

* **自顶向下，再自底向上**: 先通过 `server.py` 和 `smart_order_router.py` 了解整体流程和目标，然后再深入到各个子模块（数据收集、计算、路径查找）的具体实现。最后再回到顶层，看它们是如何协同工作的。
* **跟踪数据流**: 特别关注关键数据（如代币信息、池状态、路径列表、最终报价）是如何在不同模块之间传递和转换的。
* **关注算法**: 特别留意路径查找和订单拆分部分使用的算法，这是聚合器的核心竞争力。
* **使用调试器**: 如果可能，使用 Python 调试器（如 `pdb` 或 IDE 的调试功能）单步执行代码，观察变量变化，理解执行流程。
* **添加打印语句**: 在关键位置添加 `print()` 语句输出变量值或执行标记，帮助你理解代码逻辑。
* **小范围实验**: 尝试修改一小部分代码（例如，改变一个参数，注释掉一部分逻辑），然后运行（或运行测试），观察结果变化，加深理解。
* **查阅文档**: 如果代码中使用了第三方库（如 `web3.py`, `requests`, `networkx`），查阅这些库的官方文档。

### TODO:

uniswap volumeUSD不对，按这个排名不对

smart_order_router.py:
指标字段不一致：如果不同协议的 metric 字段不同（如 tvlUSD vs volumeUSD），

stable pool等多币池被拆成对池影响amount_out计算

V3 计算到相邻tick
获取并填入 balancer dynamic fee 常数

---

# Balancer V2/3

## [Pool Types](https://github.com/balancer/docs/tree/7ab2d4ccaca3f191db9448015e6720db41428a87/docs/concepts/pools)

| 池子类型                 | 数学模型核心                         | 特点说明 | 池子地址示例   |
|--------------------------|--------------------------------------|----------|
| **WEIGHTED**             | 📐 加权恒积公式（Weighted Constant Product） | 可非对称权重、多币支持（类似 Uniswap，但更灵活） |
| **STABLE**               | 🔁 恒和模型（Stable Constant Sum/Product Hybrid） | 适合 1:1 稳定币交易，类似 Curve V1 |
| **META_STABLE**          | 🔁 恒和 + 可变比例偏移（Virtual Parameters） | 可处理非完美锚定的资产（如 stETH） |
| **COMPOSABLE_STABLE**    | 🔁 改进的 Stable Pool，可嵌套 BPT + 支持可组合交易 | 适合多层池组合，如 pxETH/wETH |
| **GYROE**                | 🧠 Gaussian (高斯函数曲线) 定价机制 | 极端流动性集中在「理想价格」周围（研究性项目） |
| **COW_AMM**              | 🤝 CowSwap 集成，使用链下撮合的 Request-for-Quote | 无链上 swap 定价函数，链下确定价格 |
| **ELEMENT**              | 📉 固定折扣模型（Principal/Interest 分离） | 类似零息债券，不是真正意义的 AMM |
| **LIQUIDITY_BOOTSTRAPPING (LBP)** | 📉 动态调整权重（下降式拍卖） | 用于代币发行，权重随时间变化 |

其他池子概念：

**Buffer Pool**： 在V2中有 **Buffer Pool** 的概念，V3 中没有单独的 Buffer Pool，而是直接通过每个 token 的 priceRate 来实现相同功能

**Nested Pool**

**Boosted Pool**: Balancer在2021年底和Aave合作推出了Boosted Pools（增强池），可以将闲置的流动性用于Aave等协议的流动性挖矿。
---

### 🔍 1. WEIGHTED POOL
- 数学模型：
  \[
  a_{\text{out}} = b_{\text{out}} \cdot \left(1 - \left( \frac{b_{\text{in}}}{b_{\text{in}} + a_{\text{in}}} \right)^{w_{\text{in}}/w_{\text{out}}} \right)
  \]
- 类似 Uniswap v2，但支持任意代币权重，不局限 50/50；
- 可用于指数型组合（如 80% ETH + 20% WBTC）；

---

### 🔍 2. STABLE POOL
- 数学模型：
  - 基于 Curve v1 的 StableSwap 模型：
  \[
  D = \text{invariant}(\vec{b}) \quad\text{保持恒定}
  \]
- 使用恒和 + 恒积混合的方式，能低滑点处理稳定资产兑换；
- 适合：USDC/USDT/DAI 等；

---

### 🔍 3. META_STABLE
- 模型是 **StableSwap** 的变体，加入「动态虚拟锚定参数」：
  - 可通过合约参数定义偏移，使其适应非完全锚定资产；
- 应用场景：stETH、cbETH、wstETH 等；

---

### 🔍 4. **COMPOSABLE_STABLE**
- ✅ 是 **MetaStable 的升级版**：
  - 支持任意 BPT 嵌套（Composable）
  - 完全在 Vault 内结算（不复制 token）
- 数学模型与 MetaStable 类似，但兼容性更强；
- 常用于多层池子或 LSD 聚合池；

2021年8月，Balancer宣布和Lido推出MetaStable（亚稳定）池，后来，Balancer将所有稳定类型的流动池（稳定池、亚稳定池等）统一升级为可组合的稳定池。可组合稳定池可以直接用自己的LP代币进行交易，即“嵌套”交易，也可以用LP代币在其它池中与WETH等资产组成交易对，从而减少加入和退出流动性池的Gas费。

### about **NestedPool**：

```json

pool.gql query item：

from https://github.com/balancer/backend/blob/v3-canary/apps/api/gql/schema/pool.gql
"""
All info on the nested pool if the token is a BPT. It will only support 1 level of nesting.
"""
type GqlNestedPool {}

"""
All info on the pool token. It will also include the nested pool if the token is a BPT. It will only support 1 level of nesting.
A second (unsupported) level of nesting is shown by having hasNestedPool = true but nestedPool = null.
"""
type GqlPoolTokenDetail {
    """
    Indicates whether this token is a BPT and therefor has a nested pool.
    """
    hasNestedPool: Boolean!
    """
    Additional data for the nested pool if the token is a BPT. Null otherwise.
    """
    nestedPool: GqlNestedPool
}

----------------------------------------------------------------

Query SQL：

{
  aggregatorPools(
    first: 1000
    orderBy: totalLiquidity
    orderDirection: desc
    where: {chainIn: [MAINNET], minTvl: 3000}
  ) {
    type
    address
    
    poolTokens {
      symbol
      weight
      priceRate
      balanceUSD
      hasNestedPool
      nestedPool{
        symbol
				tokens{
          symbol
        }
      }
    }
  }
}

----------------------------------------------------------------

example pool 1：
a query of nestedPool：

      {
        "type": "STABLE",
        "address": "0x3dd0843a028c86e0b760b1a76929d1c5ef93a2dd",
        "protocolVersion": 2,
        "poolTokens": [
          {
            "symbol": "B-80BAL-20WETH",
            "scalingFactor": null,
            "weight": null,
            "balance": "69269.67931333178",
            "priceRate": "1.0",
            "balanceUSD": "238980.3936309947",
            "hasNestedPool": true,
            "nestedPool": {
              "symbol": "B-80BAL-20WETH",
              "tokens": [
                {
                  "symbol": "BAL"
                },
                {
                  "symbol": "WETH"
                }
              ]
            }
          },
          {
            "symbol": "auraBAL",
            "scalingFactor": null,
            "weight": null,
            "balance": "488929.18471668055",
            "priceRate": "1.0",
            "balanceUSD": "1452119.678608541",
            "hasNestedPool": false,
            "nestedPool": null
          }
        ],
        "dynamicData": {
          "swapFee": "0.003",
          "totalLiquidity": "1691100.07",
          "aggregateSwapFee": "0"
        }
      },

----------------------------------------------------------------

example pool 2：
a query of COMPOSABLE_STABLE and nestedPool：

     {
        "type": "COMPOSABLE_STABLE",
        "address": "0x49cbd67651fbabce12d1df18499896ec87bef46f",
        "protocolVersion": 2,
        "poolTokens": [
          {
            "symbol": "sDAI/3Pool",
            "scalingFactor": null,
            "weight": null,
            "balance": "2596148429299374.5",
            "priceRate": "1.038542652973860171",
            "balanceUSD": "0",
            "hasNestedPool": false,
            "nestedPool": null
          },
          {
            "symbol": "USDC-DAI-USDT",
            "scalingFactor": null,
            "weight": null,
            "balance": "985.2553298423234",
            "priceRate": "1.044189789005595951",
            "balanceUSD": "1028.722608607005",
            "hasNestedPool": true,
            "nestedPool": {
              "symbol": "USDC-DAI-USDT",
              "tokens": [
                {
                  "symbol": "DAI"
                },
                {
                  "symbol": "USDC-DAI-USDT"
                },
                {
                  "symbol": "USDC"
                },
                {
                  "symbol": "USDT"
                }
              ]
            }
          },
          {
            "symbol": "sDAI",
            "scalingFactor": null,
            "weight": null,
            "balance": "1500.8563191084506",
            "priceRate": "1.154937237712146794",
            "balanceUSD": "1733.555078090355",
            "hasNestedPool": false,
            "nestedPool": null
          }
        ],
        "dynamicData": {
          "swapFee": "0.0001",
          "totalLiquidity": "2762.28",
          "aggregateSwapFee": "0"
        }

----------------------------------------------------------------

This is its sub-pool（NestedPool）.
                },
                    {
                  "type": "COMPOSABLE_STABLE",
                  "address": "0x79c58f70905f734641735bc61e45c19dd9ad60bc",
                  "protocolVersion": 2,
                  "poolTokens": [
                    {
                      "symbol": "DAI",
                      "scalingFactor": null,
                      "weight": null,
                      "balance": "1040.332786182294",
                      "priceRate": "1.0",
                      "balanceUSD": "1040.332786182294",
                      "hasNestedPool": false,
                      "nestedPool": null
                    },
                    {
                      "symbol": "USDC-DAI-USDT",
                      "scalingFactor": null,
                      "weight": null,
                      "balance": "2596148430039884.5",
                      "priceRate": "1.044199886556045028",
                      "balanceUSD": "0",
                      "hasNestedPool": false,
                      "nestedPool": null
                    },
                    {
                      "symbol": "USDC",
                      "scalingFactor": null,
                      "weight": null,
                      "balance": "1307.117326",
                      "priceRate": "1.0",
                      "balanceUSD": "1306.972235976814",
                      "hasNestedPool": false,
                      "nestedPool": null
                    },
                    {
                      "symbol": "USDT",
                      "scalingFactor": null,
                      "weight": null,
                      "balance": "2240.337417",
                      "priceRate": "1.0",
                      "balanceUSD": "2240.032731111288",
                      "hasNestedPool": false,
                      "nestedPool": null
                    }
                  ],
                  "dynamicData": {
                    "swapFee": "0.0001",
                    "totalLiquidity": "4587.34",
                    "aggregateSwapFee": "0"
                  }
                },
```


[什么是**Composable**？](https://github.com/balancer/docs/blob/7ab2d4ccaca3f191db9448015e6720db41428a87/docs/concepts/pools/composable-stable.md#L4)

A pool is composable when it allows swaps to and from its own LP token. **Putting its LP token into other pools (or "nesting")** allows easy Batch Swaps from nested pool tokens to tokens in the outer pool.

示例1为什么nested但只是普通的stable pool？:

composable-stable pool 强调的是：这个池子自己的 LP Token（BPT）还能被用于其他池子中，继续作为 token swap 的一部分。

这个示例1只是一个 普通的 Stable Pool，用到了一个 嵌套的 LP Token。但它自己的 LP Token 不可组合使用（查询结果中pooltokens没有它的LP token），所以不符合 Composable 的定义。

---

### 🔍 5. GYROE
- 使用 **Gaussian 曲线模型**：
  \[
  P(x) = e^{- (x - \mu)^2 / 2\sigma^2 }
  \]
- 目标是集中流动性在某个「理想价格区间」；
- 类似 Uniswap V3 的集中流动性，但用不同数学方式实现；
- 研究型实验，精度高但复杂；

---

### 🔍 6. COW_AMM
- 无链上数学模型（**链下撮合**）：
  - 用户订单由 CowSwap 执行；
  - 不由 AMM 合约做定价；
  - Balancer 只是流动性来源（Liquidity Source）；

---

### 🔍 7. ELEMENT
- Element Finance 的子协议；
- 用于 Principal Token & Yield Token 的分离交易；
- Swap 价格按「固定折价/折溢价」设定，不是 AMM；

---

### 🔍 8. LIQUIDITY_BOOTSTRAPPING POOL (LBP)
- 使用 Weighted Pool 改进模型；
  - 权重随时间下降，引导价格从高到低（降低抢购）；
  - 常见公式：
    \[
    w(t) = w_0 \cdot e^{-kt}
    \]
- 常用于项目首次发行 token 的拍卖池。

---

## 🧠 总结图谱：

```text
             ┌─────────────┐
             │  WEIGHTED   │ ←─基础 AMM（灵活权重）
             └────┬────────┘
                  ↓
      ┌────────────────────┐
      │  LIQUIDITY_BOOTSTRAP│ ← 改进权重用于 Token 发售
      └────────────────────┘

             ┌─────────────┐
             │   STABLE    │ ← Curve 风格低滑点模型
             └────┬────────┘
                  ↓
         ┌──────────────────────┐
         │ META_STABLE / COMPOSABLE_STABLE │ ←锚定资产 or 嵌套池支持
         └──────────────────────┘

         ┌─────────┐      ┌──────────────┐
         │  GYROE  │      │   COW_AMM    │
         └─────────┘      └──────────────┘
             ↑                 ↑
        高斯集中        CowSwap 链下撮合

         ┌──────────┐
         │ ELEMENT  │ ← 固定利率池子
         └──────────┘
```

---

## Create pool on balancer

是的，你说得非常对，Balancer 和 Uniswap 在“创建池子”的方式上确实 **有很大区别**：

---

### 🧱 核心区别总结：

| 项目 | Uniswap | Balancer |
|------|---------|----------|
| 创建方式 | 工厂合约调用 `createPool(...)` 即可 | 有些池子是这样，但很多需要**部署自定义池合约** |
| 可否传参创建 | 可以（如 Uniswap V3） | 一部分可以（如 Weighted、Stable），但很多复杂池必须自定义 |
| 池逻辑封装 | 所有池使用统一逻辑（immutable） | 池逻辑可扩展，支持多种数学模型，自定义性更强 |
| 池种类 | V2（常乘）、V3（可自定义 fee + tick spacing） | Weighted、Stable、MetaStable、Linear、ComposableStable、Boosted 等 |

---

### ✅ 在 Balancer 上创建池的两种方式：

---

### 1️⃣ 使用 Balancer 的 **预定义池工厂（Factory）** 创建标准池

这适用于：

- Weighted Pool（加权池）
- Stable Pool（稳定币池）
- MetaStable Pool
- ComposableStable Pool（多资产池）

使用方法类似：

```solidity
IWeightedPoolFactory(factoryAddress).create(
  name,
  symbol,
  tokens,
  weights,
  swapFeePercentage,
  owner
);
```



### 2️⃣ 部署你自己写的自定义池合约

这种方法适用于：

- 需要**完全自定义数学模型**
- 构建实验性 AMM（如常乘池、指数池、定额池等）
- 使用 Balancer 的 **Vault 结构托管资产**，但自己实现 `onSwap()` 等逻辑
- 使用 hook 函数

需要做：

- 写一个符合 `IBasePool` 接口的合约
- 实现 `onSwap()`、`getSwapFee()` 等必要方法
- 用 Balancer 的 `Vault` 注册池子
- 调用 `IVault.registerPool(...)` 将你的池注册进系统
- 注册 token slot（`registerTokens(...)`）

---
### Swap on Balancer:

Balancer架构特点：

Balancer使用中央化的Vault管理所有资金，与Uniswap的独立池子不同
交易需要通过Vault的swap函数执行，而不是直接调用池子
每个池子有唯一的poolId标识，与Vault交互时需要提供


主要测试功能：

test_SwapToken0ForToken1(): 测试从wstETH交换到AAVE的交易
test_SwapToken1ForToken0(): 测试从AAVE交换到wstETH的交易
test_DirectOnSwap(): 额外添加的直接测试pool的onSwap计算函数(不执行实际交易)



# Curve V1/V2

数据获取：
使用curve_fee_enricher.py 数据整合脚本，从Curve池子合约中获取缺失的fee和offpeg_fee_multiplier参数
查询官方提供的api得到pool data
添加fee和offpeg_fee_multiplier参数
multi-pool 拆分成对 pair pool
将完整的multi-pool data 加入 pool data字段
如果是MetaPool,根据basepool_address从pool data中找到对应的basepool data 添加为basepool字段


[In Curve, pools can be 2 different types, these are:](https://resources.curve.fi/pools/overview/)

  - **Stableswap Pools** (Curve V1) for coins that are pegged to each other, for example USDC and USDT, or stETH and ETH.  
  - **Cryptoswap Pools** (Curve V2) which are for assets which fluctuate in value against each other, for example USDT and ETH, or CRV and ETH.

[curve-api](https://docs.curve.fi/curve-api/curve-api/)

## Stableswap Pools


## MetaPools

MetaPool 是一种特殊的 Curve 流动性池，它允许用户用一个新的代币（比如 USDT）与已有的稳定币池（比如 3pool）中的 LP Token（比如 3CRV）进行配对，从而创建一个新池。

USDT/3CRV MetaPool:  

```json
{
    "id": "40",
    "address": "0x5a6A4D54456819380173272A5E8E9B9904BdF41B",
    "coinsAddresses": [
      "0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3",
      "0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490",
      "0x0000000000000000000000000000000000000000",
      "0x0000000000000000000000000000000000000000"
    ],
    "decimals": [
      "18",
      "18",
      "0",
      "0"
    ],
    "virtualPrice": "1017227562020141029",
    "amplificationCoefficient": "2000",
    "underlyingDecimals": [
      "18",
      "18",
      "6",
      "6",
      "0",
      "0",
      "0",
      "0"
    ],
    "totalSupply": "33919062973451873514393312",
    "name": "Curve.fi Factory USD Metapool: Magic Internet Money 3Pool",
    "assetType": "0",
    "priceOracle": null,
    "implementation": "",
    "zapAddress": "0xa79828df1850e8a3a3064576f380d90aecdd3359",
    "assetTypeName": "usd",
    "coins": [
      {
        "address": "0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3",
        "usdPrice": 1.00031417437482,
        "decimals": "18",
        "isBasePoolLpToken": false,
        "symbol": "MIM",
        "name": "Magic Internet Money",
        "poolBalance": "15161283844810459923336580"
      },
      {
        "address": "0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490",
        "usdPrice": 1.0396126002839468,
        "decimals": "18",
        "isBasePoolLpToken": true,
        "symbol": "3Crv",
        "name": "Curve.fi DAI/USDC/USDT",
        "poolBalance": "18601203715523543465901743"
      }
    ],
    "poolUrls": {
      "swap": [
        "https://curve.fi/dex/#/ethereum/pools/mim/swap",
        "https://classic.curve.fi/mim"
      ],
      "deposit": [
        "https://curve.fi/dex/#/ethereum/pools/mim/deposit",
        "https://classic.curve.fi/mim/deposit"
      ],
      "withdraw": [
        "https://curve.fi/dex/#/ethereum/pools/mim/withdraw",
        "https://classic.curve.fi/mim/withdraw"
      ]
    },
    "lpTokenAddress": "0x5a6A4D54456819380173272A5E8E9B9904BdF41B",
    "usdTotal": 34504092.89479072,
    "isMetaPool": true,
    "basePoolAddress": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
    "underlyingCoins": [
      {
        "address": "0x99D8a9C45b2ecA8864373A26D1459e3Dff1e17F3",
        "usdPrice": 1.00031417437482,
        "decimals": "18",
        "isBasePoolLpToken": false,
        "symbol": "MIM",
        "name": "Magic Internet Money",
        "poolBalance": "15161283844810459923336580"
      },
      {
        "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "usdPrice": 0.9999985613539117,
        "decimals": "18",
        "isBasePoolLpToken": false,
        "symbol": "DAI",
        "name": "Dai Stablecoin",
        "poolBalance": "5613206849224510209744643"
      },
      {
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "usdPrice": 1,
        "decimals": "6",
        "isBasePoolLpToken": false,
        "symbol": "USDC",
        "name": "USD Coin",
        "poolBalance": "5703335826977"
      },
      {
        "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "usdPrice": 0.9999628335911316,
        "decimals": "6",
        "isBasePoolLpToken": false,
        "symbol": "USDT",
        "name": "Tether USD",
        "poolBalance": "8025742439685"
      }
    ],
    "usdTotalExcludingBasePool": 15166047.131683873,
    "gaugeAddress": "0xd8b712d29381748db89c36bca0138d7c75866ddf",
    "gaugeRewards": [
      {
        "gaugeAddress": "0xd8b712d29381748db89c36bca0138d7c75866ddf",
        "tokenPrice": 0.0005205007754259217,
        "name": "Spell Token",
        "symbol": "SPELL",
        "decimals": "18",
        "apy": 0,
        "tokenAddress": "0x090185f2135308BaD17527004364eBcC2D37e5F6"
      }
    ],
    "gaugeCrvApy": [
      5.867610730288268,
      14.669026825720671
    ],
    "gaugeFutureCrvApy": [
      5.8589855385905905,
      14.647463846476477
    ],
    "usesRateOracle": false,
    "isBroken": false,
    "hasMethods": {
      "exchange_received": false,
      "exchange_extended": false
    },
    "creationTs": 1622671203,
    "creationBlockNumber": 12557139,
    "blockchainId": "ethereum",
    "registryId": "main"
  }
  ```

the function exchange_underlying of MetaPool:  

MetaPool token ↔ BasePool token：通过base pool的`add_liquidity`或`remove_liquidity_one_coin` 来转换  

BasePool token ↔ BasePool token：直接调用 base pool 的 exchange

### virtual_price 

virtual_price = 当前池子总资产价值 / 当前总 LP token 数量

为什么要有virtual_price ？

如果你在 MetaPool 中将 3CRV token 当作普通 token 用来交易，那你必须知道：LP token 的“实际价值”

```json
 {
    "id": "0",
    "address": "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
    "coinsAddresses": [
      "0x6B175474E89094C44Da98b954EedeAC495271d0F",
      "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
      "0xdAC17F958D2ee523a2206206994597C13D831ec7",
      "0x0000000000000000000000000000000000000000"
    ],
    "decimals": [
      "18",
      "6",
      "6",
      "0"
    ],
    "virtualPrice": "1039838639719566241",
    "totalSupply": "169381828563799202857361424",
    "coins": [
      {
        "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "usdPrice": 1.000122583197268,
        "decimals": "18",
        "isBasePoolLpToken": false,
        "symbol": "DAI",
        "name": "Dai Stablecoin",
        "poolBalance": "48741811044972286421938292"
      },
      {
        "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "usdPrice": 1,
        "decimals": "6",
        "isBasePoolLpToken": false,
        "symbol": "USDC",
        "name": "USD Coin",
        "poolBalance": "53600963816438"
      },
      {
        "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "usdPrice": 0.9999472562484096,
        "decimals": "6",
        "isBasePoolLpToken": false,
        "symbol": "USDT",
        "name": "Tether USD",
        "poolBalance": "73787360313518"
      }
      ]
 }
 ```

## Cryptoswap Pools


curve 的fee机制：

1.stable swap的固定费率

2.stable swap的动态费率

添加动态费率的函数`calculate_dynamic_fee`:
```python
def _dynamic_fee(xpi: uint256, xpj: uint256, _fee: uint256) -> uint256:

    _offpeg_fee_multiplier: uint256 = self.offpeg_fee_multiplier
    if _offpeg_fee_multiplier <= FEE_DENOMINATOR:
        return _fee

    xps2: uint256 = (xpi + xpj) ** 2
    return unsafe_div(
        unsafe_mul(_offpeg_fee_multiplier, _fee),
        unsafe_add(
            unsafe_sub(_offpeg_fee_multiplier, FEE_DENOMINATOR) * 4 * xpi * xpj / xps2,
            FEE_DENOMINATOR
        )
    )
  ```
`FEE_DENOMINATOR`: 判断是否启用动态费用机制。

`offpeg_fee_multiplier`：当池子偏离 1:1 时，对应的费率放大系数, **资产严重脱锚时：**swap fee大幅提升。

3.crypto swap的动态费率：

fee = (mid_fee * f + out_fee * (1 - f))

 f 的含义（reduction_coefficient）：
 当池子接近平衡时，f ≈ 1e18，手续费接近 mid_fee
 当池子严重不平衡时，f ≈ 0，手续费趋近于 out_fee

---

# materials

## 1inch related contents

🧩 [Chainstack and 1inch](https://chainstack.com/1inch-on-chainstack-journey-to-defi-excellence/?utm_source=chatgpt.com)

```Deployment of 28 subgraphs on Dedicated Subgraphs dedicated indexer```

1inch 选择使用 Dedicated Subgraph, 技术上和 The Graph 的 Subgraph 是一样的机制, 但不是托管在 The Graph 官方的 Hosted Service 或 Decentralized Network，而是由 Chainstack 等节点服务商托管的“专属服务”。

💡 [可以用Chainstack 部署你自己的 Dedicated Subgraph](https://chainstack.com/dedicated-subgraphs/)

---

🧩 [The 1inch RabbitHole - Stay protected from sandwich attacks](https://1inch.io/rabbithole/)

---

🧩 [Introducing 1inch v2 ](https://blog.1inch.io/introducing-1inch-v2-defis-fastest-and-most-advanced-aggregation-protocol/#tl-dr)

```1inch can pack, unpack and migrate collateral tokens from Aave and Compound as part of the swap path.```

[Pathfinder .png]
```
Splitting a swap across multiple supported liquidity protocols

The utilization of different ‘market depths’ within the same protocol

using 'market depths' as bridges 
// Route through one or more intermediate tokens
// WETH → USDC/USDT → WBTC 
// Here, the USDC and USDT are utilized as the "market depth" that serves as a "bridge".
```


Maximum return and lowest gas return

[Maximum Lowest gas cost return.png]

1inch v2 supports all major protocols:

Uniswap V1, Uniswap V2, WETH, Balancer, Curve, Chai, Sushiswap, Kyber, Oasis, Mooniswap, Compound, Aave, Yearn, Bancor, PMM, C.R.E.A.M. Swap, Swerve, BlackholeSwap, Value Liquid, DODO, Shell.

---

🧩 [1inch Swap API v6, Pathfinder](https://portal.1inch.dev/documentation/contracts/aggregation-protocol/aggregation-introduction?utm_source=chatgpt.com)

### **Fusion Mode**:

is an **intent-based swap** mechanism:

- Instead of executing the swap directly on-chain,  
- The user signs and broadcasts an **intent** like “I want to swap X,”  
- This creates an **off-chain order** containing a limit price and a minimum acceptable return,  
- Then, a third party on-chain — known as a **Resolver** — fills the order and completes the swap.

✅ No gas fees for the user 
🛡️ MEV-resistant (prevents front-running)


🔄 Dutch Auction:

- The exchange rate **decreases block by block over time**,  
- Until it reaches the **minimum return** set by the user.  
- **Resolvers** choose **the optimal moment to fill** the order — ideally when it's most profitable for them — anywhere along the price curve.

### **AggregationRouterV6**:

Execute the simulation path on the chain.

---

## "SOR" related contents

### Deeplink Labs on medium
 
🧩 [Pathfinding Algorithms for DEX Aggregation and Smart Order Routing](https://medium.com/deeplink-labs/pathfinding-algorithms-for-dex-aggregation-and-smart-order-routing-9e9feaf6b796)

```
Representing Smart Order Routing for DEX Aggregation as a Pathfinding Problem

it may be the case that the construction of the graph and its edges is a more complicated task than traversing the graph once created. Selecting valid pools, deciding whether to split orders along with the size and number of those splits, assigning weights
```

💡 Selecting valid pools(The vertex set) -> assigning weights(construct the graph edges) ->  traversing the graph


🧩 [Eta X V1](https://medium.com/deeplink-labs/eta-x-v1-2-speed-scale-and-efficiency-4b21b4dee1b#e4f5)

 finding near-optimal paths through large graphs:

 - Floyd-Warshall &  Bellman-Ford algorithm

 - heuristic algorithms

🧩 [Eta X V2](https://medium.com/deeplink-labs/eta-x-v1-2-speed-scale-and-efficiency-4b21b4dee1b#e4f5)


keep a running cache of all liquidity pools contained within each supported DEX in the backend.

🧩 [Eta X V3](https://medium.com/deeplink-labs/eta-x-v1-3-expanded-dex-support-and-larger-trades-with-order-splitting-91ac0fe2cd70)

Order Splitting

---

### DODO

🧩 [DODO Research: Reveal the Secrets of the Aggregator — Problem Analysis and Model Building](https://blog.dodoex.io/dodo-research-reveal-the-secrets-of-the-aggregator-problem-analysis-and-model-building-ba0ead85948c)

```
1.1 Linear routing
if a user needs to trade ETH to USDC, the optimal path found by A linear routing is to trade ETH to USDT, then it goes to USDC, not [A-C-B] or [A-D-B] (that is, the asset A is not split into two parts and selects different paths). The chosen path only goes through two pools. These two pools may come from different protocols. For example, the protocol to trade ETH to USDT is from the Uniswap V3 pool, and the USDT-USDC protocol is from the Curve V1 pool. DEX such as Uniswap V2 and PancakeSwap also use this routing model.


At first glance, it seems to be a straightforward problem about the shortest path, and there are many mature algorithms for reference. But unlike the ordinary shortest path problems, in the process of looking for the next edge, under the weight of an edge is associated with the path in front of the sequence of the node. Therefore, in the optimum path of nodes joining the queue, each node has a state that needs to be maintained in real-time. It makes the subsequent sequence nodes of recorded path length match the state of the preceding sequence nodes. And in this problem, the final “minimum weight” is calculated not by summing the weights of all edges on the path but by calculating only the entry weight of the toToken node. This characteristic makes the traditional shortest path algorithm not wholly applicable.

When there are few nodes, it is more intuitive to search with the Depth First Search (DFS) algorithm directly, that is, to traverse every path and get the final toToken price, to select the optimal path for users to exchange. The Uniswap V2 route uses this method to find the optimal path. The first version of the Uniswap V3 route uses this method as well.
```


This kind of problem falls under the category of "Dynamic Graph or State-aware Shortest Path" in graph theory.

---

### 0x

🧩 [0x Smart Order Routing](https://0x.org/post/0x-smart-order-routing)

💡 The idea of splitting orders:

Some exchanges offer better rates but at high slippage while others offer worse rates for lower slippage. Below are real-world quotes taken from 2 DEXes to illustrate this common scenario.
[fill size.png]
[fill size 2.png]

---

🧩 [blog.astroport.fi:From Point A to Point Z](https://blog.astroport.fi/post/from-point-a-to-point-z-how-swap-paths-are-determined-on-astroport)

```
During the DFS traversal, the algorithm also checks for duplicate routes by generating a hash for each route and storing it in a set. This allows the algorithm to keep track of unique routes and avoid storing duplicate paths, further enhancing efficiency.
```

---

🧩 [Smart Order Routing: The Secret Sauce of Efficient DEX Aggregators](https://www.fastercapital.com/content/Smart-Order-Routing--Smart-Order-Routing--The-Secret-Sauce-of-Efficient-DEX-Aggregators.html#The-Role-of-SOR-in-Enhancing-Liquidity)

💡 This is the best article that explains the relevant concepts:

What is SOR functions within DEX aggregators

how SOR enhances liquidity

some case studies that showcase SOR in action(what defi action can do with SOR):  
Arbitrage、High-Volume Trade、Gas Fee Optimization

