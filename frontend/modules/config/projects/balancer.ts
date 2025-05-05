import { ProjectConfig } from '../config.types'
// import { PartnerVariant, PoolDisplayType } from '../../modules/pool/pool.types'
import { GqlChain, GqlPoolType } from '../../../modules/shared/services/api/generated/graphql'
import { isProd } from '../../config/app.config'

export const ProjectConfigBalancer: ProjectConfig = {
  projectId: 'balancer',
  projectName: 'Balancer',
  projectUrl: 'https://balancer.fi',
  projectLogo: 'https://balancer.fi/images/icons/balancer.svg',
  supportedNetworks: [
    GqlChain.Mainnet,
    // GqlChain.Arbitrum,
    // GqlChain.Avalanche,
    // GqlChain.Base,
    // GqlChain.Gnosis,
    // GqlChain.Polygon,
    // GqlChain.Zkevm,
    // GqlChain.Optimism,
    // GqlChain.Mode,
    // GqlChain.Fraxtal,

    // testnets only in dev mode
    // ...(isProd ? [] : [GqlChain.Sepolia]),
  ],

  corePoolId: '0x5c6ee304399dbdb9c8ef030ab642b10820db8f56000200000000000000000014', // veBAL BAL8020 (Balancer 80 BAL 20 WETH) pool on Ethereum
  defaultNetwork: GqlChain.Mainnet,
  ensNetwork: GqlChain.Mainnet,
  delegateOwner: '0xba1ba1ba1ba1ba1ba1ba1ba1ba1ba1ba1ba1ba1b',
  externalLinks: {
    poolComposerUrl: 'https://pool-creator.balancer.fi',
  },
  merklRewardsChains: [GqlChain.Mainnet],
  // merklRewardsChains: [GqlChain.Mainnet, GqlChain.Arbitrum, GqlChain.Base, GqlChain.Mode],


  // cowSupportedNetworks: [GqlChain.Mainnet, GqlChain.Arbitrum, GqlChain.Base, GqlChain.Gnosis],
  cowSupportedNetworks: [GqlChain.Mainnet],
  partnerCards: [
    {
      backgroundImage: 'images/partners/cards/partner-cow-bg.png',
      bgColor: 'green.900',
      ctaText: 'View pools',
      ctaUrl: '/pools/cow',
      description: 'The first MEV-capturing AMM. More returns, less risk with LVR protection.',
      iconName: 'cow',
      title: 'CoW AMM',
    },
    {
      backgroundImage: 'images/partners/cards/partner-gyro-bg.png',
      bgColor: 'pink.600',
      ctaText: 'View pools on Gyro',
      ctaUrl: 'https://app.gyro.finance/pools/ethereum/',
      description: 'Concentrated Liquidity Pools on Balancer. Improves capital efficiency for LPs.',
      externalLink: true,
      iconName: 'gyro',
      title: 'Gyroscope',
    },
    {
      backgroundImage: 'images/partners/cards/partner-xave-bg.png',
      bgColor: 'blue.400',
      ctaText: 'View pools on Xave',
      ctaUrl: 'https://app.xave.co/pool',
      description: 'Foreign Exchange Liquidity Pools. Optimized for RWA and stablecoins.',
      externalLink: true,
      iconName: 'xave',
      title: 'Xave',
    },
  ],
}
