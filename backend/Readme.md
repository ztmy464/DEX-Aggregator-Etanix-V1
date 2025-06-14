# Python Files Overview  

1. **`constants.py`**  
   - **Purpose**: Defines global constants used throughout the project. These may include:  
     - Chain IDs, RPC node URLs, and critical contract addresses (e.g., WETH, USDC).  
     - API keys (**Note: Avoid hardcoding in production**).  
     - Numerical constants (e.g., timeouts, maximum hop count) or default configuration parameters.  
   - **Algorithm**: None (static data definitions only).  
   - **Problem Solved**: Centralizes configuration and fixed values to avoid "magic numbers/strings" scattered in code, simplifying maintenance.  

2. **`pool_collector.py` / `collect_pools.py`**  
   - **Purpose**: Discovers and collects liquidity pool data from supported DEX protocols (e.g., Uniswap V2/V3, SushiSwap, DODO – inferred from `ABI/` directory). Typically involves:  
     - Querying factory contracts to fetch pool addresses.  
     - Fetching pool states (reserves, fee tiers, tick data for V3) via RPC calls (`web3.py`) or Subgraphs.  
     - May cache results in `full_pools.txt`.  
   - **Algorithm**: Blockchain RPC calls, Subgraph queries, concurrent data fetching, and storage.  
   - **Problem Solved**: Provides raw liquidity source data for routing calculations (foundational for aggregation).  

3. **`graph_constructor.py`**  
   - **Purpose**: Transforms raw pool/token data (from `pool_collector` and `token_collector`) into a graph structure.  
     - **Nodes**: Tokens.  
     - **Edges**: Liquidity pools connecting tokens, weighted by metrics like price, liquidity, or fees.  
   - **Algorithm**: Graph construction (e.g., adjacency lists, `networkx`).  
   - **Problem Solved**: Converts discrete pool data into a structured format for pathfinding algorithms.  

4. **`gas_fee_estimator.py`**  
   - **Purpose**: Estimates gas costs for potential swap paths by:  
     - Fetching current gas prices (via RPC calls like `eth_gasPrice` or EIP-1559).  
     - Calculating gas limits based on path complexity (hops, contract interactions).  
   - **Algorithm**: Gas price lookup + gas limit estimation.  
   - **Problem Solved**: Evaluates net trade profitability by accounting for transaction costs.  

5. **`simulateSwap.py`**  
   - **Purpose**: Simulates price impact (slippage) for a given trade size on a specific pool/path, using AMM models:  
     - Uniswap V2 (`x*y=k`), V3 (ticks). 
   - **Algorithm**: Implements AMM pricing formulas.  
   - **Problem Solved**: Quantifies trade efficiency to avoid high-slippage paths.  

6. **`pathfinder.py` / `path_crawler.py`**  
   - **Purpose**: Finds all possible swap paths between input/output tokens in the constructed graph.  
   - **Algorithm**: Graph traversal:  
     - **BFS/DFS**: Enumerates paths up to a max hop count.  
     - **Dijkstra/Bellman-Ford**: Optimizes for "cost" (e.g., log-transformed prices).  
   - **Problem Solved**: Identifies token swap sequences (e.g., `A → Pool1 → B → Pool2 → C`).  

7. **`smart_order_router.py` (SOR)**  
   - **Purpose**: Core logic for trade aggregation:  
     1. Fetches candidate paths from `pathfinder`.  
     2. Evaluates each path using `simulateSwap` and `gas_fee_estimator`.  
     3. Splits orders across multiple paths (**order splitting**) for optimal execution.  
   - **Algorithm**: Path ranking, order splitting (greedy/linear programming), and cost-benefit analysis.  
   - **Problem Solved**: Maximizes user receive amount by optimizing path execution.  

8. **`server.py`**  
   - **Purpose**: Exposes SOR functionality via REST API (likely Flask/FastAPI):  
     - Endpoints: `quote` (price estimation) and `swap` (execution).  
     - Input validation + JSON response formatting.  
   - **Algorithm**: Web server routing/request handling.  
   - **Problem Solved**: Provides external access to the aggregator backend.  

---

# work process

---

### 1. **Fetching Structured On-Chain Data**
   - **DEX Subgraphs**:
     - Graph nodes monitor blockchain events to provide indexed, structured historical/aggregated data queries.
   - **Multicall**:
     - Smart contract pattern relying on RPC nodes for real-time state reads (cannot retrieve historical data).

