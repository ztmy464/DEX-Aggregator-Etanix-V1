import { Web3Provider } from '../../../web3/Web3Provider'
import { ApolloClientProvider } from '../../services/api/apollo-client-provider'
import { ReactNode } from 'react'
// import { RecentTransactionsProvider } from '../../modules/transactions/RecentTransactionsProvider'
import { ApolloGlobalDataProvider } from '../../services/api/apollo-global-data.provider'
import { UserSettingsProvider } from '../../../user/settings/UserSettingsProvider'
import { WagmiConfigProvider } from '../../../web3/WagmiConfigProvider'

export function Providers({ children }: { children: ReactNode }) {
  return (
    <WagmiConfigProvider>
      <Web3Provider>
        <ApolloClientProvider>
          <ApolloGlobalDataProvider>
            <UserSettingsProvider>
                {children}
            </UserSettingsProvider>
          </ApolloGlobalDataProvider>
        </ApolloClientProvider>
      </Web3Provider>
    </WagmiConfigProvider>
  )
}
