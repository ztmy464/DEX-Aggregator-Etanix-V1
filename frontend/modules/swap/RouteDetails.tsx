/* eslint-disable react-hooks/exhaustive-deps */
import { NumberText } from '../shared/components/typography/NumberText'
import { useCurrency } from '../shared/hooks/useCurrency'
import { bn, fNum } from '../shared/utils/numbers'
import {
  HStack,
  VStack,
  Text,
  Box,
  Popover,
  PopoverTrigger,
  PopoverContent,
  Icon,
  Tag,
  Divider,
} from '@chakra-ui/react'
import { ArrowDownIcon, ArrowForwardIcon } from '@chakra-ui/icons';
import { GqlSorSwapType } from '../shared/services/api/generated/graphql'
import { useUserSettings } from '../user/settings/UserSettingsProvider'
import { usePriceImpact } from '../price-impact/PriceImpactProvider'
import { useTokens } from '../tokens/TokensProvider'
// import { NativeWrapHandler } from './handlers/NativeWrap.handler'
import { InfoIcon } from '../shared/components/icons/InfoIcon'
import pluralize from 'pluralize'
// import { BaseDefaultSwapHandler } from './handlers/BaseDefaultSwap.handler'
import { getFullPriceImpactLabel, getMaxSlippageLabel } from '../price-impact/price-impact.utils'
import { SimulateSwapResponse, SwapInfo } from './swap.types'; 
import { useSwap } from './SwapProvider';
import React from 'react';

const getDexName = (exchange: string) => {
  return exchange.includes('_') ? exchange.replace(/_/g, ' ') : exchange;
};

export function RouteDetails() {
  const { simulationQuery, tokenInInfo, tokenOutInfo } = useSwap();

  // Safely access the first route
  const route = simulationQuery.data?.routes?.[0];

  if (!route || !simulationQuery.data || !tokenInInfo || !tokenOutInfo) {
    // Render loading state or null if data isn't ready
    return <Text>Loading route details...</Text>;
  }

  const swaps = route.swap;

  return (
    <VStack align="stretch" spacing={3} w="full" fontSize="sm">
      {/* Display Overall Input */}
      <HStack justify="space-between">
        <Text color="grayText">Start with:</Text>
        <HStack>
          <Text fontWeight="medium">
            {fNum('token', route.amount_in)} {tokenInInfo.symbol}
          </Text>
           {/* You might want to add a TokenIcon component here if you have one */}
        </HStack>
      </HStack>

      <Divider my={1} />

      {/* Iterate through each swap hop */}
      {swaps.map((swap: SwapInfo, index: number) => (
        <React.Fragment key={swap.pool}>
          <VStack align="stretch" spacing={1.5}>
            {/* Hop Input */}
             <HStack justify="space-between">
                <Text color="grayText" fontSize="xs">Input</Text>
                <HStack spacing={1.5}>
                   {/* Consider adding TokenIcon */}
                  <Text fontSize="xs">
                    {fNum('token', swap.input_amount)} {swap.input_token}
                  </Text>
                </HStack>
             </HStack>

            {/* DEX Info */}
            <HStack justify="center" spacing={2} my={1} position="relative">
                <Icon as={ArrowDownIcon} boxSize={3} color="gray.500" position="absolute" left="0" />
                 <Tag size="sm" variant="subtle" colorScheme="blue"> {/* Adjust colorScheme */}
                   {getDexName(swap.exchange)}
                 </Tag>
                <Icon as={ArrowDownIcon} boxSize={3} color="gray.500" position="absolute" right="0" />
            </HStack>

             {/* Hop Output */}
             <HStack justify="space-between">
                 <Text color="grayText" fontSize="xs">Output</Text>
                 <HStack spacing={1.5}>
                    {/* Consider adding TokenIcon */}
                   <Text fontSize="xs" fontWeight="medium">
                     {fNum('token', swap.output_amount)} {swap.output_token}
                   </Text>
                 </HStack>
             </HStack>
          </VStack>

          {/* Add divider between hops, but not after the last one */}
          {index < swaps.length - 1 && <Divider my={2} variant="dashed" />}
        </React.Fragment>
      ))}

      <Divider my={1} />

      {/* Display Overall Output */}
      <HStack justify="space-between">
        <Text color="grayText">Receive:</Text>
        <HStack>
          <Text fontWeight="bold" color="green.500"> {/* Highlight final output */}
            {fNum('token', route.amount_out)} {tokenOutInfo.symbol}
          </Text>
           {/* You might want to add a TokenIcon component here */}
        </HStack>
      </HStack>
       {/* Optionally display total gas fee for the route */}
       <HStack justify="space-between" w="full">
          <Text color="grayText" fontSize="xs">Est. Gas Fee:</Text>
          <Text color="grayText" fontSize="xs">{fNum('token', route.gas_fee, {})} ETH</Text> {/* Adjust formatting/currency */}
       </HStack>
    </VStack>
  );
}