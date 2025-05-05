import { ApolloClient } from '@apollo/client'
import { TransactionConfig } from '../../web3/contracts/contract.types'
import { BuildSwapInputs, SimulateSwapResponse, SimulateSwapInputs } from '../swap.types'
import { ApiToken } from '../../tokens/token.types'
import { getChainId } from '../../config/app.config'
import { useBlockNumber } from 'wagmi'
import { Address } from 'viem'
/**
 * SwapHandler is an interface that defines the methods that must be implemented by a handler.
 * They take standard inputs from the UI and return frontend standardised outputs.
 */
export interface SwapHandler {
  apolloClient?: ApolloClient<object>
  tokens?: ApiToken[]
  name: string

  simulate(inputs: SimulateSwapInputs): Promise<SimulateSwapResponse>
  build(inputs: BuildSwapInputs): TransactionConfig
}

export type SimulateSwapParams = {
  handler: SwapHandler
  swapInputs: SimulateSwapInputs
  enabled: boolean
}

export function useSimulateSwapQuery({
  handler,
  swapInputs: { swapAmount, chain, tokenIn, tokenOut, swapType, poolIds },
  enabled = true,
}: SimulateSwapParams) {

  const inputs = {
    swapAmount,
    swapType,
    tokenIn,
    tokenOut,
    chain,
    poolIds,
  }

  const chainId = getChainId(chain)
  const { data: blockNumber } = useBlockNumber({ chainId })

  // const queryKey = swapQueryKeys.simulation(inputs)

  // const queryFn = async () => handler.simulate(inputs)

  // return useQuery<SimulateSwapResponse, Error>({
  //   queryKey,
  //   queryFn,
  //   enabled: enabled && !isZero(debouncedSwapAmount),
  //   gcTime: 0,
  //   retry(failureCount, error) {
  //     if (isWrapWithTooSmallAmount(error?.message)) {
  //       // Avoid more retries
  //       return false
  //     }
  //     // 2 retries by default
  //     return failureCount < 2
  //   },
  //   meta: sentryMetaForSwapHandler('Error in swap simulation query', {
  //     chainId: getChainId(chain),
  //     blockNumber,
  //     handler,
  //     swapInputs: inputs,
  //     enabled,
  //   }),
  //   ...onlyExplicitRefetch,
  // })
}