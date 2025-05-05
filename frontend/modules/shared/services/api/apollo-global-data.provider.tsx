/**
 * Apollo Global Data Provider
 *
 * This component is used to fetch data that is needed for the entire
 * application during the RSC render pass. The data is then passed to the client
 * providers that should then call `useSeedApolloCache` to seed the apollo cache
 * prior to the useQuery call, ensuring the data is already present on the first
 * client render pass.
 */
import { getApolloServerClient } from '../../services/api/apollo-server.client'
import {
  GetProtocolStatsDocument,
  GetTokenPricesDocument,
  GetTokensDocument,
} from '../../services/api/generated/graphql'
import { TokensProvider } from '../../../tokens/TokensProvider'
import { FiatFxRatesProvider } from '../../utils/FxRatesProvider'
import { getFxRates } from '../../utils/currencies'
import { mins } from '../../utils/time'
import { PropsWithChildren } from 'react'
import { getHooksMetadata } from '../../../hooks/getHooksMetadata'
import { HooksProvider } from '../../../hooks/HooksProvider'
// import { getPoolTags } from '@repo/lib/modules/pool/tags/getPoolTags'
// import { PoolTagsProvider } from '@repo/lib/modules/pool/tags/PoolTagsProvider'
// import { getErc4626Metadata } from '@repo/lib/modules/pool/metadata/getErc4626Metadata'
// import { PoolsMetadataProvider } from '@repo/lib/modules/pool/metadata/PoolsMetadataProvider'
// import { getPoolsMetadata } from '@repo/lib/modules/pool/metadata/getPoolsMetadata'
import { PROJECT_CONFIG } from '../../../config/getProjectConfig'
// import { ProtocolStatsProvider } from '../../../modules/protocol/ProtocolStatsProvider'
// import { FeeManagersProvider } from '../../../modules/fee-managers/FeeManagersProvider'
// import { getFeeManagersMetadata } from '../../../modules/fee-managers/getFeeManagersMetadata'

export const revalidate = 60

export async function ApolloGlobalDataProvider({ children }: PropsWithChildren) {
  const client = getApolloServerClient()

  const tokensQueryVariables = {
    chains: PROJECT_CONFIG.supportedNetworks,
  }

  const { data: tokensQueryData } = await client.query({
    query: GetTokensDocument,
    variables: tokensQueryVariables,
    context: {
      fetchOptions: {
        next: { revalidate: mins(20).toSecs() },
      },
    },
  })

  const { data: tokenPricesQueryData } = await client.query({
    query: GetTokenPricesDocument,
    variables: {
      chains: PROJECT_CONFIG.supportedNetworks,
    },
    context: {
      fetchOptions: {
        next: { revalidate: mins(10).toSecs() },
      },
    },
  })

  const { data: protocolData } = await client.query({
    query: GetProtocolStatsDocument,
    variables: {
      chains: PROJECT_CONFIG.networksForProtocolStats || PROJECT_CONFIG.supportedNetworks,
    },
    context: {
      fetchOptions: {
        next: { revalidate: mins(10).toSecs() },
      },
    },
  })

  const [
    exchangeRates,
    hooksMetadata,
    // poolTags,
    // erc4626Metadata,
    // poolsMetadata,
    // feeManagersMetadata,
  ] = await Promise.all([
    getFxRates(),
    getHooksMetadata(),
    // getPoolTags(),
    // getErc4626Metadata(),
    // getPoolsMetadata(),
    // getFeeManagersMetadata(),
  ])

  return (
    <TokensProvider
      tokenPricesData={tokenPricesQueryData}
      tokensData={tokensQueryData}
      variables={tokensQueryVariables}
    >
      <FiatFxRatesProvider data={exchangeRates}>
        <HooksProvider data={hooksMetadata}>
          {children}
        </HooksProvider>
      </FiatFxRatesProvider>
    </TokensProvider>
  )
}
