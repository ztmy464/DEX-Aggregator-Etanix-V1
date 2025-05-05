'use client'
/* eslint-disable react-hooks/exhaustive-deps */

import { ApolloClient, useApolloClient, useReactiveVar } from '@apollo/client'
import { HumanAmount } from '../sdk'
import { useDisclosure } from '@chakra-ui/react'
import { getNetworkConfig } from '../config/app.config'
import { useNetworkConfig } from '../config/useNetworkConfig'
import { useMakeVarPersisted } from '../shared/hooks/useMakeVarPersisted'
import { LABELS } from '../shared/labels'
import { GqlChain, GqlSorSwapType } from '../shared/services/api/generated/graphql'
import { isSameAddress, selectByAddress } from '../shared/utils/addresses'
import { useMandatoryContext } from '../shared/utils/contexts'
import { isDisabledWithReason } from '../shared/utils/functions/isDisabledWithReason'
import { bn } from '../shared/utils/numbers'
import { invert } from 'lodash'
import { PropsWithChildren, createContext, useEffect, useMemo, useState } from 'react'
import { Address, Hash, InvalidDecimalNumberError, isAddress, parseUnits } from 'viem'
import { ChainSlug, chainToSlugMap, getChainSlug } from '../pool/pool.utils'
import { calcMarketPriceImpact } from '../price-impact/price-impact.utils'
import { usePriceImpact } from '../price-impact/PriceImpactProvider'
import { useTokenBalances } from '../tokens/TokenBalancesProvider'
import { useTokenInputsValidation } from '../tokens/TokenInputsValidationProvider'
import { useTokens } from '../tokens/TokensProvider'
// import { useTransactionSteps } from '../transactions/transaction-steps/useTransactionSteps'
import { emptyAddress } from '../web3/contracts/wagmi-helpers'
import { useUserAccount } from '../web3/UserAccountProvider'
import { DefaultSwapHandler } from './handlers/DefaultSwap.handler'

import { SwapHandler } from './handlers/Swap.handler'
import { useSimulateSwapQuery } from './queries/useSimulateSwapQuery'

import {
  OSwapAction,
  RouteData,
  SimulateSwapResponse,
  SwapAction,
  SwapState,
} from './swap.types'
// import { useSwapSteps } from './useSwapSteps'
import {
  getWrapHandlerClass,
  getWrapType,
  getWrapperForBaseToken,
  isNativeWrap,
  isSupportedWrap,
  isWrapOrUnwrap,
} from './wrap.helpers'
import { PROJECT_CONFIG } from '../config/getProjectConfig'
import { ApiToken } from '../tokens/token.types'

export type UseSwapResponse = ReturnType<typeof _useSwap>
export const SwapContext = createContext<UseSwapResponse | null>(null)

export type PathParams = {
  chain?: string
  tokenIn?: string
  tokenOut?: string
  amountIn?: string
  amountOut?: string
  // When urlTxHash is present the rest of the params above are not used
  urlTxHash?: Hash
}

function selectSwapHandler(
  tokenInAddress: Address,
  tokenOutAddress: Address,
  chain: GqlChain,
  swapType: GqlSorSwapType,
  apolloClient: ApolloClient<object>,
  tokens: ApiToken[]
): DefaultSwapHandler {
  return new DefaultSwapHandler(apolloClient)
}

