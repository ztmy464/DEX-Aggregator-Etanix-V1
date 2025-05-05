// import { TOTAL_APR_TYPES } from '@repo/lib/shared/hooks/useAprTooltip'
import {
  GetPoolQuery,
  GqlChain,
  GqlPoolAprItem,
  GqlPoolAprItemType,
  GqlPoolComposableStableNested,
  GqlPoolTokenDetail,
  GqlPoolType,
} from '../shared/services/api/generated/graphql'
// import { Numberish, bn, fNum } from '@repo/lib/shared/utils/numbers'
// import BigNumber from 'bignumber.js'
import { invert } from 'lodash'
// import { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime'
// import { Address, formatUnits, parseUnits } from 'viem'
// import { TokenAmountHumanReadable } from '../tokens/token.types'
// import { ClaimablePool } from './actions/claim/ClaimProvider'


// URL slug for each chain
export enum ChainSlug {
  Ethereum = 'ethereum',
  Arbitrum = 'arbitrum',
  Polygon = 'polygon',
  Avalanche = 'avalanche',
  Fantom = 'fantom',
  Base = 'base',
  Optimisim = 'optimism',
  Zkevm = 'zkevm',
  Gnosis = 'gnosis',
  Sepolia = 'sepolia',
  Mode = 'mode',
  Fraxtal = 'fraxtal',
  Sonic = 'sonic',
}

// Maps GraphQL chain enum to URL slug
export const chainToSlugMap: Record<GqlChain, ChainSlug> = {
  [GqlChain.Mainnet]: ChainSlug.Ethereum,
  // [GqlChain.Arbitrum]: ChainSlug.Arbitrum,
  // [GqlChain.Polygon]: ChainSlug.Polygon,
  // [GqlChain.Avalanche]: ChainSlug.Avalanche,
  // [GqlChain.Fantom]: ChainSlug.Fantom,
  // [GqlChain.Base]: ChainSlug.Base,
  // [GqlChain.Optimism]: ChainSlug.Optimisim,
  // [GqlChain.Zkevm]: ChainSlug.Zkevm,
  // [GqlChain.Gnosis]: ChainSlug.Gnosis,
  // [GqlChain.Sepolia]: ChainSlug.Sepolia,
  // [GqlChain.Mode]: ChainSlug.Mode,
  // [GqlChain.Fraxtal]: ChainSlug.Fraxtal,
  // [GqlChain.Sonic]: ChainSlug.Sonic,
}

export function getChainSlug(chainSlug: ChainSlug): GqlChain {
  const slugToChainMap = invert(chainToSlugMap) as Record<ChainSlug, GqlChain>
  const chain = slugToChainMap[chainSlug]
  if (!chain) throw new Error(`Chain ${chainSlug} is not a valid chainName`)
  return chain
}
