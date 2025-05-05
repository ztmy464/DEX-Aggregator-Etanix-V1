import { GqlChain } from '../../../modules/shared/services/api/generated/graphql'

import mainnet from './mainnet'

const networkConfigs = {
  [GqlChain.Mainnet]: mainnet,
}

export default networkConfigs
