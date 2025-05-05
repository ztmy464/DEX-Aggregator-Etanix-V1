/* eslint-disable react/no-unescaped-entities */
'use client'

import { TokenInput } from '../tokens/TokenInput'
import { GqlChain, GqlPoolType } from '../shared/services/api/generated/graphql'
import { HumanAmount } from '../sdk'
import {
  Card,
  Center,
  HStack,
  VStack,
  Tooltip,
  useDisclosure,
  IconButton,
  Button,
  Box,
  CardHeader,
  CardFooter,
  CardBody,
  useToast,
  Image,
} from '@chakra-ui/react'
import { TransactionSettings } from '../user/settings/TransactionSettings'
import { TokenSelectModal } from '../tokens/TokenSelectModal/TokenSelectModal'
import { RefObject, useRef, useState } from 'react'
import { useSwap } from './SwapProvider'
import { Address } from 'viem'
import { CheckCircle, Link, Repeat, RefreshCw  } from 'react-feather'
import { motion, easeOut } from 'framer-motion'
import { capitalize } from 'lodash'
import FadeInOnView from '../shared/components/containers/FadeInOnView'
import { useIsMounted } from '../shared/hooks/useIsMounted'
import { useUserAccount } from '../web3/UserAccountProvider'
import { ChainSelect } from '../chains/ChainSelect'
import { ConnectWallet } from '../web3/ConnectWallet'
import { ApiToken } from '../tokens/token.types'
import { PriceImpactAccordion } from '../price-impact/PriceImpactAccordion'
import { RoutesAccordion } from '../price-impact/RoutesAccordion'
import { SwapRate } from './SwapRate'
import { SwapRoute } from './SwapRoute'
import { SwapDetails } from './SwapDetails'
import { RouteDetails } from './RouteDetails'


type Props = {
  redirectToPoolPage?: () => void // Only used for pool swaps
}

