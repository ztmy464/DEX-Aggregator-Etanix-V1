import { getNetworkConfig } from './app.config'
import { setTag } from '@sentry/nextjs'
import { useEffect } from 'react'
import { useUserAccount } from '../web3/UserAccountProvider'
import { PROJECT_CONFIG } from './getProjectConfig'

export function useNetworkConfig() {
  let defaultNetwork

  const { chain } = useUserAccount()
  const projectDefaultNetwork = PROJECT_CONFIG.defaultNetwork

  if (!chain) {
    defaultNetwork = projectDefaultNetwork
  }

  if (!chain) {
    defaultNetwork = PROJECT_CONFIG.defaultNetwork
  }

  useEffect(() => {
    setTag('walletNetwork', chain?.name)
  }, [chain])

  return getNetworkConfig(chain?.id, defaultNetwork)
}
