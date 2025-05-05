/* eslint-disable max-len */

import { SwapForm } from '../../../modules/swap/SwapForm'
import { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Swap tokens on Etanix-V1',
  description: `Swap tokens via multiple decentralized exchange`,
}

export default function SwapPage() {
  return <SwapForm />
}
