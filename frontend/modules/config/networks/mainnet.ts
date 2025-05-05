import { GqlChain } from '../../../modules/shared/services/api/generated/graphql'
import { NetworkConfig } from '../config.types'
import { SupportedWrapHandler } from '../../swap/swap.types'
import { mainnet } from 'viem/chains'

const networkConfig: NetworkConfig = {
  chainId: 1,
  name: 'Ethereum Mainnet',
  shortName: 'Ethereum',
  chain: GqlChain.Mainnet,
  iconPath: '/images/chains/MAINNET.svg',
  blockExplorer: {
    baseUrl: 'https://etherscan.io',
    name: 'Etherscan',
  },
  tokens: {
    addresses: {
      veBalBpt: '0x5c6ee304399dbdb9c8ef030ab642b10820db8f56',
      bal: '0xba100000625a3754423978a60c9317c58a424e3d',
      wNativeAsset: '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
      auraBal: '0x616e8bfa43f920657b3497dbf40d6b1a02d4608d',
    },
    nativeAsset: {
      name: 'Ether',
      address: '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
      symbol: 'ETH',
      decimals: 18,
    },
    supportedWrappers: [
      {
        // stETH/wstETH
        baseToken: '0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84',
        wrappedToken: '0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0',
        swapHandler: SupportedWrapHandler.LIDO,
      },
    ],
    /**
     * The approval function for these tokens doesn't allow setting a new approval
     * level if the current level is > 0. Thus they must be approved in two steps
     * first setting to 0 then setting to the required amount.
     */
    doubleApprovalRequired: [
      '0xdac17f958d2ee523a2206206994597c13d831ec7', // USDT
      '0xf629cbd94d3791c9250152bd8dfbdf380e2a3b9c', // ENJ
    ],
    defaultSwapTokens: {
      tokenIn: '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
    },
    popularTokens: {
      '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee': 'ETH',
      '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2': 'WETH',
      '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48': 'USDC',
      '0x6B175474E89094C44Da98b954EedeAC495271d0F': 'DAI',
      '0xdAC17F958D2ee523a2206206994597C13D831ec7': 'USDT',
      '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599': 'WBTC',
      '0xba100000625a3754423978a60c9317c58a424e3D': 'BAL',
      '0xc0c293ce456ff0ed870add98a0828dd4d2903dbf': 'AURA',
      '0x616e8bfa43f920657b3497dbf40d6b1a02d4608d': 'auraBAL',
      '0x5c6ee304399dbdb9c8ef030ab642b10820db8f56': 'B-80BAL-20WETH',
      '0x7f39c581f595b53c5cb19bd0b3f8da6c935e2ca0': 'wstETH',
      '0xae78736cd615f374d3085123a210448e74fc6393': 'rETH',
      '0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9': 'AAVE',
      '0xbf5495efe5db9ce00f80364c8b423567e58d2110': 'ezETH',
      '0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee': 'weETH',
      '0xfae103dc9cf190ed75350761e95403b7b8afa6c0': 'rswETH',
      '0xe07f9d810a48ab5c3c914ba3ca53af14e4491e8a': 'GYD',
      '0x6810e776880c02933d47db1b9fc05908e5386b96': 'GNO',
      '0x40d16fc0246ad3160ccc09b8d0d3a2cd28ae6c2f': 'GHO',
    },
  },
} as const satisfies NetworkConfig

export default networkConfig
