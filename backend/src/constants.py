UNISWAP_V2 = 'Uniswap_V2'
SUSHISWAP_V2 = 'Sushiswap_V2'
UNISWAP_V3 = "Uniswap_V3"
PANCAKESWAP_V3 = "Pancakeswap_V3"
CURVE = 'Curve'
BALANCER_V3 = 'Balancer_V3'

MAX_ROUTES = 10

DEX_LIST = (
    CURVE,
    BALANCER_V3,
    UNISWAP_V2,
    UNISWAP_V3,
    SUSHISWAP_V2,
    PANCAKESWAP_V3,
)
MAX_ORDERS = 20 # Seems unused currently

# used for sorting/pagination when fetching pools
DEX_ORDER_BY = {
    UNISWAP_V2: 'trackedReserveETH',
    UNISWAP_V3: 'volumeUSD',
    SUSHISWAP_V2: 'reserveUSD',
    PANCAKESWAP_V3: 'totalValueLockedUSD',
    CURVE: 'usdTotal',
    BALANCER_V3: 'totalLiquidity', # can not be order well when querying
}

# the metric representing liquidity
DEX_METRIC = {
    UNISWAP_V2: 'reserveUSD',
    UNISWAP_V3: 'totalValueLockedUSD',
    SUSHISWAP_V2: 'reserveUSD',
    PANCAKESWAP_V3: 'totalValueLockedUSD',
    CURVE: 'reserveUSD',
    BALANCER_V3: 'reserveUSD', 
}

UNISWAPV2_ENDPOINT = "https://gateway.thegraph.com/api/subgraphs/id/EYCKATKGBKLWvSfwvBjzfCBmGwYNdVkduYXVivCsLRFu"
SUSHISWAPV2_ENDPOINT = "https://gateway.thegraph.com/api/subgraphs/id/A4JrrMwrEXsYNAiYw7rWwbHhQZdj6YZg1uVy5wa6g821"
UNISWAPV3_ENDPOINT = "https://gateway.thegraph.com/api/subgraphs/id/5zvR82QoaXYFyDEKLZ9t6v9adgnptxYpKpSbxtgVENFV"
PANCAKESWAP_V3_ENDPOINT = "https://gateway.thegraph.com/api/subgraphs/id/CJYGNhb7RvnhfBDjqpRnD3oxgyhibzc7fkAMa38YV3oS"
CURVE_ENDPOINT = "https://api.curve.fi/v1/getPools/big/ethereum"
BALANCER_V3_ENDPOINT = "https://api-v3.balancer.fi/"
PROXY = "http://127.0.0.1:7890"

# List of token addresses to exclude from routing consideration
BLACKLISTED_TOKENS = [
    '0xd233d1f6fd11640081abb8db125f722b5dc729dc'  # Example: Dollar Protocol token address
]


ALCHEMY_KEY = "ALCHEMY_KEY"
API_KEY = "API_KEY"