import {
  SorGetSwapPathsQuery,
  GqlChain,
  GqlSorSwapType,
} from '../shared/services/api/generated/graphql'
// import {
//   AuraBalSwapQueryOutput,
//   ExactInQueryOutput,
//   ExactOutQueryOutput,
//   Permit2,
//   Swap,
// } from '@balancer/sdk'
import { Address, Hex } from 'viem'

export type SwapTokenInput = {
  address: Address
  amount: string
  scaledAmount: bigint
}

export type SwapState = {
  tokenIn: SwapTokenInput
  tokenOut: SwapTokenInput
  swapType: GqlSorSwapType
  selectedChain: GqlChain
}

export type SimulateSwapInputs = {
  chain: GqlChain
  tokenIn: Address
  tokenOut: Address
  swapType: GqlSorSwapType
  swapAmount: string
  poolIds?: string[]
}

type ApiSwapQuery = SorGetSwapPathsQuery['swaps']

// export type SimulateSwapResponse = Pick<
//   ApiSwapQuery,
//   'effectivePrice' | 'effectivePriceReversed' | 'returnAmount' | 'swapType'
// >

export interface SwapInfo {
  pool: string;
  exchange: string;
  dangerous: boolean;
  input_token: string;
  input_amount: number;
  input_amount_usd: number;
  output_token: string;
  output_amount: number;
  output_amount_usd: number;
  execute_price: number;
  gas_fee: number;
}

export interface RouteData {
  amount_in: string; // Changed from number to string
  amount_in_usd: string; // Changed from number to string
  amount_out: string; // Changed from number to string
  amount_out_usd: string; // Changed from number to string
  gas_fee: string;
  path: string[];
  rate_exchange: string; // Changed from number to string
  rate_receive: string; // Changed from number to string
  swap: SwapInfo[]; // Changed from swap_0, swap_1 to an array
}

export interface SimulateSwapResponse {
  routes: RouteData[]; // Changed from array of tuples to array of objects
}


// export interface SdkSimulateSwapResponse extends SimulateSwapResponse {
//   swap: Swap
//   queryOutput: ExactInQueryOutput | ExactOutQueryOutput
//   protocolVersion: number
//   hopCount: number
// }


export interface BuildSwapInputs extends SwapState {
  account: Address
  slippagePercent: string
  simulateResponse: SimulateSwapResponse
  wethIsEth: boolean
  relayerApprovalSignature?: Hex
}



export enum SupportedWrapHandler {
  LIDO = 'LIDO',
}

export const OWrapType = {
  WRAP: 'wrap',
  UNWRAP: 'unwrap',
} as const

export type WrapType = (typeof OWrapType)[keyof typeof OWrapType]

export const OSwapAction = {
  ...OWrapType,
  SWAP: 'swap',
} as const

export type SwapAction = (typeof OSwapAction)[keyof typeof OSwapAction]