export function SwapForm({ redirectToPoolPage }: Props) {


  const {
    tokenIn,
    tokenOut,
    selectedChain,
    tokens,
    tokenSelectKey,
    isDisabled,
    disabledReason,
    previewModalDisclosure,
    simulationQuery,
    swapAction,
    selectedExchanges,
    // swapTxHash,
    // transactionSteps,
    setTokenInAmount,
    setTokenOutAmount,
    setTokenSelectKey,
    setTokenIn,
    setTokenOut,
    switchTokens,
    resetSwapAmounts,
    replaceUrlPath,
    setSelectedChain,
    setNeedsToAcceptHighPI,
    setSelectedExchanges,
  } = useSwap()
  const [copiedDeepLink, setCopiedDeepLink] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isrefetchSimulation, setIsrefetchSimulation] = useState(false);
  const toast = useToast();
  // Disclosures
  const tokenSelectDisclosure = useDisclosure();


  // Refs
  const nextBtn = useRef(null);
  const finalRefTokenIn = useRef<HTMLInputElement | null>(null);
  const finalRefTokenOut = useRef<HTMLInputElement | null>(null);

  const isPoolSwapUrl = false;
  const isMounted = useIsMounted()
  const { isConnected } = useUserAccount()

  const isLoadingSwaps = simulationQuery.isLoading
  const isLoading = isLoadingSwaps || !isMounted || isrefetchSimulation
  const loadingText = isLoading ? 'Fetching swap...' : undefined

  // Functions
  function copyDeepLink() {
    navigator.clipboard.writeText(window.location.href);
    setCopiedDeepLink(true);
    setTimeout(() => setCopiedDeepLink(false), 2000);
  }

  function handleTokenSelect(token: ApiToken) {
    if (!token) return
    if (tokenSelectKey === 'tokenIn') {
      setTokenIn(token.address as Address)
    } else if (tokenSelectKey === 'tokenOut') {
      setTokenOut(token.address as Address)
    } else {
      console.error('Unhandled token select key', tokenSelectKey)
    }
  }

  function openTokenSelectModal(tokenSelectKey: 'tokenIn' | 'tokenOut') {
    setTokenSelectKey(tokenSelectKey);
    tokenSelectDisclosure.onOpen();
  }

  const { refetch: refetchSimulation } = simulationQuery
  const handleRefreshPools = async () => {
    setIsRefreshing(true);
    try {
      const response = await fetch(`${process.env.NEXT_PRIVATE_ALLOWED_ORIGINS}/refresh_pools`);
      
      if (response.ok) {
        toast({
          title: "Pools refreshed",
          description: "Liquidity pools data has been updated.",
          status: "success",
          duration: 3000,
          isClosable: true,
        });

        setIsrefetchSimulation(true);
        await refetchSimulation(); // ✅ 等待请求完成
        setIsrefetchSimulation(false);

      } else {
        toast({
          title: "Refresh failed",
          description: "Failed to refresh pools data. Please try again.",
          status: "error",
          duration: 3000,
          isClosable: true,
        });
      }
    } catch (error) {
      toast({
        title: "Connection error",
        description: "Could not connect to the server.",
        status: "error",
        duration: 3000,
        isClosable: true,
      });
      console.error("Error refreshing pools:", error);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <FadeInOnView>
      <Center
        h="full"
        left={['-12px', '0']}
        maxW="lg"
        mx="auto"
        position="relative"
        w={['100vw', 'full']}
      >
        <Card rounded="xl">
        <CardHeader as={HStack} justify="space-between" w="full" zIndex={11}>
          {/* 最左边的图片 */}
          <Image
            src="/images/flower_flat_1_transparent.png"
            alt="Info"
            boxSize="60px"
            opacity={0.7}
            cursor="pointer"
          />

          {/* 最右边的按钮组 */}
          <HStack>
            <Tooltip label={copiedDeepLink ? 'Copied!' : 'Copy swap link'}>
              <Button color="grayText" onClick={copyDeepLink} size="sm" variant="tertiary">
                {copiedDeepLink ? <CheckCircle size={16} /> : <Link size={16} />}
              </Button>
            </Tooltip>

            <TransactionSettings 
              size="sm"
              selectedExchanges={selectedExchanges}
              setSelectedExchanges={setSelectedExchanges} 
            />

            <Tooltip
              label={
                <>
                  Manually refresh liquidity pools<br />
                  Refresh automatically every five minutes
                </>
              }
            >
              <Button
                color="grayText"
                onClick={handleRefreshPools}
                size="sm"
                variant="tertiary"
                isLoading={isRefreshing}
                loadingText="Refreshing"
                spinner={<RefreshCw size={16} className={isRefreshing ? "animate-spin" : ""} />}
              >
                <RefreshCw size={16} className={isRefreshing ? "animate-spin" : ""} />
              </Button>
            </Tooltip>
          </HStack>
        </CardHeader>

          <CardBody align="start" as={VStack}>
            <VStack spacing="md" w="full">
              <ChainSelect
                  onChange={newValue => {
                    setSelectedChain(newValue as GqlChain)
                    setTokenInAmount('')
                  }}
                  value={selectedChain}
              />
              {/* Token input placeholders */}
              <VStack w="full">
              <TokenInput
                  address={tokenIn.address}
                  aria-label="TokenIn"
                  chain={selectedChain}
                  onChange={e => setTokenInAmount(e.currentTarget.value as HumanAmount)}
                  // 点击Token输入框时，打开 Token 选择弹窗
                  // TODO:
                  onToggleTokenClicked={() => openTokenSelectModal('tokenIn')}
                  ref={finalRefTokenIn}
                  value={tokenIn.amount}
                />
                <Box border="red 1px solid" position="relative">
                  <IconButton
                    aria-label="Switch tokens"
                    fontSize="2xl"
                    h="8"
                    icon={<Repeat size={16} />}
                    isRound
                    ml="-4"
                    mt="-4"
                    // 点击切换Token按钮时，改变交易方向
                    onClick={switchTokens}
                    position="absolute"
                    size="sm"
                    variant="tertiary"
                    w="8"
                  />
                </Box>
                <TokenInput
                  address={tokenOut.address}
                  aria-label="TokeOut"
                  chain={selectedChain}
                  disableBalanceValidation
                  hasPriceImpact
                  isLoadingPriceImpact={
                    simulationQuery.isLoading || !simulationQuery.data || !tokenIn.amount
                  }
                  onChange={e => setTokenOutAmount(e.currentTarget.value as HumanAmount)}
                  // 点击Token输入框时，打开 Token 选择弹窗
                  onToggleTokenClicked={() => openTokenSelectModal('tokenOut')}
                  ref={finalRefTokenOut}
                  value={tokenOut.amount}
                />
              </VStack>
              {!!simulationQuery.data && (
                <motion.div
                  animate={{ opacity: 1, scaleY: 1 }}
                  initial={{ opacity: 0, scaleY: 0.9 }}
                  style={{ width: '100%', transformOrigin: 'top' }}
                  transition={{ duration: 0.3, ease: easeOut }}
                >
                </motion.div>
              )}
              {!!simulationQuery.data && (
                <motion.div
                  animate={{ opacity: 1, scaleY: 1 }}
                  initial={{ opacity: 0, scaleY: 0.9 }}
                  style={{ width: '100%', transformOrigin: 'top' }}
                  transition={{ duration: 0.3, ease: easeOut }}
                >
                  <PriceImpactAccordion
                    accordionButtonComponent={<SwapRate />}
                    accordionPanelComponent={<SwapDetails />}
                    isDisabled={!simulationQuery.data}
                    setNeedsToAcceptPIRisk={setNeedsToAcceptHighPI}
                  />
                </motion.div>
              )}
              {!!simulationQuery.data && (
                <motion.div
                  animate={{ opacity: 1, scaleY: 1 }}
                  initial={{ opacity: 0, scaleY: 0.9 }}
                  style={{ width: '100%', transformOrigin: 'top' }}
                  transition={{ duration: 0.3, ease: easeOut }}
                >
                  <RoutesAccordion
                    accordionButtonComponent={<SwapRoute />}
                    accordionPanelComponent={<RouteDetails />}
                    isDisabled={!simulationQuery.data}
                  />
                </motion.div>
              )}

              {simulationQuery.isError ? (
                <Box>Simulation Error Placeholder</Box>
              ) : null}
            </VStack>
          </CardBody>
          <CardFooter>
            {isConnected ? (
              <Tooltip label={isDisabled ? disabledReason : ''}>
                <Button
                  isDisabled={isDisabled || !isMounted}
                  isLoading={isLoading}
                  loadingText={loadingText}
                  onClick={() => !isDisabled && previewModalDisclosure.onOpen()}
                  ref={nextBtn}
                  size="lg"
                  variant="secondary"
                  w="full"
                >
                  Next
                </Button>
              </Tooltip>
            ) : (
              <ConnectWallet
                isLoading={isLoading}
                loadingText={loadingText}
                size="lg"
                variant="primary"
                w="full"
              />
            )}
          </CardFooter>
        </Card>
      </Center>
      <TokenSelectModal
          chain={selectedChain}
          currentToken={tokenSelectKey === 'tokenIn' ? tokenIn.address : tokenOut.address}
          finalFocusRef={tokenSelectKey === 'tokenIn' ? finalRefTokenIn as RefObject<HTMLInputElement> : finalRefTokenOut as RefObject<HTMLInputElement>}
          isOpen={tokenSelectDisclosure.isOpen}
          onClose={tokenSelectDisclosure.onClose}
          onOpen={tokenSelectDisclosure.onOpen}
          onTokenSelect={handleTokenSelect}
          tokens={tokens}
        />
    </FadeInOnView>
  );
}