### 2. **Constructing the Graph**
   - **Price Quotation (Data Transformation)**:
     - Tools:
       - `viem` (lightweight Ethereum client)
       - DEX SDKs:
         - [Uniswap SDK](https://docs.uniswap.org/sdk/core/overview) (for pool abstractions and math utilities)

### 3. **Smart Order Routing (SOR)**
   - References:
     - `Deeplink Labs: Eta X V1`
     - `DODO Research`
   - **Key Challenges**:
     - Order splitting (optimal distribution across liquidity sources)
     - Multi-hop routing (must balance):
       - Gas optimization
       - Slippage control
       - Maximum output return
       - Lowest gas-adjusted cost

### 4. **Transaction Simulation**

----

## progress bar  

Obtain on-chain data？ → The Graph notes  

↓  

Which data should be obtained？##  

↓  
  
Optimal path discovery?  → materials #   

↓  
  
How to construct the graph (vertex & edges)？  

↓  

How to traversing the graph (pathfinding algorithms)?  
DFS、Floyd-Warshall &  Bellman-Ford、heuristic  

↓  
  
Refactor pool_collector: Include queried raw pool data and base pool information in the results for Curve and Balancer.  

↓  
   
Refactor path_crawler: Reorganize the amount_out calculation logic and encapsulate it into simulateswap.py, skipping price_impact (due to inaccurate USD pricing).  

↓  
  
Ensure the calculate_routes function executes successfully and outputs viable route results.  

---

## TODO: (done)

The Uniswap volume in USD is incorrect. Based on this ranking, it is also wrong. 

smart_order_router.py:  
Indicator fields are inconsistent: the metric fields of different protocols are different (such as tvlUSD vs volumeUSD)

The stable pool and other multi-currency pools have been divided into pairs, and the amount_out calculation has been affected by the pairs. 

V3 calculates to the adjacent tick

Obtain and fill in the constant of balancer dynamic fee

---

## bug logging: (resolved)

1.
for balancer, pools with in bgt token, bgt token need been excluded

3. 
need to set up another query for querying pankeswap ticks

4.
The scaleTokenAmount function is compatible with scientific notation (such as "1.23e-5").

5.
If there is only one pool (that is, filt_pools is a dictionary), 
in fact, when traversing the keys of the dictionary, we are not dealing with the pools themselves.

6.
Handle tick crossing when tick is not initialized

7.
handle the reserve number of CPAMM pool which is not in wei 0xd75ea151a61d06868e31f8988d28dfe5e9df57b4

8.
Adjust the strategy for query ticks, query the ticks with liquidityNet not 0 when the pool value is less than 10M

9.
output_amount is 0, because the liquidity is 0 0x18645a4a6b70fdb959221be0be2091fbe17dc7c1

10.

sell_ID=0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2&sell_amount=1&buy_ID=0x6982508145454ce325ddbe47a25d4ec3d2311933
currently liquidity is big enough, so sub side of multiple liquidityNet is still > 0,
the rest of liquidity is use from current tick to max tick or min tick ??

---

# protocol

## Balancer：

### pool types:

```text
             ┌─────────────┐
             │  WEIGHTED   │ ← Base AMM (Flexible Weighting)
             └────┬────────┘
                  ↓
      ┌────────────────────┐
      │  LIQUIDITY_BOOTSTRAP│ ← Enhanced weights for token launches
      └────────────────────┘

             ┌─────────────┐
             │   STABLE    │ ← Curve-style low-slippage model
             └────┬────────┘
                  ↓
         ┌─────────────────────────────────┐
         │ META_STABLE / COMPOSABLE_STABLE │ ← Pegged assets or nested pool support
         └─────────────────────────────────┘

         ┌─────────┐      ┌──────────────┐
         │  GYROE  │      │   COW_AMM    │
         └─────────┘      └──────────────┘
             ↑                 ↑
        Gaussian Concentrated Liquidity   CowSwap off-chain matching

         ┌──────────┐
         │ ELEMENT  │ ← Fixed-rate pools
         └──────────┘
```

---

## Balancer Architecture Characteristics:

Balancer employs a centralized Vault to manage all assets, differing from Uniswap's independent pool model  
All transactions must be executed through the Vault's swap function rather than direct pool calls  
Each pool is identified by a unique poolId, which must be provided when interacting with the Vault  

Key differences from Uniswap:
- Single Vault vs. decentralized pools
- Indirect swap execution via Vault
- Mandatory poolId reference system

---

## Curve V1/V2

### pool types:

[In Curve, pools can be 2 different types, these are:](https://resources.curve.fi/pools/overview/)

  - **Stableswap Pools** (Curve V1) for coins that are pegged to each other, for example USDC and USDT, or stETH and ETH.  
  - **Cryptoswap Pools** (Curve V2) which are for assets which fluctuate in value against each other, for example USDT and ETH, or CRV and ETH.

---

### Curve Data Collection

1. **Data Sources**  
   - Official [Curve API](https://docs.curve.fi/curve-api/curve-api/)
   - Custom data integration script `curve_fee_enricher.py`

2. **Parameter Retrieval**  
   - Obtains missing parameters directly from Curve pool contracts:
     - `fee` (transaction fee percentage)
     - `offpeg_fee_multiplier` (dynamic fee adjustment coefficient)

3. **Data Processing Workflow**  
   - Queries official API to obtain base pool data
   - Augments data with fee-related parameters
   - For multi-pools:
     - Splits into constituent trading pairs
     - Preserves complete multi-pool structure in `pool_data` field
   - For MetaPools:
     - Locates corresponding base pool data using `basepool_address`
     - Adds as `basepool` field

---

### The fee mechanism of the curve:

1. **Fixed fee** of the stable swap 

2. **Dynamic fee** of stable swap

The function of dynamic rates : `calculate_dynamic_fee`:
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
`FEE_DENOMINATOR`: Determine whether to enable the dynamic fee mechanism.

`offpeg_fee_multiplier`：When the ratio of the pool deviates from 1:1, the corresponding rate amplification coefficient, **severe asset disengagement:** the swap fee significantly increases.  

3.**Dynamic fee** of the crypto swap:

fee = (mid_fee * f + out_fee * (1 - f))

 f （reduction_coefficient）：

When the pool is close to equilibrium, f ≈ 1e18, and the transaction fee is close to the mid_fee.

When the pool is severely unbalanced, f ≈ 0, and the transaction fee approaches the out_fee.

---

# reference materials

## 1inch related contents

🧩 [Chainstack and 1inch](https://chainstack.com/1inch-on-chainstack-journey-to-defi-excellence/?utm_source=chatgpt.com)

```Deployment of 28 subgraphs on Dedicated Subgraphs dedicated indexer```

1inch opts to use the Dedicated Subgraph. Technically, it operates on the same mechanism as The Graph's Subgraph, but it is not hosted on The Graph's official Hosted Service or Decentralized Network. Instead, it is managed by node service providers such as Chainstack.

💡 [deploy your own Dedicated Subgraph using Chainstack.](https://chainstack.com/dedicated-subgraphs/)

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