export type SwapProviderProps = {
  pathParams: PathParams
  // Only used by pool swap
  poolActionableTokens?: ApiToken[]
}
export function _useSwap({ poolActionableTokens, pathParams }: SwapProviderProps) {
  const urlTxHash = pathParams.urlTxHash
  const isPoolSwapUrl = false

  const isPoolSwap = false
  const shouldDiscardOldPersistedValue = isPoolSwapUrl
  const swapStateVar = useMakeVarPersisted<SwapState>(
    {
      tokenIn: {
        address: emptyAddress,
        amount: '',
        scaledAmount: BigInt(0),
      },
      tokenOut: {
        address: emptyAddress,
        amount: '',
        scaledAmount: BigInt(0),
      },
      swapType: GqlSorSwapType.ExactIn,
      selectedChain: PROJECT_CONFIG.defaultNetwork,
    },
    'swapState',
    shouldDiscardOldPersistedValue
  )

  const swapState = useReactiveVar(swapStateVar)

  const [needsToAcceptHighPI, setNeedsToAcceptHighPI] = useState(false)
  const [tokenSelectKey, setTokenSelectKey] = useState<'tokenIn' | 'tokenOut'>('tokenIn')
  const [initUserChain, setInitUserChain] = useState<GqlChain | undefined>(undefined)

  const { isConnected } = useUserAccount()
  const { chain: walletChain } = useNetworkConfig()
  const { getToken, getTokensByChain, usdValueForToken } = useTokens()
  const { tokens, setTokens } = useTokenBalances()
  const { hasValidationErrors } = useTokenInputsValidation()
  const { setPriceImpact, setPriceImpactLevel } = usePriceImpact()

  const selectedChain = swapState.selectedChain
  const previewModalDisclosure = useDisclosure()

  const client = useApolloClient()
  const handler = useMemo(() => {
    return selectSwapHandler(
      swapState.tokenIn.address,
      swapState.tokenOut.address,
      selectedChain,
      swapState.swapType,
      client,
      tokens
    )
  }, [swapState.tokenIn.address, swapState.tokenOut.address, selectedChain])

  const isTokenInSet = swapState.tokenIn.address !== emptyAddress
  const isTokenOutSet = swapState.tokenOut.address !== emptyAddress

  const tokenInInfo = getToken(swapState.tokenIn.address, selectedChain)
  const tokenOutInfo = getToken(swapState.tokenOut.address, selectedChain)

  if (
    (isTokenInSet && !tokenInInfo && !isPoolSwap) ||
    (isTokenOutSet && !tokenOutInfo && !isPoolSwap)
  ) {
    try {
      setDefaultTokens()
    } catch (error) {
      throw new Error('Token metadata not found')
    }
  }

  const tokenInUsd = usdValueForToken(tokenInInfo, swapState.tokenIn.amount)
  const tokenOutUsd = usdValueForToken(tokenOutInfo, swapState.tokenOut.amount)

  const getSwapAmount = () => {
    const swapState = swapStateVar()
    return (
      (swapState.swapType === GqlSorSwapType.ExactIn
        ? swapState.tokenIn.amount
        : swapState.tokenOut.amount) || '0'
    )
  }

  const shouldFetchSwap = (state: SwapState, urlTxHash?: Hash) => {
    if (urlTxHash) return false
    return (
      isAddress(state.tokenIn.address) &&
      isAddress(state.tokenOut.address) &&
      !!state.swapType &&
      bn(getSwapAmount()).gt(0)
    )
  }

  const ALL_DEXES = [
    'Uniswap_V2',
    'Sushiswap_V2',
    'Uniswap_V3',
    'Pancakeswap_V3',
    'Curve',
    'Balancer_V3'
  ]

  const [selectedExchanges, setSelectedExchanges] = useState<string[]>(ALL_DEXES);

  const simulationQuery  = useSimulateSwapQuery({
    handler,
    swapInputs: {
      chain: selectedChain,
      tokenIn: swapState.tokenIn.address,
      tokenOut: swapState.tokenOut.address,
      swapType: swapState.swapType,
      swapAmount: getSwapAmount(),
      // We only use this field to filter by the specific pool swap path in pool swap flow
      // poolIds: getPoolSwapPoolsIds(),
    },
    selectedExchanges,
    enabled: shouldFetchSwap(swapState, urlTxHash),
  })
  // 解构simulationQuery
  const { data: simulationData, isFetching, isError, isLoading } = simulationQuery

  console.log('🔍 simulationQuery:----------------------------', simulationData?.routes[0])
//   {
//     "swapType": "EXACT_IN",
//     "selectedChain": "MAINNET",
//     "tokenIn": {
//         "address": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
//         "amount": "1",
//         "scaledAmount": "100000000"
//     },
//     "tokenOut": {
//         "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
//         "amount": "0",
//         "scaledAmount": "0"
//     }
//  }

function handleSimulationResponse({amount_out}: RouteData) {
    const swapState = swapStateVar()
    swapStateVar({
      ...swapState,

    })

    // if (swapType === GqlSorSwapType.ExactIn) {
    setTokenOutAmount(amount_out, { userTriggered: false })
    // } 
    // else {
    //   setTokenInAmount(returnAmount, { userTriggered: false })
    // }
  }
  //LIVED:
  function setSelectedChain(_selectedChain: GqlChain) {
    const defaultTokenState = getDefaultTokenState(_selectedChain)
    swapStateVar(defaultTokenState)
  }

  function setTokenIn(tokenAddress: Address) {
    const swapState = swapStateVar()
    const isSameAsTokenOut = isSameAddress(tokenAddress, swapState.tokenOut.address)

    swapStateVar({
      ...swapState,
      tokenIn: {
        ...swapState.tokenIn,
        address: tokenAddress,
      },
      tokenOut: isSameAsTokenOut
        ? { ...swapState.tokenOut, address: emptyAddress }
        : swapState.tokenOut,
    })
  }

  function setTokenOut(tokenAddress: Address) {
    const swapState = swapStateVar()
    const isSameAsTokenIn = isSameAddress(tokenAddress, swapState.tokenIn.address)

    swapStateVar({
      ...swapState,
      tokenOut: {
        ...swapState.tokenOut,
        address: tokenAddress,
      },
      tokenIn: isSameAsTokenIn
        ? { ...swapState.tokenIn, address: emptyAddress }
        : swapState.tokenIn,
    })
  }

  function switchTokens() {
    const swapState = swapStateVar()
    swapStateVar({
      ...swapState,
      tokenIn: swapState.tokenOut,
      tokenOut: swapState.tokenIn,
      swapType: GqlSorSwapType.ExactIn,
    })
    setTokenInAmount('', { userTriggered: false })
    setTokenOutAmount('', { userTriggered: false })
  }
  
  //LIVED:
  function setTokenInAmount(
    amount: string,
    { userTriggered = true }: { userTriggered?: boolean } = {}
  ) {
    const state = swapStateVar()
    const newState = {
      ...state,
      tokenIn: {
        ...state.tokenIn,
        /*
          When copy-pasting a swap URL with a token amount, the tokenInInfo can be undefined
          so we set amount as zero instead of crashing the app
        */
        amount: tokenInInfo ? amount : '0',
        scaledAmount: tokenInInfo ? scaleTokenAmount(amount, tokenInInfo) : BigInt(0),
      },
    }

    if (userTriggered) {
      swapStateVar({
        ...newState,
        swapType: GqlSorSwapType.ExactIn,
      })
      setTokenOutAmount('', { userTriggered: false })
    } else {
      // Sometimes we want to set the amount without triggering a fetch or
      // swapType change, like when we populate the amount after a change from the other input.
      swapStateVar(newState)
    }
  }

  function setTokenOutAmount(
    amount: string,
    { userTriggered = true }: { userTriggered?: boolean } = {}
  ) {
    const state = swapStateVar()
    const newState = {
      ...state,
      tokenOut: {
        ...state.tokenOut,
        /*
          When copy-pasting a swap URL with a token amount, the tokenOutInfo can be undefined
          so we set amount as zero instead of crashing the app
        */
        amount: tokenOutInfo ? amount : '0',
        scaledAmount: tokenOutInfo ? scaleTokenAmount(amount, tokenOutInfo) : BigInt(0),
      },
    }

    if (userTriggered) {
      swapStateVar({
        ...newState,
        swapType: GqlSorSwapType.ExactOut,
      })
      setTokenInAmount('', { userTriggered: false })
    } else {
      // Sometimes we want to set the amount without triggering a fetch or
      // swapType change, like when we populate the amount after a change from
      // the other input.
      swapStateVar(newState)
    }
  }

  //LIVED:
  function getDefaultTokenState(chain: GqlChain) {
    const swapState = swapStateVar()
    const {
      tokens: { defaultSwapTokens },
    } = getNetworkConfig(chain)
    const { tokenIn, tokenOut } = defaultSwapTokens || {}

    return {
      swapType: GqlSorSwapType.ExactIn,
      selectedChain: chain,
      tokenIn: {
        ...swapState.tokenIn,
        address: tokenIn ? tokenIn : emptyAddress,
      },
      tokenOut: {
        ...swapState.tokenOut,
        address: tokenOut ? tokenOut : emptyAddress,
      },
    }
  }

  function resetSwapAmounts() {
    const state = swapStateVar()

    swapStateVar({
      ...state,
      tokenIn: {
        ...state.tokenIn,
        amount: '',
        scaledAmount: BigInt(0),
      },
      tokenOut: {
        ...state.tokenOut,
        amount: '',
        scaledAmount: BigInt(0),
      },
    })
  }

  function setDefaultTokens() {
    swapStateVar(getDefaultTokenState(selectedChain))
  }

  function replaceUrlPath() {
    if (isPoolSwapUrl) return // Avoid redirection when the swap is within a pool page
    const { selectedChain, tokenIn, tokenOut, swapType } = swapState
    const networkConfig = getNetworkConfig(selectedChain)
    const { popularTokens } = networkConfig.tokens
    const chainSlug = chainToSlugMap[selectedChain as GqlChain]
    const newPath = ['/swap']

    const _tokenIn = selectByAddress(popularTokens || {}, tokenIn.address) || tokenIn.address
    const _tokenOut = selectByAddress(popularTokens || {}, tokenOut.address) || tokenOut.address

    if (chainSlug) newPath.push(`/${chainSlug}`)
    if (_tokenIn) newPath.push(`/${_tokenIn}`)
    if (_tokenIn && _tokenOut) newPath.push(`/${_tokenOut}`)
    if (_tokenIn && _tokenOut && tokenIn.amount && swapType === GqlSorSwapType.ExactIn) {
      newPath.push(`/${tokenIn.amount}`)
    }
    if (_tokenIn && _tokenOut && tokenOut.amount && swapType === GqlSorSwapType.ExactOut) {
      newPath.push(`/0/${tokenOut.amount}`)
    }

    window.history.replaceState({}, '', newPath.join(''))
  }

  function normalizeDecimalString(value: string, decimals: number): string {
    const num = Number(value)
    if (!Number.isFinite(num)) throw new InvalidDecimalNumberError({ value })
    // 保留 decimals + 1 位小数，防止精度被截断太早
    return num.toFixed(decimals + 1).replace(/\.?0+$/, '')
  }
  

  function scaleTokenAmount(amount: string, token: ApiToken): bigint {
    if (amount === '') return parseUnits('0', token.decimals)

      const normalizedAmount = normalizeDecimalString(amount, token.decimals)
    return parseUnits(normalizedAmount, token.decimals)
  }

  function calcPriceImpact() {
    if (!bn(tokenInUsd).isZero() && !bn(tokenOutUsd).isZero()) {
      setPriceImpact(calcMarketPriceImpact(tokenInUsd, tokenOutUsd))
    } else if (simulationData) {
      setPriceImpact(undefined)
      setPriceImpactLevel('low')
    }
  }
  

  const networkConfig = getNetworkConfig(selectedChain)
  const wethIsEth =
    isSameAddress(swapState.tokenIn.address, networkConfig.tokens.nativeAsset.address) ||
    isSameAddress(swapState.tokenOut.address, networkConfig.tokens.nativeAsset.address)
  const validAmountOut = bn(swapState.tokenOut.amount).gt(0)


  const vaultAddress  = 0

  const swapAction: SwapAction = useMemo(() => {
    if (isWrapOrUnwrap(swapState.tokenIn.address, swapState.tokenOut.address, selectedChain)) {
      const wrapType = getWrapType(
        swapState.tokenIn.address,
        swapState.tokenOut.address,
        selectedChain
      )
      return wrapType ? wrapType : OSwapAction.SWAP
    }

    return OSwapAction.SWAP
  }, [swapState.tokenIn.address, swapState.tokenOut.address, selectedChain])

  const isWrap = swapAction === 'wrap' || swapAction === 'unwrap'

  /**
   * Step construction
   */
  // const { steps, isLoadingSteps } = useSwapSteps({
  //   vaultAddress,
  //   swapState,
  //   handler,
  //   simulationQuery,
  //   wethIsEth,
  //   swapAction,
  //   tokenInInfo,
  //   tokenOutInfo,
  //   isPoolSwap: !!isPoolSwap,
  // })

  // const transactionSteps = useTransactionSteps(steps, isLoadingSteps)

  // const swapTxHash = urlTxHash || transactionSteps.lastTransaction?.result?.data?.transactionHash
  // const swapTxConfirmed = transactionSteps.lastTransactionConfirmed

  // const hasQuoteContext = !!simulationQuery.data

  function setInitialTokenIn(slugTokenIn?: string) {
    const { popularTokens } = getInitialNetworkConfig().tokens
    const symbolToAddressMap = invert(popularTokens || {}) as Record<string, Address>
    if (slugTokenIn) {
      if (isAddress(slugTokenIn)) {
        setTokenIn(slugTokenIn as Address)
      } else if (symbolToAddressMap[slugTokenIn] && isAddress(symbolToAddressMap[slugTokenIn])) {
        setTokenIn(symbolToAddressMap[slugTokenIn])
      }
    }
  }

  function setInitialTokenOut(slugTokenOut?: string) {
    const { popularTokens } = getInitialNetworkConfig().tokens
    const symbolToAddressMap = invert(popularTokens || {}) as Record<string, Address>
    if (slugTokenOut) {
      if (isAddress(slugTokenOut)) setTokenOut(slugTokenOut as Address)
      else if (symbolToAddressMap[slugTokenOut] && isAddress(symbolToAddressMap[slugTokenOut])) {
        setTokenOut(symbolToAddressMap[slugTokenOut])
      }
    }
  }

  function setInitialChain(slugChain?: string) {
    const _chain =
      slugChain && getChainSlug(slugChain as ChainSlug)
        ? getChainSlug(slugChain as ChainSlug)
        : walletChain

    setSelectedChain(_chain)
  }

  function setInitialAmounts(slugAmountIn?: string, slugAmountOut?: string) {
    if (slugAmountIn && !slugAmountOut && bn(slugAmountIn).gt(0)) {
      setTokenInAmount(slugAmountIn as HumanAmount)
    } else if (slugAmountOut && bn(slugAmountOut).gt(0)) {
      setTokenOutAmount(slugAmountOut as HumanAmount)
    } else resetSwapAmounts()
  }

  // Returns networkConfig to be used in the initial load
  function getInitialNetworkConfig() {
    const swapState = swapStateVar()
    return getNetworkConfig(swapState.selectedChain)
  }

  // Set state on initial load
  useEffect(() => {
    if (urlTxHash) return

    const { chain, tokenIn, tokenOut, amountIn, amountOut } = pathParams
    
    setInitialChain(chain)
    setInitialTokenIn(tokenIn)
    setInitialTokenOut(tokenOut)
    setInitialAmounts(amountIn, amountOut)

    if (!swapState.tokenIn.address && !swapState.tokenOut.address) setDefaultTokens()
  }, [])

  // When wallet chain changes, update the swap form chain
  useEffect(() => {
    if (isConnected && initUserChain && walletChain !== selectedChain) {
      setSelectedChain(walletChain)
    } else if (isConnected) {
      setInitUserChain(walletChain)
    }
  }, [walletChain])

  // When a new simulation is triggered, update the state
  useEffect(() => {
    if (simulationData) {
      
      handleSimulationResponse(simulationData.routes[0])
    }
  }, [simulationData])

  // Check if tokenIn is a base wrap token and set tokenOut as the wrapped token.
  useEffect(() => {
    const wrapper = getWrapperForBaseToken(swapState.tokenIn.address, selectedChain)
    if (wrapper) setTokenOut(wrapper.wrappedToken)

    // If the token in address changes we should reset tx step index because
    // the first approval will be different.
    // transactionSteps.setCurrentStepIndex(0)
  }, [swapState.tokenIn.address])

  // Check if tokenOut is a base wrap token and set tokenIn as the wrapped token.
  useEffect(() => {
    const wrapper = getWrapperForBaseToken(swapState.tokenOut.address, selectedChain)
    if (wrapper) setTokenIn(wrapper.wrappedToken)
  }, [swapState.tokenOut.address])

  // Update the URL path when the tokens change
  useEffect(() => {
    replaceUrlPath()
  }, [selectedChain, swapState.tokenIn, swapState.tokenOut, swapState.tokenIn.amount])

  // Update selectable tokens when the chain changes
  useEffect(() => {
    if (isPoolSwap) return
    setTokens(getTokensByChain(selectedChain))
  }, [selectedChain])

  // Open the preview modal when a swap tx hash is present
  // useEffect(() => {
  //   if (swapTxHash) {
  //     previewModalDisclosure.onOpen()
  //   }
  // }, [swapTxHash])

  // If token out value changes when swapping exact in, recalculate price impact.
  useEffect(() => {
    if (swapState.swapType === GqlSorSwapType.ExactIn) {
      calcPriceImpact()
    }
  }, [tokenOutUsd])

  // If token in value changes when swapping exact out, recalculate price impact.
  useEffect(() => {
    if (swapState.swapType === GqlSorSwapType.ExactOut) {
      calcPriceImpact()
    }
  }, [tokenInUsd])

  const { isDisabled, disabledReason } = isDisabledWithReason(
    [!isConnected, LABELS.walletNotConnected],
    [!validAmountOut, 'Invalid amount out'],
    [needsToAcceptHighPI, 'Accept high price impact first'],
    [hasValidationErrors, 'Invalid input'],
    [isError, 'Error fetching swap'],
    [isLoading, 'Fetching swap...']
  )

  return {
    ...swapState,
    selectedChain,
    tokens,
    tokenInInfo,
    tokenOutInfo,
    tokenSelectKey,
    simulationQuery,
    isDisabled,
    disabledReason,
    previewModalDisclosure,
    handler,
    wethIsEth,
    swapAction,
    urlTxHash,
    isWrap,
    isPoolSwap,
    poolActionableTokens,
    selectedExchanges,
    setSelectedExchanges,
    replaceUrlPath,
    resetSwapAmounts,
    setTokenSelectKey,
    setSelectedChain,
    setTokenInAmount,
    setTokenOutAmount,
    setTokenIn,
    setTokenOut,
    switchTokens,
    setNeedsToAcceptHighPI,
  }
}

type Props = PropsWithChildren<{
  params: SwapProviderProps
}>

export function SwapProvider({ params, children }: Props) {
  const hook = _useSwap(params)
  return <SwapContext.Provider value={hook}>{children}</SwapContext.Provider>
}

export const useSwap = (): UseSwapResponse => useMandatoryContext(SwapContext, 'Swap')
