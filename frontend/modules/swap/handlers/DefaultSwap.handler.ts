import { ApolloClient } from '@apollo/client'
// import { Path } from '../../sdk'
import { SorGetSwapPathsDocument } from '../../shared/services/api/generated/graphql'
// import { ProtocolVersion } from '../../pool/pool.types'
import { SimulateSwapInputs, SimulateSwapResponse } from '../swap.types'
// import { BaseDefaultSwapHandler } from './BaseDefaultSwap.handler'
import {
  ensureError,
  isFailedToFetchApolloError,
  swapApolloNetworkErrorMessage,
} from '../../shared/utils/errors'
import { SwapHandler } from './Swap.handler'

export class DefaultSwapHandler  {
  name = 'DefaultSwapHandler'

  constructor(public apolloClient: ApolloClient<object>) {
  }

  async simulate({ ...variables }: SimulateSwapInputs) {

    //

    return {
      expectedOutputAmount: '98500000000000000000', // 98.5 DAI
      selectedPath: [], // 最佳路径详情
      slippage: '0.3%',
      hops: 2,
      gasEstimate: 152000,
    } 
  }
}
