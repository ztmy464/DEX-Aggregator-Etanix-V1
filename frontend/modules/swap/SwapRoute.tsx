import { Text } from '@chakra-ui/react'
import { useState } from 'react'
import { useSwap } from './SwapProvider'
import { useCurrency } from '../shared/hooks/useCurrency'
import { useTokens } from '../tokens/TokensProvider'
import { fNum } from '../shared/utils/numbers'

// Helper to create plural words (simple version)
const pluralize = (word: string, count: number) => {
  return count === 1 ? word : `${word}s`;
}

// Helper function to get a simplified DEX name (e.g., "Uniswap" from "Uniswap_V2")
const getDexName = (exchange: string) => {
  return exchange.split('_')[0]; // Basic split, adjust if DEX naming is different
};


export function SwapRoute() {
  const { simulationQuery } = useSwap();

  const route = simulationQuery.data?.routes?.[0];

  if (!route) {
    // Don't render anything or show loading if no route data yet
    return null;
  }

  const hopCount = route.swap.length;
  // Get unique, simplified DEX names used in the route
  const dexNames = Array.from(new Set(route.swap.map((s: any) => s.exchange.includes('_') ? s.exchange.replace(/_/g, ' ') : s.exchange))).join(', ');

  const routeSummary = `${hopCount} ${pluralize('Hop', hopCount)} via ${dexNames}`;

  return (
    <Text fontSize="sm" variant="secondary" noOfLines={1}> {/* Prevent wrapping */}
        Route: {routeSummary}
    </Text>
  );
}
