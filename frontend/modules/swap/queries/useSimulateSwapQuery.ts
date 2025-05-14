import { getChainId } from '../../config/app.config'
import { useBlockNumber } from 'wagmi'
import { useDebounce } from 'use-debounce'
import { Address } from 'viem'
import { SimulateSwapInputs,SimulateSwapResponse } from '../swap.types'
import { isZero } from '@/modules/shared/utils/numbers'
import { GqlSorSwapType } from '@/modules/shared/services/api/generated/graphql'
import { DefaultSwapHandler } from '../handlers/DefaultSwap.handler'
import { useQuery } from '@tanstack/react-query'

export type SimulateSwapParams = {
  handler: DefaultSwapHandler
  swapInputs: SimulateSwapInputs
  selectedExchanges: string[]
  enabled: boolean
}

export function useSimulateSwapQuery({
  handler,
  swapInputs: { swapAmount, chain, tokenIn, tokenOut, swapType, poolIds },
  selectedExchanges,
  enabled = true,
}: SimulateSwapParams) {

  // 防抖机制（debounce）
  const debouncedSwapAmount = useDebounce(swapAmount, 2000)[0]
  
  const params = new URLSearchParams({
    sell_ID: tokenIn,
    sell_amount: debouncedSwapAmount,
    buy_ID: tokenOut,
  })

  // Add exchanges parameter if there are selected exchanges
  if (selectedExchanges && selectedExchanges.length > 0) {
    params.append('exchanges', selectedExchanges.join(','));
  }

  // const url = `${process.env.NEXT_PRIVATE_ALLOWED_ORIGINS}/order_router?${params.toString()}`
  const url = `http://8.134.121.38:5080/order_router?${params.toString()}`
  console.log('🔍 url:----------------------------', url)

  const chainId = getChainId(chain)
  const { data: blockNumber } = useBlockNumber({ chainId })

  const queryKey = [debouncedSwapAmount, tokenIn, tokenOut, blockNumber]
  const order_router = async () => {
    try {
      const response = await fetch(url)
      
      return await response.json()
    } catch (error) {
      console.error('Error fetching route data:', error)
      return null
    }
  }
  // React Query 发现queryKey变化 → 重新发送请求（只要 enabled === true）,不需要useEffect
  return useQuery<SimulateSwapResponse, Error>({
    queryKey: queryKey,
    enabled: enabled && !isZero(debouncedSwapAmount),
    queryFn: order_router,
    retry(failureCount, error){
      return failureCount < 2
    }
  })
}