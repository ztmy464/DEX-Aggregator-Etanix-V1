'use client'

// import { ChainSlug, getChainSlug } from '../../modules/pool/pool.utils'
import { PriceImpactProvider } from '../../modules/price-impact/PriceImpactProvider'
// import { RelayerSignatureProvider } from '../../modules/relayer/RelayerSignatureProvider'
import { SwapProviderProps, SwapProvider } from './SwapProvider'
import { TokenBalancesProvider } from '../tokens/TokenBalancesProvider'
import { TokenInputsValidationProvider } from '../tokens/TokenInputsValidationProvider'
import { useTokens } from '../tokens/TokensProvider'
// import { TransactionStateProvider } from '../../modules/transactions/transaction-steps/TransactionStateProvider'
import { PropsWithChildren } from 'react'
// import { Permit2SignatureProvider } from '../../tokens/approvals/permit2/Permit2SignatureProvider'
import { PROJECT_CONFIG } from '../config/getProjectConfig'

type Props = PropsWithChildren<{
  props: SwapProviderProps
}>

// Layout shared by standard swap page (/swap) and pool swap page (/poolid/swap)
export default function SwapLayout({ props, children }: Props) {
  const { getTokensByChain } = useTokens()

  const chain = props.pathParams.chain
  const initChain = PROJECT_CONFIG.defaultNetwork
  const initTokens = getTokensByChain(initChain)

  // if (!initTokens) {
  //   // Avoid "Cant scale amount without token metadata" error when tokens are not ready in SwapProvider
  //   return null
  // }

  return (

          <TokenInputsValidationProvider>
            <TokenBalancesProvider initTokens={initTokens}>
              <PriceImpactProvider>
                <SwapProvider params={props}>{children}</SwapProvider>
              </PriceImpactProvider>
            </TokenBalancesProvider>
          </TokenInputsValidationProvider>

  )
}
